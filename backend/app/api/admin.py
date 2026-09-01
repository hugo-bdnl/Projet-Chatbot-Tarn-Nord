"""Endpoints d'administration (back-office) : annuaire, analytiques, configuration, réindexation.

Tous exigent le header X-API-Key quand CHATBOT_API_KEY est défini (REQ-FUNC.6).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from ..bootstrap import AppState
from ..directory import DuplicateOrganization
from ..schemas import (AnalyticsSummary, ChatbotConfig, DomainOut, DomainUpdate, ImportRequest, ImportResponse,
                       IngestResponse, OrganizationIn, OrganizationList, OrganizationOut, QueryList)
from .deps import get_state, require_api_key

router = APIRouter(prefix="/admin", dependencies=[Depends(require_api_key)])


# ------------------------------------------------------------------ annuaire
@router.get("/organizations", response_model=OrganizationList, tags=["admin · annuaire"])
def list_organizations(q: str | None = Query(default=None, max_length=200),
                       domain: str | None = Query(default=None, max_length=120),
                       active: bool | None = Query(default=None, description="Défaut : toutes"),
                       limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0),
                       state: AppState = Depends(get_state)) -> OrganizationList:
    total, items = state.repo.list(q=q, domain=domain, active=active, limit=limit, offset=offset)
    return OrganizationList(total=total, items=items)


@router.post("/organizations", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED,
             tags=["admin · annuaire"])
async def create_organization(payload: OrganizationIn, state: AppState = Depends(get_state)) -> OrganizationOut:
    try:
        org = state.repo.create(payload)
    except DuplicateOrganization as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Une organisation « {exc} » existe déjà") from exc
    await run_in_threadpool(state.indexer.sync_organization, org)
    return org


@router.put("/organizations/{org_id}", response_model=OrganizationOut, tags=["admin · annuaire"])
async def update_organization(org_id: int, payload: OrganizationIn,
                              state: AppState = Depends(get_state)) -> OrganizationOut:
    try:
        org = state.repo.update(org_id, payload)
    except DuplicateOrganization as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Une organisation « {exc} » existe déjà") from exc
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation introuvable")
    await run_in_threadpool(state.indexer.sync_organization, org)
    return org


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["admin · annuaire"])
async def delete_organization(org_id: int, state: AppState = Depends(get_state)) -> None:
    if not state.repo.delete(org_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation introuvable")
    await run_in_threadpool(state.indexer.sync_organization, None, org_id)


@router.post("/organizations/import", response_model=ImportResponse, tags=["admin · annuaire"])
async def import_organizations(payload: ImportRequest, state: AppState = Depends(get_state)) -> ImportResponse:
    """Import en masse (synchronisation avec l'annuaire régional, REQ-FUNC.5) : upsert par nom."""
    state.repo.upsert_domains(payload.domains)
    result = state.repo.import_many(payload.organizations, replace=payload.replace)
    report = await run_in_threadpool(state.indexer.rebuild)
    return ImportResponse(created=result.created, updated=result.updated, deleted=result.deleted,
                          total=state.repo.count(active_only=False), passages=report.passages)


@router.get("/organizations/export", response_model=list[OrganizationOut], tags=["admin · annuaire"])
def export_organizations(state: AppState = Depends(get_state)) -> list[OrganizationOut]:
    """Export complet (actives et inactives), réimportable tel quel via /admin/organizations/import."""
    return state.repo.list(active=None, limit=100_000)[1]


@router.put("/domains/{domain_id}", response_model=DomainOut, tags=["admin · annuaire"])
def update_domain(domain_id: int, payload: DomainUpdate, state: AppState = Depends(get_state)) -> DomainOut:
    try:
        domain = state.repo.update_domain(domain_id, payload)
    except DuplicateOrganization as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if domain is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Domaine introuvable")
    return domain


# ------------------------------------------------------------------- index
@router.post("/reindex", response_model=IngestResponse, tags=["admin · index"])
async def reindex(state: AppState = Depends(get_state)) -> IngestResponse:
    """Reconstruit l'index depuis le corpus et l'annuaire (après modification des fiches Markdown)."""
    report = await run_in_threadpool(state.indexer.rebuild)
    return IngestResponse(documents=report.documents, organizations=report.organizations,
                          passages=report.passages, seconds=report.seconds, model=state.settings.embedding_model)


# -------------------------------------------------------------- analytiques
@router.get("/analytics", response_model=AnalyticsSummary, tags=["admin · analytiques"])
def analytics(days: int = Query(default=7, ge=1, le=366), state: AppState = Depends(get_state)) -> AnalyticsSummary:
    return state.analytics.summary(days)


@router.get("/analytics/questions", response_model=QueryList, tags=["admin · analytiques"])
def questions(answered: bool | None = Query(default=None), limit: int = Query(default=50, ge=1, le=500),
              offset: int = Query(default=0, ge=0), state: AppState = Depends(get_state)) -> QueryList:
    """Journal des questions (les plus récentes d'abord) ; `answered=false` = à exploiter pour enrichir l'annuaire."""
    return state.analytics.recent(limit=limit, offset=offset, answered=answered)


# ------------------------------------------------------------ configuration
@router.get("/config", response_model=ChatbotConfig, tags=["admin · configuration"])
def get_config(state: AppState = Depends(get_state)) -> ChatbotConfig:
    return state.config_store.get()


@router.put("/config", response_model=ChatbotConfig, tags=["admin · configuration"])
def put_config(payload: ChatbotConfig, state: AppState = Depends(get_state)) -> ChatbotConfig:
    return state.config_store.save(payload)


@router.post("/config/reset", response_model=ChatbotConfig, tags=["admin · configuration"])
def reset_config(state: AppState = Depends(get_state)) -> ChatbotConfig:
    return state.config_store.reset()
