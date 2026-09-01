"""Couche conversationnelle : transforme un besoin exprimé en orientation vers les acteurs du territoire.

Principe (note de synthèse « benchmark ») : on RETROUVE, on ne rédige pas. Le texte renvoyé est assemblé
à partir (1) des fiches de l'annuaire, (2) d'extraits exacts des documents, (3) des messages configurés
par l'administrateur. Sous le seuil de fiabilité, le chatbot dit qu'il n'a pas trouvé et propose des
catégories de besoins (REQ-FUNC.1 : guider la formulation du besoin).
"""

from __future__ import annotations

import re
import time
import unicodedata

from .analytics import Analytics
from .chatbot_config import ConfigStore
from .config import Settings
from .directory import DirectoryRepository, organization_card, short_description
from .directory.render import org_id_from_doc_id
from .schemas import (AskRequest, AskResponse, ChatbotConfig, DocumentExtract, Hit, Intent, OrganizationOut,
                      OrganizationResult, SearchMode)
from .search import SearchEngine
from .search.keyword import tokenize

_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "`": "'"})
_NAME_TAIL_TOKENS = 3   # au-delà, la question ne se réduit pas à « parlez-moi de <acteur> »


def normalize(text: str) -> str:
    text = "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")
    return " ".join(text.translate(_APOSTROPHES).split())


def _contains(haystack_norm: str, needle_norm: str) -> bool:
    if not needle_norm:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(needle_norm)}(?![a-z0-9])", haystack_norm) is not None


_SEPARATOR_RE = re.compile(r"\s+[–—-]\s+")
_ACRONYM_RE = re.compile(r"^[a-z0-9&'.]{2,12}$")


def _aliases(name: str) -> list[str]:
    """Façons de désigner un acteur dans une question.

    « Institut Clément Ader (ICA) – site d'Albi » -> nom complet, 'institut clement ader – site d'albi',
    'institut clement ader', 'ica'. « France Travail – Agence d'Albi » -> …, 'france travail'.
    Le contenu d'une parenthèse n'est retenu que s'il s'agit d'un sigle isolé (« IMT Mines Albi – CNRS »
    entre parenthèses ne doit pas faire passer RAPSODEE pour IMT Mines Albi).
    """
    norm = normalize(name)
    candidates = [norm]
    without_parens = re.sub(r"\s*\([^)]*\)", "", norm).strip()
    if without_parens:
        candidates.append(without_parens)
    for inner in re.findall(r"\(([^)]+)\)", norm):
        acronym = _SEPARATOR_RE.split(inner.strip(), maxsplit=1)[0].strip()
        if _ACRONYM_RE.match(acronym):
            candidates.append(acronym)
    for base in list(candidates):
        candidates.append(_SEPARATOR_RE.split(base, maxsplit=1)[0].strip())
    aliases: list[str] = []
    for a in candidates:
        if len(a) >= 3 and a not in aliases:
            aliases.append(a)
    return aliases


def detect_category(question: str, config: ChatbotConfig, organizations: list[OrganizationOut]) -> str | None:
    """Catégorie de besoin : mots-clés de la question, sinon domaines / mots-clés des acteurs proposés."""
    texts = [normalize(question),
             normalize(" ; ".join(t for o in organizations for t in (*o.domains, *o.keywords)))]
    for text in texts:
        best, best_n = None, 0
        for cat in config.categories:
            n = sum(1 for k in cat.keywords if _contains(text, normalize(k)))
            if n > best_n:
                best, best_n = cat.name, n
        if best:
            return best
    return None


