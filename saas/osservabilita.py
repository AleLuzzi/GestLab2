"""Salute del servizio, log delle richieste e segnalazione degli errori.

Il controllo ``/health`` verifica il database. Le richieste, tranne il health
check riuscito, finiscono nel log operativo. Un'eccezione non gestita riceve
un riferimento assistenza, viene scritta nel log e, se ``SENTRY_DSN`` è
configurato e ``sentry-sdk`` è installato, viene inviata a Sentry senza dati
personali di default.
"""

import logging
import os
import uuid

from core.db import connection
from core.env import ambiente_corrente

logger = logging.getLogger("gestlab.saas")
_invia_errore = None


def controlla_database():
    """Esegue una lettura minima. Solleva se il database non risponde."""
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()


def esito_salute():
    """Restituisce lo stato HTTP e il corpo del controllo di salute."""
    try:
        controlla_database()
    except Exception:
        logger.exception("Health check: database non raggiungibile")
        return 503, {"status": "degraded", "database": "error"}
    return 200, {"status": "ok", "database": "ok"}


def riga_accesso(metodo, percorso, stato, secondi):
    """Scrive una riga di accesso. Il health check riuscito non riempie il log."""
    if percorso == "/health" and stato == 200:
        return
    messaggio = "HTTP %s %s %s %sms"
    argomenti = (stato, metodo, percorso, int(secondi * 1000))
    if stato >= 500:
        logger.error(messaggio, *argomenti)
    elif stato >= 400:
        logger.warning(messaggio, *argomenti)
    else:
        logger.info(messaggio, *argomenti)


def registra_errore(metodo, percorso, errore):
    """Registra un errore non gestito e restituisce il riferimento assistenza."""
    riferimento = uuid.uuid4().hex
    logger.error(
        "Errore non gestito riferimento=%s %s %s",
        riferimento,
        metodo,
        percorso,
        exc_info=errore,
    )
    if _invia_errore is not None:
        try:
            _invia_errore(errore, riferimento, metodo, percorso)
        except Exception:
            logger.exception(
                "Error tracking non riuscito riferimento=%s", riferimento
            )
    return riferimento


def avvia_error_tracking():
    """Attiva Sentry solo quando il DSN è configurato e il pacchetto è presente."""
    global _invia_errore
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        _invia_errore = None
        return False
    try:
        import sentry_sdk
    except ImportError:
        logger.error("SENTRY_DSN è impostato ma sentry-sdk non è installato")
        _invia_errore = None
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=ambiente_corrente() or "development",
        send_default_pii=False,
    )

    def invia(errore, riferimento, metodo, percorso):
        sentry_sdk.set_tag("riferimento", riferimento)
        sentry_sdk.set_tag("http_method", metodo)
        sentry_sdk.set_tag("path", percorso)
        sentry_sdk.capture_exception(errore)

    _invia_errore = invia
    logger.info("Error tracking attivo")
    return True
