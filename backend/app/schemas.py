"""Contrat de l'API (modèles Pydantic).

Trois familles :
  - annuaire : Organisation / Site / Contact / Domaine d'activité (MCD du recueil des besoins, § 6) ;
  - conversation : /ask, /feedback et la configuration métier du chatbot ;
  - administration : analytiques, import/export, état du système.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SearchMode(str, Enum):
    """Les trois approches comparées dans le benchmark."""

    semantic = "semantic"   # recherche sémantique (recommandation du benchmark)
    keyword = "keyword"     # recherche par mots-clés (BM25) — baseline
    hybrid = "hybrid"       # fusion des deux (Reciprocal Rank Fusion)


def _one_line(value: str) -> str:
    return " ".join(value.split())


def _dedupe(values: list[str]) -> list[str]:
    seen: list[str] = []
    for v in values:
        v = _one_line(v)
        if v and v.lower() not in {s.lower() for s in seen}:
            seen.append(v)
    return seen


# ============================================================ annuaire (MCD)
class SiteIn(BaseModel):
    """Site physique d'une organisation (entité « Site » du MCD)."""

    label: str = Field(default="", max_length=120, description="Ex. « Siège », « Antenne Tarn »")
    address: str = Field(default="", max_length=300)
    postal_code: str = Field(default="", max_length=12)
    city: str = Field(default="", max_length=120)

    _strip = field_validator("label", "address", "postal_code", "city")(_one_line)


class SiteOut(SiteIn):
    id: int


class ContactIn(BaseModel):
    """Personne ou service à contacter (entité « Contact » du MCD)."""

    last_name: str = Field(default="", max_length=120)
    first_name: str = Field(default="", max_length=120)
    role: str = Field(default="", max_length=160, description="Fonction ou service (ex. « Accueil entreprises »)")
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40)

    _strip = field_validator("last_name", "first_name", "role", "phone")(_one_line)

    @field_validator("email")
    @classmethod
    def _email_shape(cls, v: str) -> str:
        v = v.strip()
        if v and ("@" not in v or " " in v):
            raise ValueError("adresse e-mail invalide")
        return v

    @property
    def display_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p)


class ContactOut(ContactIn):
    id: int


class DomainOut(BaseModel):
    """Domaine d'activité (entité du MCD) : nom + description, partagé entre organisations."""

    id: int
    name: str
    description: str = ""
    organizations: int = Field(default=0, description="Nombre d'organisations rattachées")


class DomainIn(BaseModel):
    """Domaine avec sa description (fichier de démarrage / import)."""

    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)


class DomainUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class OrganizationIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000,
                             description="Ce que fait l'organisation, pour qui, sur quels besoins "
                                         "(c'est ce texte qui est indexé pour la recherche)")
    website: str = Field(default="", max_length=300)
    keywords: list[str] = Field(default_factory=list, max_length=50,
                                description="Termes supplémentaires pour la recherche (acronymes, synonymes)")
    domains: list[str] = Field(default_factory=list, max_length=20, description="Noms de domaines d'activité")
    sites: list[SiteIn] = Field(default_factory=list, max_length=20)
    contacts: list[ContactIn] = Field(default_factory=list, max_length=20)
    active: bool = Field(default=True, description="Une organisation inactive reste en base mais n'est plus proposée")

    _strip = field_validator("name", "website")(_one_line)
    _lists = field_validator("keywords", "domains")(_dedupe)

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str) -> str:
        return v.strip()


class OrganizationOut(OrganizationIn):
    id: int
    sites: list[SiteOut] = Field(default_factory=list)
    contacts: list[ContactOut] = Field(default_factory=list)
    created_at: str
    updated_at: str


class OrganizationList(BaseModel):
    total: int
    items: list[OrganizationOut]


class ImportRequest(BaseModel):
    domains: list[DomainIn] = Field(default_factory=list, description="Descriptions de domaines (facultatif)")
    organizations: list[OrganizationIn]
    replace: bool = Field(default=False, description="Supprimer les organisations absentes de l'import")


class ImportResponse(BaseModel):
    created: int
    updated: int
    deleted: int
    total: int
    passages: int = Field(description="Taille de l'index après réindexation")


# ============================================================ recherche / conversation
class Source(BaseModel):
    doc_id: str = Field(description="`org:<id>` pour une organisation, chemin relatif pour un document")
    kind: str = Field(default="document", description="`organization` ou `document`")
    title: str
    source: str = Field(description="`annuaire` ou chemin du fichier dans le corpus")
    section: str = Field(default="", description="Chemin des titres de section (documents Markdown)")
    organization_id: int | None = None


class Hit(BaseModel):
    rank: int
    passage_id: str
    text: str
    score: float = Field(description="Score de pertinence du mode choisi, ramené dans [0, 1]")
    semantic_score: float | None = Field(default=None, description="Similarité cosinus (si calculée)")
    keyword_score: float | None = Field(default=None, description="Score BM25 brut (si calculé)")
    keyword_rank: int | None = Field(default=None, description="Rang dans le classement mots-clés (1 = meilleur)")
    source: Source


class Intent(str, Enum):
    orientation = "orientation"     # un ou plusieurs acteurs proposés (cas nominal)
    organization = "organization"   # fiche détaillée d'un acteur nommé dans la question
    document = "document"           # extrait d'une fiche documentaire seulement
    no_answer = "no_answer"         # rien d'assez fiable : on ne devine pas


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000, examples=["J'ai besoin d'une pièce métallique spécifique"])
    mode: SearchMode | None = Field(default=None, description="Défaut : CHATBOT_DEFAULT_MODE (semantic)")
    max_organizations: int | None = Field(default=None, ge=1, le=10,
                                          description="Défaut : valeur de la configuration admin")
    session_id: str | None = Field(default=None, max_length=64,
                                   description="Identifiant anonyme de session (haché côté serveur) "
                                               "pour compter les utilisateurs distincts")
    debug: bool = Field(default=False, description="Inclure les passages candidats bruts (`hits`)")