class Assistant:
    def __init__(self, engine: SearchEngine, repo: DirectoryRepository, config_store: ConfigStore,
                 analytics: Analytics, settings: Settings) -> None:
        self.engine = engine
        self.repo = repo
        self.config_store = config_store
        self.analytics = analytics
        self.settings = settings

    # ------------------------------------------------------------------ API
    def answer(self, question: str, mode: SearchMode, config: ChatbotConfig,
               max_organizations: int | None = None) -> tuple[AskResponse, list[Hit]]:
        """Construit la réponse sans journaliser (utilisé par /ask et par l'évaluation)."""
        question = " ".join(question.split())
        max_orgs = max_organizations or config.max_organizations
        hits: list[Hit] = []
        named = self.named_organization(question) if config.orientation_enabled else None
        if named is not None:
            resp = self._organization_response(question, mode, config, named)
        else:
            hits = self.engine.search(question, mode, self.settings.candidate_pool)
            resp = self._search_response(question, mode, config, hits, max_orgs)
        resp.category = detect_category(question, config, resp.organizations)
        return resp, hits

    def ask(self, req: AskRequest) -> AskResponse:
        t0 = time.perf_counter()
        config = self.config_store.get()
        mode = req.mode or SearchMode(self.settings.default_mode)
        resp, hits = self.answer(req.question, mode, config, req.max_organizations)
        question = resp.question
        resp.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        if not config.suggestions_enabled:
            resp.suggestions = []
        if config.analytics_enabled:
            resp.query_id = self.analytics.log(
                question=question, answered=resp.answered, intent=resp.intent.value, category=resp.category,
                top_score=resp.score, latency_ms=resp.latency_ms, mode=mode.value,
                organizations=[o.name for o in resp.organizations], session_id=req.session_id,
            )
        if req.debug:
            resp.hits = hits
        return resp

    # ------------------------------------------------------- acteur nommé
    def named_organization(self, question: str) -> OrganizationOut | None:
        """Si la question se résume à « parlez-moi de <acteur> », renvoie cet acteur (sans passer par l'index)."""
        norm_q = normalize(question)
        best: tuple[int, str] | None = None
        for org_id, name in self.repo.names():
            for alias in _aliases(name):
                if _contains(norm_q, alias) and (best is None or len(alias) > len(best[1])):
                    best = (org_id, alias)
        if best is None:
            return None
        remainder = re.sub(rf"(?<![a-z0-9]){re.escape(best[1])}(?![a-z0-9])", " ", norm_q)
        if len(tokenize(remainder)) > _NAME_TAIL_TOKENS:
            return None
        return self.repo.get(best[0])

    def _organization_response(self, question: str, mode: SearchMode, config: ChatbotConfig,
                               org: OrganizationOut) -> AskResponse:
        result = OrganizationResult(**org.model_dump(), score=1.0)
        suggestions = [f"Quels autres acteurs en {d} ?" for d in org.domains[:3]]
        return AskResponse(question=question, mode=mode, intent=Intent.organization, answered=True,
                           answer=organization_card(org), score=1.0, organizations=[result],
                           suggestions=suggestions, latency_ms=0.0)

    # ------------------------------------------------------ recherche
    @staticmethod
    def _shown_score(hit: Hit) -> float:
        """Score exposé à l'usager / aux analytiques : la similarité cosinus si elle existe (comparable au seuil)."""
        return hit.semantic_score if hit.semantic_score is not None else hit.score

    def _search_response(self, question: str, mode: SearchMode, config: ChatbotConfig,
                         hits: list[Hit], max_orgs: int) -> AskResponse:
        best_by_doc: dict[str, Hit] = {}
        for h in hits:   # triés par score décroissant
            if self.engine.is_confident(h, mode):
                best_by_doc.setdefault(h.source.doc_id, h)

        organizations: list[OrganizationResult] = []
        if config.orientation_enabled:
            for h in (x for x in best_by_doc.values() if x.source.kind == "organization"):
                org_id = org_id_from_doc_id(h.source.doc_id)
                org = self.repo.get(org_id) if org_id is not None else None
                if org and org.active:
                    organizations.append(OrganizationResult(**org.model_dump(), score=self._shown_score(h)))
                if len(organizations) >= max_orgs:
                    break
        documents = [DocumentExtract(title=h.source.title, source=h.source.source, section=h.source.section,
                                     text=h.text, score=self._shown_score(h))
                     for h in best_by_doc.values() if h.source.kind == "document"][:1]
        top_score = self._shown_score(hits[0]) if hits else None

        if organizations:
            return AskResponse(
                question=question, mode=mode, intent=Intent.orientation, answered=True,
                answer=self._compose_orientation(config, organizations, documents), score=top_score,
                organizations=organizations, documents=documents,
                suggestions=[f"En savoir plus sur {o.name}" for o in organizations], latency_ms=0.0)
        if documents:
            doc = documents[0]
            where = f"{doc.title} › {doc.section}" if doc.section else doc.title
            return AskResponse(
                question=question, mode=mode, intent=Intent.document, answered=True,
                answer=f"{doc.text}\n\nSource : {where}", score=top_score, documents=documents,
                suggestions=self._category_suggestions(config), latency_ms=0.0)
        return AskResponse(
            question=question, mode=mode, intent=Intent.no_answer, answered=False,
            answer=self._compose_no_answer(config), score=top_score,
            suggestions=self._category_suggestions(config), latency_ms=0.0)

    # ----------------------------------------------------- composition
    @staticmethod
    def _compose_orientation(config: ChatbotConfig, organizations: list[OrganizationResult],
                             documents: list[DocumentExtract]) -> str:
        lines = [config.orientation_intro, ""]
        for o in organizations:
            line = f"• {o.name}"
            desc = short_description(o.description)
            if desc:
                line += f" — {desc}"
            cities = [s.city for s in o.sites if s.city]
            if cities:
                line += f" ({cities[0]})"
            lines.append(line)
        if documents:
            doc = documents[0]
            where = f"{doc.title} › {doc.section}" if doc.section else doc.title
            lines += ["", f"À lire aussi — {where} :", doc.text]
        if config.orientation_outro:
            lines += ["", config.orientation_outro]
        return "\n".join(lines).strip()

    @staticmethod
    def _compose_no_answer(config: ChatbotConfig) -> str:
        lines = [config.no_answer_message]
        lines += [f"• {c.name}" for c in config.categories]
        return "\n".join(lines).strip()

    @staticmethod
    def _category_suggestions(config: ChatbotConfig) -> list[str]:
        return [c.example_question or c.name for c in config.categories][:6]
