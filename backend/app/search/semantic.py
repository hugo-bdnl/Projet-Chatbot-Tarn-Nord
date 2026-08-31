"""Index vectoriel persistant (ChromaDB embarqué, distance cosinus)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ..ingestion.chunker import Passage

logger = logging.getLogger(__name__)

_ADD_BATCH = 256


@dataclass
class StoredHit:
    passage: Passage
    score: float   # similarité cosinus dans [-1, 1] (en pratique [0, 1])


def _passage_from_record(pid: str, text: str, meta: dict) -> Passage:
    return Passage(
        passage_id=pid,
        doc_id=str(meta.get("doc_id", "")),
        title=str(meta.get("title", "")),
        source=str(meta.get("source", "")),
        section=str(meta.get("section", "")),
        position=int(meta.get("position", 0)),
        text=text,
        kind=str(meta.get("kind", "document")),
    )


class ChromaStore:
    def __init__(self, data_dir: Path, collection_name: str = "passages") -> None:
        import chromadb

        data_dir = Path(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(data_dir))
        self._name = collection_name
        self._collection = self._get_or_create()

    def _get_or_create(self):
        # embedding_function=None : nous fournissons toujours nos propres vecteurs
        # (sinon Chroma téléchargerait un modèle anglais par défaut).
        return self._client.get_or_create_collection(
            name=self._name, metadata={"hnsw:space": "cosine"}, embedding_function=None,
        )

    # --- écriture ---------------------------------------------------------
    def reset(self) -> None:
        try:
            self._client.delete_collection(self._name)
        except Exception:  # collection absente
            pass
        self._collection = self._get_or_create()

    def add(self, passages: list[Passage], embeddings: list[list[float]]) -> None:
        if len(passages) != len(embeddings):
            raise ValueError("passages et embeddings doivent avoir la même longueur")
        for i in range(0, len(passages), _ADD_BATCH):
            batch = passages[i:i + _ADD_BATCH]
            self._collection.add(
                ids=[p.passage_id for p in batch],
                embeddings=embeddings[i:i + _ADD_BATCH],
                documents=[p.text for p in batch],
                metadatas=[{
                    "doc_id": p.doc_id, "title": p.title, "source": p.source,
                    "section": p.section, "position": p.position, "kind": p.kind,
                } for p in batch],
            )

    def delete_document(self, doc_id: str) -> None:
        """Supprime tous les passages d'un document (mise à jour incrémentale de l'annuaire)."""
        self._collection.delete(where={"doc_id": {"$eq": doc_id}})

    # --- lecture ----------------------------------------------------------
    def count(self) -> int:
        return self._collection.count()

    def query(self, embedding: list[float], top_k: int) -> list[StoredHit]:
        n = self.count()
        if n == 0:
            return []
        res = self._collection.query(
            query_embeddings=[embedding], n_results=min(top_k, n),
            include=["documents", "metadatas", "distances"],
        )
        hits: list[StoredHit] = []
        for pid, text, meta, dist in zip(res["ids"][0], res["documents"][0],
                                         res["metadatas"][0], res["distances"][0]):
            hits.append(StoredHit(passage=_passage_from_record(pid, text, meta or {}),
                                  score=1.0 - float(dist)))
        return hits

    def similarities(self, embedding: list[float], ids: list[str]) -> dict[str, float]:
        """Similarité cosinus entre une requête et des passages désignés (vecteurs normalisés -> produit scalaire)."""
        if not ids:
            return {}
        res = self._collection.get(ids=ids, include=["embeddings"])
        out: dict[str, float] = {}
        for pid, vec in zip(res["ids"], res["embeddings"]):
            out[pid] = float(sum(a * b for a, b in zip(embedding, vec)))
        return out

    def all_passages(self) -> list[Passage]:
        """Tous les passages (pour construire l'index mots-clés en mémoire)."""
        n = self.count()
        if n == 0:
            return []
        res = self._collection.get(include=["documents", "metadatas"], limit=n)
        passages = [_passage_from_record(pid, text, meta or {})
                    for pid, text, meta in zip(res["ids"], res["documents"], res["metadatas"])]
        passages.sort(key=lambda p: (p.doc_id, p.position))
        return passages

    def list_documents(self) -> list[dict]:
        docs: dict[str, dict] = {}
        for p in self.all_passages():
            entry = docs.setdefault(p.doc_id, {"doc_id": p.doc_id, "kind": p.kind, "title": p.title,
                                               "source": p.source, "passages": 0})
            entry["passages"] += 1
        return sorted(docs.values(), key=lambda d: (d["kind"], d["doc_id"]))
