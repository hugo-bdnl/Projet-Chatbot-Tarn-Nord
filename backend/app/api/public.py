"""Endpoints publics : widget de chat et consultation de l'annuaire."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from .. import __version__
from ..bootstrap import AppState
from ..schemas import (AskRequest, AskResponse, DocumentInfo, DomainOut, FeedbackRequest, FeedbackResponse,
                       HealthResponse, OrganizationList, OrganizationOut, PublicConfig)
from .deps import get_state

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["système"])
def health(state: AppState = Depends(get_state)) -> HealthResponse:
    docs = state.engine.list_documents()
    return HealthResponse(status="ok", version=__version__, model=state.settings.embedding_model,
                          documents=sum(1 for d in docs if d["kind"] == "document"),
                          organizations=state.repo.count(), passages=state.engine.count_passages())


@router.get("/config", response_model=PublicConfig, tags=["conversation"])
def public_config(state: AppState = Depends(get_state)) -> PublicConfig:
    cfg = state.config_store.get()
    return PublicConfig(name=cfg.name, welcome_message=cfg.welcome_message,
                        initial_suggestions=cfg.initial_suggestions if cfg.suggestions_enabled else [],
                        suggestions_enabled=cfg.suggestions_enabled)


@router.post("/ask", response_model=AskResponse, tags=["conversation"])
async def ask(payload: AskRequest, state: AppState = Depends(get_state)) -> AskResponse:
    """Besoin exprimé -> acteurs de l'innovation pertinents (+ extrait documentaire), ou « non trouvé »."""
    return await run_in_threadpool(state.assistant.ask, payload)


@router.post("/feedback", response_model=FeedbackResponse, tags=["conversation"])
def feedback(payload: FeedbackRequest, state: AppState = Depends(get_state)) -> FeedbackResponse:
    """Évaluation d'une réponse par l'usager (REQ-FUNC.3) ; `query_id` vient de la réponse de /ask."""
    ok = state.analytics.feedback(payload.query_id, payload.helpful, payload.comment)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question inconnue ou journalisation désactivée")
    return FeedbackResponse(ok=True)


@router.get("/organizations", response_model=OrganizationList, tags=["annuaire"])
def organizations(q: str | None = Query(default=None, max_length=200),
                  domain: str | None = Query(default=None, max_length=120),
                  limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0),
                  state: AppState = Depends(get_state)) -> OrganizationList:
    total, items = state.repo.list(q=q, domain=domain, active=True, limit=limit, offset=offset)
    return OrganizationList(total=total, items=items)


@router.get("/organizations/{org_id}", response_model=OrganizationOut, tags=["annuaire"])
def organization(org_id: int, state: AppState = Depends(get_state)) -> OrganizationOut:
    org = state.repo.get(org_id)
    if org is None or not org.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation introuvable")
    return org


@router.get("/domains", response_model=list[DomainOut], tags=["annuaire"])
def domains(state: AppState = Depends(get_state)) -> list[DomainOut]:
    return state.repo.list_domains()


@router.get("/documents", response_model=list[DocumentInfo], tags=["corpus"])
def documents(state: AppState = Depends(get_state)) -> list[DocumentInfo]:
    """Contenu de l'index : fiches documentaires et organisations, avec leur nombre de passages."""
    return [DocumentInfo(**d) for d in state.engine.list_documents()]
