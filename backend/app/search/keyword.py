"""Recherche par mots-clés (BM25) — la « baseline » du benchmark.

Volontairement simple : minuscules, accents retirés, mots vides français supprimés,
pas de lemmatisation. Elle illustre la limite décrite dans la note de synthèse :
sans mot commun entre la question et le passage, elle ne trouve rien.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..ingestion.chunker import Passage

FRENCH_STOPWORDS = frozenset("""
a ai aie au aux avec ce ces cet cette ceci cela ca c d dans de des du elle elles en est et etre
eu il ils j je l la le les leur leurs lui ma mais me meme mes moi mon n ne ni nos notre nous on ont
ou par pas pour qu que quel quelle quelles quels qui s sa se ses si son sont sur t ta te tes toi ton
tu un une vos votre vous y quand comment combien puis peut peux dois doit faut faire fait ete
""".split())

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_APOSTROPHES = str.maketrans({"'": " ", "’": " ", "ʼ": " "})


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def tokenize(text: str) -> list[str]:
    text = strip_accents(text.lower()).translate(_APOSTROPHES)
    return [t for t in _TOKEN_RE.findall(text) if t not in FRENCH_STOPWORDS and len(t) > 1]


@dataclass
class KeywordHit:
    passage: Passage
    score: float   # score BM25 brut (>= 0)


class BM25Index:
    def __init__(self, passages: list[Passage]) -> None:
        from rank_bm25 import BM25Okapi

        self._passages = list(passages)
        corpus_tokens = [tokenize(p.embed_text) for p in self._passages]
        # BM25Okapi ne supporte pas un corpus vide ; on garde un index « nul » dans ce cas
        self._bm25 = BM25Okapi(corpus_tokens) if corpus_tokens else None

    def __len__(self) -> int:
        return len(self._passages)

    def query(self, question: str, top_k: int) -> list[KeywordHit]:
        if self._bm25 is None:
            return []
        tokens = tokenize(question)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [KeywordHit(passage=self._passages[i], score=float(scores[i]))
                for i in order if scores[i] > 0]
