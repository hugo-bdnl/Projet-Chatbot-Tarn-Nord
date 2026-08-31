"""Lecture des documents sources (Markdown, texte, HTML, PDF) -> texte brut + titre."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf"}


@dataclass(frozen=True)
class RawDocument:
    doc_id: str      # chemin relatif au corpus (documents) ou `org:<id>` (organisations) — identifiant stable
    title: str
    source: str      # chemin du fichier, ou `annuaire`
    text: str
    kind: str = "document"   # `document` | `organization`


def _title_from_filename(path: Path) -> str:
    stem = path.stem.replace("_", " ").replace("-", " ").strip()
    return stem[:1].upper() + stem[1:] if stem else path.name


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)


def _load_markdown(path: Path) -> tuple[str, str]:
    # les commentaires HTML (notes de rédaction, avertissements internes) ne sont ni indexés ni affichés
    text = _HTML_COMMENT_RE.sub("", path.read_text(encoding="utf-8", errors="replace"))
    m = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    title = m.group(1).strip() if m else _title_from_filename(path)
    return title, text


def _load_text(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    first = text.strip().splitlines()[0].strip() if text.strip() else ""
    title = first if 0 < len(first) <= 120 else _title_from_filename(path)
    return title, text


def _load_html(path: Path) -> tuple[str, str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.h1:
        title = soup.h1.get_text(" ", strip=True)
    text = soup.get_text("\n", strip=True)
    return title or _title_from_filename(path), text


def _load_pdf(path: Path) -> tuple[str, str]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(p for p in pages if p)
    meta_title = reader.metadata.get("/Title") if reader.metadata else None
    title = str(meta_title).strip() if meta_title else _title_from_filename(path)
    return title, text


_LOADERS = {
    ".md": _load_markdown,
    ".markdown": _load_markdown,
    ".txt": _load_text,
    ".html": _load_html,
    ".htm": _load_html,
    ".pdf": _load_pdf,
}


def load_file(path: Path, corpus_dir: Path) -> RawDocument | None:
    """Charge un fichier ; renvoie None s'il n'est pas supporté ou vide."""
    loader = _LOADERS.get(path.suffix.lower())
    if loader is None:
        return None
    try:
        title, text = loader(path)
    except Exception as exc:  # fichier corrompu, PDF chiffré, etc. : on journalise, on continue
        logger.warning("Impossible de lire %s : %s", path, exc)
        return None
    text = text.strip()
    if not text:
        logger.warning("Document vide ignoré : %s", path)
        return None
    rel = path.relative_to(corpus_dir).as_posix()
    return RawDocument(doc_id=rel, title=title, source=rel, text=text)


def load_corpus(corpus_dir: Path) -> list[RawDocument]:
    """Parcourt récursivement le dossier corpus (ordre déterministe)."""
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.is_dir():
        raise FileNotFoundError(f"Dossier corpus introuvable : {corpus_dir.resolve()}")
    docs: list[RawDocument] = []
    for path in sorted(corpus_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and not path.name.startswith("."):
            doc = load_file(path, corpus_dir)
            if doc:
                docs.append(doc)
    return docs
