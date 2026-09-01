from app.ingestion.chunker import Passage
from app.search.keyword import BM25Index, strip_accents, tokenize


def _p(i: int, text: str, title: str = "Doc") -> Passage:
    return Passage(passage_id=f"d{i}#0", doc_id=f"d{i}", title=title, source=f"d{i}.md",
                   section="", position=0, text=text)


def test_strip_accents():
    assert strip_accents("déchèterie élève à") == "decheterie eleve a"


def test_tokenize_removes_stopwords_and_apostrophes():
    tokens = tokenize("Quels sont les horaires d'ouverture de la mairie ?")
    assert tokens == ["horaires", "ouverture", "mairie"]
    assert tokenize("L’école") == ["ecole"]


def test_bm25_finds_document_with_shared_words():
    idx = BM25Index([
        _p(1, "Horaires d'ouverture de la mairie : du lundi au vendredi."),
        _p(2, "Tarifs de la piscine intercommunale."),
        _p(3, "Collecte des ordures ménagères le lundi."),
    ])
    hits = idx.query("Quels sont les horaires de la mairie ?", top_k=3)
    assert hits and hits[0].passage.doc_id == "d1"
    assert all(h.score > 0 for h in hits)


def test_bm25_returns_nothing_without_common_words():
    idx = BM25Index([_p(1, "Horaires d'ouverture de la mairie.")])
    # reformulation sans mot commun : la limite des mots-clés décrite dans le benchmark
    assert idx.query("Quand puis-je venir vous voir ?", top_k=3) == []
    assert idx.query("de la les", top_k=3) == []   # uniquement des mots vides


def test_bm25_empty_index():
    idx = BM25Index([])
    assert len(idx) == 0
    assert idx.query("mairie", top_k=3) == []
