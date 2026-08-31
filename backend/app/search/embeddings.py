"""Calcul des « empreintes numériques » (embeddings) avec sentence-transformers, sur CPU."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class Embedder:
    """Enveloppe minimale autour de SentenceTransformer.

    Les modèles de la famille E5 attendent les préfixes « query: » / « passage: »
    (recherche asymétrique question -> passage). On les ajoute automatiquement.
    Les vecteurs sont normalisés : le produit scalaire vaut la similarité cosinus.
    """

    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        from sentence_transformers import SentenceTransformer

        t0 = time.perf_counter()
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name, device="cpu")
        self._is_e5 = "e5" in model_name.lower().split("/")[-1]
        self.dimension = int(self.model.get_sentence_embedding_dimension() or 0)
        logger.info("Modèle %s chargé en %.1fs (dim=%d, préfixes E5=%s)",
                    model_name, time.perf_counter() - t0, self.dimension, self._is_e5)

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts, batch_size=self.batch_size, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefix = "passage: " if self._is_e5 else ""
        return self._encode([prefix + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        prefix = "query: " if self._is_e5 else ""
        return self._encode([prefix + text])[0]
