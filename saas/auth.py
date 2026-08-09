"""Autenticazione e autorizzazione per il backend SaaS.

Gestisce hashing delle password (bcrypt), emissione/verifica dei token JWT
(access + refresh) e dipendenze FastAPI per estrarre tenant_id e ruolo dalle
richieste autenticate.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.env import get_secret

# In produzione: valori da variabili d'ambiente / Secret Manager / .env.
SECRET_KEY = get_secret("JWT_SECRET", os.environ.get("GESTLAB_JWT_SECRET", "cambia-questa-secret-key"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("GESTLAB_ACCESS_MIN", get_secret("JWT_ACCESS_MIN", "60")))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("GESTLAB_REFRESH_DAYS", get_secret("JWT_REFRESH_DAYS", "7")))

_bearer = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------------- #
#  Password hashing (bcrypt)
# ------------------------------------------------------------------------- #

def hash_password(password: str) -> str:
    """Restituisce l'hash bcrypt della password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una password in chiaro contro l'hash salvato."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ------------------------------------------------------------------------- #
#  JWT
# ------------------------------------------------------------------------- #

def create_token(subject: str, tenant_id: int, ruolo: str,
                 token_type: str = "access",
                 expires_delta: timedelta | None = None) -> str:
    """Crea un JWT (access o refresh)."""
    if expires_delta is None:
        expires_delta = (
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            if token_type == "access"
            else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "tenant_id": tenant_id,
        "ruolo": ruolo,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica e valida un JWT. Solleva 401 se non valido/scaduto."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token scaduto")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token non valido")


# ------------------------------------------------------------------------- #
#  Dipendenze FastAPI
# ------------------------------------------------------------------------- #

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Dipendeza FastAPI: restituisce il payload dell'utente autenticato."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenziali mancanti")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token non di accesso")

    return payload


def require_roles(*ruoli: str):
    """Factory di dipendenza: verifica che l'utente abbia uno dei ruoli."""

    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("ruolo") not in ruoli:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Ruolo non autorizzato per questa operazione",
            )
        return user

    return _checker
