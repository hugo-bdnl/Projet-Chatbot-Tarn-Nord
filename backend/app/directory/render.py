"""Projection d'une organisation en texte : (1) document indexé pour la recherche, (2) fiche affichée.

Le texte indexé se limite à ce qui décrit le BESOIN couvert (description, domaines, mots-clés) :
villes, adresses et numéros de téléphone n'aident pas la recherche et sont affichés depuis la base.
"""

from __future__ import annotations

import re

from ..ingestion.loaders import RawDocument
from ..schemas import OrganizationOut

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def doc_id_for(org_id: int) -> str:
    return f"org:{org_id}"


def org_id_from_doc_id(doc_id: str) -> int | None:
    if doc_id.startswith("org:") and doc_id[4:].isdigit():
        return int(doc_id[4:])
    return None


def short_description(text: str, max_len: int = 180) -> str:
    """Première phrase (ou début) de la description, pour les listes."""
    text = " ".join(text.split())
    if not text:
        return ""
    first = _SENTENCE_END.split(text, maxsplit=1)[0]
    if len(first) <= max_len:
        return first
    cut = first.rfind(" ", 0, max_len)
    return first[: cut if cut > max_len // 2 else max_len].rstrip(" ,;:") + "…"


def organization_to_document(org: OrganizationOut) -> RawDocument:
    lines = [org.description.strip()]
    if org.domains:
        lines.append("Domaines d'activité : " + ", ".join(org.domains) + ".")
    if org.keywords:
        lines.append("Mots-clés : " + ", ".join(org.keywords) + ".")
    # NB : villes, adresses et coordonnées ne sont pas indexées (tous les acteurs sont territoriaux ;
    # « Albi » dans une question hors sujet ferait remonter n'importe quelle fiche).
    return RawDocument(doc_id=doc_id_for(org.id), title=org.name, source="annuaire",
                       text="\n\n".join(line for line in lines if line), kind="organization")


def organization_card(org: OrganizationOut) -> str:
    """Fiche détaillée en texte brut (réponse quand l'usager nomme un acteur)."""
    lines = [org.name, ""]
    if org.description:
        lines += [org.description.strip(), ""]
    if org.domains:
        lines.append("Domaines d'activité : " + ", ".join(org.domains))
    for s in org.sites:
        place = ", ".join(p for p in (s.address, " ".join(x for x in (s.postal_code, s.city) if x)) if p)
        if place:
            lines.append(f"Adresse{' (' + s.label + ')' if s.label else ''} : {place}")
    for c in org.contacts:
        who = c.display_name
        if c.role:
            who = f"{who} ({c.role})" if who else c.role
        coords = " — ".join(x for x in (c.email, c.phone) if x)
        if who or coords:
            lines.append("Contact : " + " — ".join(x for x in (who, coords) if x))
    if org.website:
        lines.append(f"Site web : {org.website}")
    return "\n".join(lines).strip()
