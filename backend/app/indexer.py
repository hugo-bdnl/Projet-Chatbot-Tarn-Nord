"""Alimente l'index de recherche à partir des deux sources : fiches du corpus + organisations de l'annuaire."""

from __future__ import annotations

import logging

from .config import Settings
from .directory import DirectoryRepository, organization_to_document
from .directory.render import doc_id_for
from .schemas import OrganizationOut
from .search import IngestReport, SearchEngine

logger = logging.getLogger(__name__)


class Indexer:
    def __init__(self, engine: SearchEngine, repo: DirectoryRepository, settings: Settings) -> None:
        self.engine = engine
        self.repo = repo
        self.settings = settings

    def rebuild(self) -> IngestReport:
        docs = self.engine.corpus_documents(self.settings.corpus_dir)
        if not docs:
            logger.info("Aucune fiche documentaire dans %s", self.settings.corpus_dir)
        orgs = [organization_to_document(o) for o in self.repo.all_active()]
        return self.engine.reindex(docs + orgs)

    def sync_organization(self, org: OrganizationOut | None, org_id: int | None = None) -> int:
        """Après création / modification / suppression d'une organisation. Renvoie le nombre de passages."""
        if org is None or not org.active:
            target = org_id if org is None else org.id
            if target is not None:
                self.engine.delete_document(doc_id_for(target))
            return 0
        return self.engine.upsert_document(organization_to_document(org))
