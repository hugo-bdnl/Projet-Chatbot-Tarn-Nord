"""API HTTP (FastAPI) du chatbot territorial.

Public  : GET /health, GET /config, POST /ask, POST /feedback, GET /organizations[/{id}], GET /domains, GET /documents
Admin   : /admin/organizations (CRUD, import, export), /admin/domains/{id}, /admin/reindex,
          /admin/analytics[/questions], /admin/config (GET, PUT, reset) — header X-API-Key
Swagger : GET /docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api import admin_router, public_router
from .bootstrap import build_state, startup
from .config import Settings, get_settings

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper(),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.api_key:
        logger.warning("CHATBOT_API_KEY non définie : les endpoints /admin/* sont ouverts (mode développement)")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = await run_in_threadpool(build_state, settings)
        await run_in_threadpool(startup, state)
        app.state.chatbot = state
        yield

    app = FastAPI(
        title="Chatbot territorial — orientation vers les acteurs de l'innovation",
        version=__version__,
        description="Oriente les industriels vers les acteurs de l'innovation du territoire à partir d'un "
                    "annuaire et de fiches documentaires, par recherche sémantique. Sans IA générative : "
                    "chaque réponse est assemblée à partir de données existantes, jamais inventée.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "X-API-Key"],
    )
    app.include_router(public_router)
    app.include_router(admin_router)
    return app


app = create_app()
