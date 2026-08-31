"""Moteur de recherche : index sémantique (ChromaDB), index mots-clés (BM25), fusion, seuil de fiabilité.

Il ne connaît ni l'annuaire ni la conversation : il indexe des RawDocument (fiches Markdown ou
organisations projetées en texte) et renvoie des passages classés. La composition de la réponse est
faite par `app.assistant`.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import Settings
from ..ingestion import Passage, RawDocument, chunk_document
from ..schemas import Hit, SearchMode, Source
from .embeddings import Embedder
from .keyword import BM25Index
from .semantic import ChromaStore

logger = logging.getLogger(__name__)


@dataclass
class IngestReport:
    documents: int
    organizations: int
    passages: int
    seconds: float


@dataclass
class _Candidate:
    passage: Passage
    score: float
    semantic_score: float | None = None
    keyword_score: float | None = None
    keyword_rank: int | None = None


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """RRF : score(d) = somme sur les listes de 1 / (k + rang), le rang commençant à 1."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + rank)
    return fused


def _to_source(p: Passage) -> Source:
    org_id = int(p.doc_id[4:]) if p.kind == "organization" and p.doc_id[4:].isdigit() else None
    return Source(doc_id=p.doc_id, kind=p.kind, title=p.title, source=p.source, section=p.section,
                  organization_id=org_id)


class SearchEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.RLock()
        self.embedder = Embedder(settings.embedding_model, settings.embedding_batch_size)
        self.store = ChromaStore(settings.data_dir, settings.collection_name)
        self.keyword_index = BM25Index(self.store.all_passages())
        logger.info("Index chargé : %d passages", self.store.count())

    # ------------------------------------------------------------------ état
    def count_passages(self) -> int:
        return self.store.count()

    def list_documents(self) -> list[dict]:
        return self.store.list_documents()

    def is_empty(self) -> bool:
        return self.store.count() == 0

    # ------------------------------------------------------------- indexation
    def _chunk(self, doc: RawDocument) -> list[Passage]:
        if doc.kind == "organization":
            return chunk_document(doc, self.settings.org_chunk_size, 0)
        return chunk_document(doc, self.settings.chunk_size, self.settings.chunk_overlap)

    def reindex(self, docs: list[RawDocument]) -> IngestReport:
        """Reconstruit intégralement l'index (idempotent)."""
        t0 = time.perf_counter()
        passages: list[Passage] = []
        for doc in docs:
            passages.extend(self._chunk(doc))
        n_orgs = sum(1 for d in docs if d.kind == "organization")
        logger.info("Indexation : %d documents + %d organisations -> %d passages",
                    len(docs) - n_orgs, n_orgs, len(passages))
        embeddings = self.embedder.embed_passages([p.embed_text for p in passages])
        with self._lock:
            self.store.reset()
            if passages:
                self.store.add(passages, embeddings)
            self.keyword_index = BM25Index(passages)
        report = IngestReport(documents=len(docs) - n_orgs, organizations=n_orgs, passages=len(passages),
                              seconds=round(time.perf_counter() - t0, 2))
        logger.info("Indexation terminée en %.1fs", report.seconds)
        return report

    def upsert_document(self, doc: RawDocument) -> int:
        """Remplace les passages d'un seul document (mise à jour d'une organisation)."""
        passages = self._chunk(doc)
        embeddings = self.embedder.embed_passages([p.embed_text for p in passages])
        with self._lock:
            self.store.delete_document(doc.doc_id)
            if passages:
                self.store.add(passages, embeddings)
            self.keyword_index = BM25Index(self.store.all_passages())
        return len(passages)

    def delete_document(self, doc_id: str) -> None:
        with self._lock:
            self.store.delete_document(doc_id)
            self.keyword_index = BM25Index(self.store.all_passages())

    # -------------------------------------------------------------- recherche
    def _semantic(self, question: str, n: int, embedding: list[float] | None = None) -> list[_Candidate]:
        emb = embedding or self.embedder.embed_query(question)
        return [_Candidate(h.passage, h.score, semantic_score=h.score) for h in self.store.query(emb, n)]

    def _keyword(self, question: str, n: int) -> list[_Candidate]:
        hits = self.keyword_index.query(question, n)
        top = hits[0].score if hits else 0.0
        return [_Candidate(h.passage, (h.score / top) if top > 0 else 0.0, keyword_score=h.score, keyword_rank=i)
                for i, h in enumerate(hits, start=1)]

    def _hybrid(self, question: str, n: int) -> list[_Candidate]:
        pool = max(n, self.settings.candidate_pool)
        emb = self.embedder.embed_query(question)
        sem = self._semantic(question, pool, emb)
        kw = self._keyword(question, pool)
        by_id: dict[str, _Candidate] = {}
        for c in sem:
            by_id[c.passage.passage_id] = _Candidate(c.passage, 0.0, semantic_score=c.semantic_score)
        for c in kw:
            cur = by_id.setdefault(c.passage.passage_id, _Candidate(c.passage, 0.0))
            cur.keyword_score = c.keyword_score
            cur.keyword_rank = c.keyword_rank
        # les candidats remontés par BM25 seul reçoivent aussi leur similarité : la règle de fiabilité
        # reste sémantique pour tous (un simple mot commun ne suffit pas à répondre)
        missing = [pid for pid, c in by_id.items() if c.semantic_score is None]
        for pid, score in self.store.similarities(emb, missing).items():
            by_id[pid].semantic_score = score
        fused = reciprocal_rank_fusion(
            [[c.passage.passage_id for c in sem], [c.passage.passage_id for c in kw]],
            k=self.settings.rrf_k,
        )
        top = max(fused.values(), default=0.0)
        for pid, cand in by_id.items():
            cand.score = fused[pid] / top if top > 0 else 0.0
        return sorted(by_id.values(), key=lambda c: c.score, reverse=True)[:n]

    def search(self, question: str, mode: SearchMode = SearchMode.semantic,
               top_k: int | None = None) -> list[Hit]:
        n = top_k or self.settings.default_top_k
        with self._lock:
            if mode == SearchMode.semantic:
                cands = self._semantic(question, n)
            elif mode == SearchMode.keyword:
                cands = self._keyword(question, n)
            else:
                cands = self._hybrid(question, n)
        return [Hit(rank=i, passage_id=c.passage.passage_id, text=c.passage.text,
                    score=round(c.score, 4),
                    semantic_score=None if c.semantic_score is None else round(c.semantic_score, 4),
                    keyword_score=None if c.keyword_score is None else round(c.keyword_score, 4),
                    keyword_rank=c.keyword_rank,
                    source=_to_source(c.passage))
                for i, c in enumerate(cands, start=1)]

    def is_confident(self, hit: Hit, mode: SearchMode) -> bool:
        """Règle de fiabilité : un passage n'est retenu que s'il est jugé pertinent.

        - sémantique : similarité cosinus >= min_score ;
        - mots-clés  : au moins un mot de la question présent (BM25 > 0) ;
        - hybride    : critère sémantique (calculé pour tous les candidats), BM25 ne servant qu'au classement.
        """
        if mode == SearchMode.keyword:
            return (hit.keyword_score or 0.0) > 0.0
        if hit.semantic_score is None:
            return (hit.keyword_score or 0.0) > 0.0
        if hit.semantic_score >= self.settings.min_score:
            return True
        # hybride : accord lexical fort (top BM25) + sémantique quasi au seuil
        return (mode == SearchMode.hybrid
                and hit.keyword_rank is not None
                and hit.keyword_rank <= self.settings.hybrid_keyword_top
                and hit.semantic_score >= self.settings.min_score - self.settings.hybrid_tolerance)

    # ------------------------------------------------------------ utilitaire
    @staticmethod
    def corpus_documents(corpus_dir: Path) -> list[RawDocument]:
        from ..ingestion import load_corpus

        return load_corpus(corpus_dir) if Path(corpus_dir).is_dir() else []
