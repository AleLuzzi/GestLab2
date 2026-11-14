"""Richiesta e conferma del reset password via email."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from core.env import get_secret
from saas import auth, mail
from saas.repositories import tenant_repo

logger = logging.getLogger("gestlab.saas")

VALIDITA_MINUTI = 60
MESSAGGIO_RICHIESTA = (
    "Se l'indirizzo è registrato, riceverai un'email con le istruzioni "
    "per reimpostare la password."
)


class InvioEmailNonDisponibile(Exception):
    """L'email di reset non può essere inviata."""


class TokenResetNonValido(Exception):
    """Il token è assente, già usato o scaduto."""


def _url_reimpostazione(token: str) -> str:
    base = get_secret("GESTLAB_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/?reset={token}"


def richiedi_reimpostazione(email: str) -> str:
    """Prepara un token monouso e lo invia solo se l'utente è attivo.

    Senza SMTP la funzione si interrompe prima di cercare l'utente, così la
    risposta non rivela quali indirizzi esistono.
    """
    if not mail.smtp_configurato():
        raise InvioEmailNonDisponibile(
            "Invio email non configurato. Impostare SMTP_HOST e SMTP_FROM."
        )

    utente = tenant_repo.trova_utente_by_email(email)
    if not utente or not utente.get("attivo"):
        return MESSAGGIO_RICHIESTA

    token = secrets.token_urlsafe(32)
    token_hash = auth.hash_reset_token(token)
    scade_il = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        minutes=VALIDITA_MINUTI
    )
    tenant_repo.salva_token_reset(utente["id"], token_hash, scade_il)
    corpo = (
        "Hai chiesto di reimpostare la password di GestLab.\n\n"
        f"Apri questo collegamento entro {VALIDITA_MINUTI} minuti:\n"
        f"{_url_reimpostazione(token)}\n\n"
        "Se non hai fatto tu la richiesta, ignora questo messaggio. "
        "La password attuale resta invariata."
    )
    try:
        mail.invia_email(utente["email"], "Reimpostazione password GestLab", corpo)
    except Exception:
        logger.exception("Invio email di reset non riuscito per utente %s", utente["id"])
        try:
            tenant_repo.annulla_token_reset(token_hash)
        except Exception:
            logger.exception("Annullamento token di reset non riuscito")
        raise InvioEmailNonDisponibile(
            "Impossibile inviare l'email di reimpostazione. Riprova più tardi."
        )
    return MESSAGGIO_RICHIESTA


def reimposta_password(token: str, password: str) -> None:
    """Valida la nuova password e consuma il token nella stessa transazione."""
    auth.valida_password(password)
    aggiornata = tenant_repo.consuma_token_reset(
        auth.hash_reset_token(token.strip()),
        auth.hash_password(password),
    )
    if not aggiornata:
        raise TokenResetNonValido(
            "Il collegamento non è valido oppure è scaduto."
        )