class OrganizationResult(OrganizationOut):
    score: float = Field(description="Meilleur score de pertinence de l'organisation pour la question")


class DocumentExtract(BaseModel):
    title: str
    source: str
    section: str = ""
    text: str = Field(description="Texte EXACT du passage (jamais généré)")
    score: float


class AskResponse(BaseModel):
    question: str
    mode: SearchMode
    intent: Intent
    answered: bool = Field(description="False si rien n'atteint le seuil de fiabilité")
    answer: str = Field(description="Texte à afficher, assemblé uniquement à partir de l'annuaire, "
                                    "des documents et des messages configurés")
    category: str | None = Field(default=None, description="Catégorie de besoin détectée (analytiques)")
    score: float | None = Field(default=None, description="Score du meilleur résultat")
    organizations: list[OrganizationResult] = Field(default_factory=list)
    documents: list[DocumentExtract] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list, description="Questions de relance proposées")
    query_id: int | None = Field(default=None, description="Identifiant du journal, à renvoyer sur /feedback")
    latency_ms: float
    hits: list[Hit] = Field(default_factory=list, description="Rempli seulement si debug=true")


class FeedbackRequest(BaseModel):
    query_id: int
    helpful: bool
    comment: str | None = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    ok: bool


# ============================================================ configuration métier
class Category(BaseModel):
    """Catégorie de besoin : sert à la détection (mots-clés) et aux relances proposées."""

    name: str = Field(min_length=2, max_length=80)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    example_question: str = Field(default="", max_length=200)

    _lists = field_validator("keywords")(_dedupe)


class ChatbotConfig(BaseModel):
    name: str = Field(default="Assistant Grand Albigeois", max_length=80)
    welcome_message: str = Field(max_length=1000, default=(
        "Bonjour ! Je suis le chatbot du Grand Albigeois. Comment puis-je vous aider aujourd'hui ? "
        "Je peux vous orienter vers les acteurs de l'innovation du territoire pour vos projets."))
    initial_suggestions: list[str] = Field(default_factory=lambda: [
        "J'ai besoin d'une pièce métallique spécifique",
        "Je cherche des aides pour innover",
        "Je recherche des solutions RH",
        "J'ai un projet de transition énergétique",
    ], max_length=8)
    suggestions_enabled: bool = Field(default=True, description="Proposer des questions de relance")
    orientation_enabled: bool = Field(default=True, description="Orienter vers les acteurs de l'annuaire "
                                                                "(sinon : extraits documentaires seulement)")
    analytics_enabled: bool = Field(default=True, description="Journaliser les questions (anonymisées)")
    max_organizations: int = Field(default=3, ge=1, le=10, description="Acteurs proposés au maximum par réponse")
    orientation_intro: str = Field(default="Voici les acteurs du territoire qui peuvent répondre à votre besoin :",
                                   max_length=500)
    orientation_outro: str = Field(default="Souhaitez-vous plus d'informations sur l'un de ces acteurs ?",
                                   max_length=500)
    no_answer_message: str = Field(max_length=1000, default=(
        "Je n'ai pas trouvé d'acteur ni de document correspondant à votre demande avec un niveau de "
        "fiabilité suffisant. Pouvez-vous préciser votre besoin ? Je peux vous orienter vers :"))
    categories: list[Category] = Field(default_factory=list, max_length=20)


class PublicConfig(BaseModel):
    """Partie de la configuration exposée au widget de chat (sans authentification)."""

    name: str
    welcome_message: str
    initial_suggestions: list[str]
    suggestions_enabled: bool


# ============================================================ analytiques
class PeriodTotals(BaseModel):
    conversations: int
    unique_sessions: int
    answered: int
    answer_rate: float | None
    feedback_count: int
    satisfaction_rate: float | None
    avg_latency_ms: float | None


class DayCount(BaseModel):
    date: str
    count: int


class NamedCount(BaseModel):
    name: str
    count: int


class QuestionCount(BaseModel):
    question: str
    count: int


class HourLatency(BaseModel):
    hour: int
    avg_latency_ms: float
    count: int


class AnalyticsSummary(BaseModel):
    days: int
    since: str
    totals: PeriodTotals
    previous: PeriodTotals = Field(description="Même période juste avant, pour les variations")
    per_day: list[DayCount]
    categories: list[NamedCount]
    top_questions: list[QuestionCount]
    unanswered_questions: list[QuestionCount] = Field(description="À exploiter pour enrichir l'annuaire")
    top_organizations: list[NamedCount]
    latency_by_hour: list[HourLatency]


class QueryRecord(BaseModel):
    id: int
    ts: str
    question: str
    answered: bool
    intent: str
    category: str | None
    top_score: float | None
    latency_ms: float
    mode: str
    organizations: list[str]
    helpful: bool | None
    feedback_comment: str | None


class QueryList(BaseModel):
    total: int
    items: list[QueryRecord]


# ============================================================ système
class DocumentInfo(BaseModel):
    doc_id: str
    kind: str
    title: str
    source: str
    passages: int


class IngestResponse(BaseModel):
    documents: int
    organizations: int
    passages: int
    seconds: float
    model: str


class HealthResponse(BaseModel):
    status: str
    version: str
    model: str
    documents: int
    organizations: int
    passages: int
