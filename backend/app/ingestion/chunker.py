"""Découpage des documents en passages.

Stratégie :
  1. un document Markdown est d'abord découpé par ses titres (##, ###…) ;
     le titre de niveau 1 est le titre du document, pas une section ;
  2. chaque section est ensuite découpée en fenêtres d'environ `chunk_size`
     caractères, en respectant les paragraphes puis les phrases, avec un
     chevauchement `chunk_overlap` pour ne pas couper une information en deux.
Chaque passage garde le chemin de ses titres (« Horaires > Été ») : il est
affiché à l'usager et injecté dans le texte embarqué pour donner du contexte.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .loaders import RawDocument

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")
_WS_RE = re.compile(r"[ \t]+")


@dataclass(frozen=True)
class Passage:
    passage_id: str
    doc_id: str
    title: str
    source: str
    section: str
    position: int
    text: str
    kind: str = "document"   # `document` | `organization`

    @property
    def embed_text(self) -> str:
        """Texte réellement indexé : titre + section + passage (contexte pour l'embedding et BM25)."""
        head = self.title if not self.section else f"{self.title} — {self.section}"
        return f"{head}\n{self.text}"


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_markdown_sections(text: str) -> list[tuple[str, str]]:
    """Renvoie [(chemin_de_section, corps)] ; le chemin exclut le titre de niveau 1."""
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []   # (niveau, titre)
    buffer: list[str] = []
    in_code = False

    def flush() -> None:
        body = _clean("\n".join(buffer))
        if body:
            path = " > ".join(t for lvl, t in stack if lvl >= 2)
            sections.append((path, body))
        buffer.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            buffer.append(line)
            continue
        m = None if in_code else _HEADING_RE.match(line)
        if m:
            flush()
            level, heading = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading))
        else:
            buffer.append(line)
    flush()
    return sections


def _split_long(unit: str, size: int) -> list[str]:
    """Coupe une unité trop longue (paragraphe) en phrases, puis en dur si nécessaire."""
    pieces: list[str] = []
    for sentence in _SENTENCE_RE.split(unit):
        while len(sentence) > size:
            cut = sentence.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            pieces.append(sentence)
    return pieces


def chunk_text(text: str, size: int = 700, overlap: int = 100) -> list[str]:
    """Découpe un texte en fenêtres d'environ `size` caractères avec chevauchement."""
    if size <= 0:
        raise ValueError("size doit être > 0")
    overlap = max(0, min(overlap, size // 2))
    text = _clean(text)
    if not text:
        return []
    if len(text) <= size:
        return [text]

    # unités = (texte, séparateur avec l'unité précédente) : un paragraphe entier commence
    # après une ligne vide ; les phrases issues d'un paragraphe trop long se suivent d'un espace.
    units: list[tuple[str, str]] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) > size:
            for i, sentence in enumerate(_split_long(para, size)):
                units.append((sentence, "\n\n" if i == 0 else " "))
        else:
            units.append((para, "\n\n"))

    chunks: list[str] = []
    current = ""
    for unit, sep in units:
        candidate = f"{current}{sep}{unit}" if current else unit
        if len(candidate) <= size or not current:
            current = candidate
            continue
        chunks.append(current)
        tail = current[-overlap:] if overlap else ""
        if tail and " " in tail:
            tail = tail[tail.index(" ") + 1:]   # ne pas démarrer au milieu d'un mot
        current = f"{tail} {unit}".strip() if tail else unit
    if current:
        chunks.append(current)
    return chunks


def chunk_document(doc: RawDocument, size: int = 700, overlap: int = 100) -> list[Passage]:
    """Document -> passages numérotés, avec le chemin des sections Markdown."""
    is_markdown = doc.source.lower().endswith((".md", ".markdown"))
    sections = split_markdown_sections(doc.text) if is_markdown else [("", doc.text)]

    passages: list[Passage] = []
    position = 0
    for section, body in sections:
        for text in chunk_text(body, size=size, overlap=overlap):
            passages.append(Passage(
                passage_id=f"{doc.doc_id}#{position}",
                doc_id=doc.doc_id,
                title=doc.title,
                source=doc.source,
                section=section,
                position=position,
                text=text,
                kind=doc.kind,
            ))
            position += 1
    return passages
