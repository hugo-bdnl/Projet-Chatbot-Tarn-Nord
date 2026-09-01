"""Assemblage des composants (partagé par l'API et la CLI)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .analytics import Analytics
from .assistant import Assistant
from .chatbot_config import ConfigStore
from .config import Settings
from .db import Database
from .directory import DirectoryRepository, ImportResult, load_seed_file
from .indexer import Indexer
from .search import IngestReport, SearchEngine

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    settings: Settings
    db: Database
    repo: DirectoryRepository
    config_store: ConfigStore
    analytics: Analytics
    engine: SearchEngine
    indexer: Indexer
    assistant: Assistant


def build_state(settings: Settings) -> AppState:
    db = Database(settings.db_file)
    repo = DirectoryRepository(db)
    config_store = ConfigStore(db)
    analytics = Analytics(db, config_store.analytics_salt(), settings.analytics_retention_days)
    engine = SearchEngine(settings)   # charge le modèle d'embedding (~10 s)
    indexer = Indexer(engine, repo, settings)
    assistant = Assistant(engine, repo, config_store, analytics, settings)
    return AppState(settings, db, repo, config_store, analytics, engine, indexer, assistant)


def seed_if_empty(state: AppState) -> ImportResult | None:
    s = state.settings
    if not s.auto_seed or state.repo.count(active_only=False) > 0:
        return None
    if not s.seed_file.is_file():
        logger.info("Annuaire vide et pas de fichier de démarrage (%s)", s.seed_file)
        return None
    seed = load_seed_file(s.seed_file)
    state.repo.upsert_domains(seed.domains)
    result = state.repo.import_many(seed.organizations)
    logger.info("Annuaire initialisé depuis %s : %d organisations", s.seed_file, result.created)
    return result


def index_if_empty(state: AppState) -> IngestReport | None:
    if not state.settings.auto_ingest or not state.engine.is_empty():
        return None
    logger.info("Index vide : construction depuis le corpus et l'annuaire")
    return state.indexer.rebuild()


def startup(state: AppState) -> None:
    seed_if_empty(state)
    index_if_empty(state)
    purged = state.analytics.purge()
    if purged:
        logger.info("Journal des questions : %d entrées purgées (> %d jours)",
                    purged, state.settings.analytics_retention_days)
