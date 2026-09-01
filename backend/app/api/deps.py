"""Dépendances FastAPI : accès à l'état applicatif, contrôle de la clé d'administration."""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request, status

from ..bootstrap import AppState


def get_state(request: Request) -> AppState:
    state = getattr(request.app.state, "chatbot", None)
    if state is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service en cours d'initialisation")
    return state


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    """Protège /admin/* (REQ-FUNC.6). Sans CHATBOT_API_KEY, l'administration est ouverte (développement)."""
    expected: str = request.app.state.settings.api_key
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Clé API invalide")
