from app.ingestion.chunker import chunk_document, chunk_text, split_markdown_sections
from app.ingestion.loaders import RawDocument

MD = """# Horaires de la mairie

Introduction générale.

## Mairie de Brézac

Ouverte du lundi au vendredi.

### Été

Fermée le samedi en juillet et août.

## Contact

Téléphone 05 00 12 34 56.
"""


def test_split_markdown_sections_builds_heading_path():
    sections = split_markdown_sections(MD)
    assert sections == [
        ("", "Introduction générale."),
        ("Mairie de Brézac", "Ouverte du lundi au vendredi."),
        ("Mairie de Brézac > Été", "Fermée le samedi en juillet et août."),
        ("Contact", "Téléphone 05 00 12 34 56."),
    ]


def test_split_markdown_ignores_headings_inside_code_blocks():
    text = "## A\n\n```\n# pas un titre\n```\n\n## B\n\nfin"
    sections = split_markdown_sections(text)
    assert [s for s, _ in sections] == ["A", "B"]
    assert "# pas un titre" in sections[0][1]


def test_chunk_text_short_text_is_single_chunk():
    assert chunk_text("Bonjour.", size=100) == ["Bonjour."]
    assert chunk_text("   \n\n  ", size=100) == []


def test_chunk_text_respects_size_and_overlap():
    paragraphs = [f"Paragraphe numéro {i} avec un peu de contenu pour remplir." for i in range(30)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, size=300, overlap=60)
    assert len(chunks) > 1
    assert all(len(c) <= 300 + 60 for c in chunks)
    # tout le contenu est conservé
    joined = " ".join(chunks)
    assert all(p in joined for p in paragraphs)
    # le chevauchement reprend la fin du chunk précédent
    tail = chunks[0][-30:]
    assert tail.split(" ", 1)[-1][:10] in chunks[1]


def test_chunk_text_splits_overlong_paragraph_on_sentences():
    text = "Phrase une. " * 100
    chunks = chunk_text(text, size=200, overlap=0)
    assert all(len(c) <= 200 for c in chunks)
    assert "\n\n" not in chunks[0]   # phrases d'un même paragraphe séparées par un espace


def test_chunk_document_numbers_passages_and_keeps_sections():
    doc = RawDocument(doc_id="horaires.md", title="Horaires de la mairie", source="horaires.md", text=MD)
    passages = chunk_document(doc, size=700, overlap=100)
    assert [p.position for p in passages] == list(range(len(passages)))
    assert passages[0].passage_id == "horaires.md#0"
    assert passages[2].section == "Mairie de Brézac > Été"
    assert passages[2].embed_text.startswith("Horaires de la mairie — Mairie de Brézac > Été")
    assert all(p.title == "Horaires de la mairie" for p in passages)
