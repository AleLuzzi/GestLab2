"""Apertura, rotazione e revoca delle sessioni di refresh.

Ogni login apre una famiglia. Il rinnovo revoca il refresh presentato ed
emette il successivo della stessa famiglia. Un refresh già ruotato o revocato,
se ripresentato, chiude l'intera famiglia: la copia rubata non resta valida.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from saas import auth
from saas.repositories import tenant_repo


def _scadenza_refresh():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        days=auth.REFRESH_TOKEN_EXPIRE_DAYS
    )


def apri_sessione(utente: dict) -> tuple[str, str]:
    """Emette access e refresh e persiste solo l'hash del refresh."""
    jti = secrets.token_urlsafe(32)
    tenant_repo.salva_refresh_token(
        utente["id"],
        auth.hash_token(jti),
        str(uuid.uuid4()),
        _scadenza_refresh(),
    )
    access = auth.create_token(
        utente["email"], utente["tenant_id"], utente["ruolo"], "access"
    )
    refresh = auth.create_token(
        utente["email"],
        utente["tenant_id"],
        utente["ruolo"],
        "refresh",
        jti=jti,
    )
    return access, refresh


def rinnova_sessione(refresh_token: str) -> tuple[str, str]:
    """Ruota il refresh e restituisce la nuova coppia, con il ruolo attuale."""
    info = _leggi_refresh(refresh_token)
    nuovo_jti = secrets.token_urlsafe(32)
    esito = tenant_repo.ruota_refresh_token(
        auth.hash_token(info["jti"]),
        auth.hash_token(nuovo_jti),
        _scadenza_refresh(),
    )
    if esito["stato"] != "ruotato":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sessione non più valida. Accedi di nuovo.",
        )
    utente = esito["utente"]
    access = auth.create_token(
        utente["email"], utente["tenant_id"], utente["ruolo"], "access"
    )
    refresh = auth.create_token(
        utente["email"],
        utente["tenant_id"],
        utente["ruolo"],
        "refresh",
        jti=nuovo_jti,
    )
    return access, refresh


def chiudi_sessione(refresh_token: str) -> None:
    """Revoca la famiglia del refresh presentato."""
    info = _leggi_refresh(refresh_token)
    tenant_repo.revoca_refresh_token(auth.hash_token(info["jti"]))


def _leggi_refresh(refresh_token: str) -> dict:
    info = auth.decode_token(refresh_token)
    if info.get("type") != "refresh" or not info.get("jti"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token non di refresh")
    return info
