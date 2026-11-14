"""Scrittura dell'audit log nella transazione del chiamante."""

import json


def registra(cursor, tenant_id, utente_email, azione, entita, entita_id=None, dettaglio=None):
    """Registra una cancellazione o una rettifica prima del commit.

    Il cursore deve appartenere alla stessa transazione dell'operazione.
    Se l'inserimento fallisce, il chiamante deve eseguire il rollback.
    """
    email = str(utente_email or "").strip()
    if not email:
        raise ValueError("L'audit richiede l'identità dell'utente.")
    if azione not in {"CANCELLAZIONE", "RETTIFICA"}:
        raise ValueError("Azione di audit non prevista.")

    testo = None
    if dettaglio is not None:
        testo = json.dumps(dettaglio, ensure_ascii=False, default=str)
        testo = testo[:1000]

    cursor.execute(
        "INSERT INTO audit_log "
        "(tenant_id, utente_email, azione, entita, entita_id, dettaglio) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (
            tenant_id,
            email,
            azione,
            entita,
            None if entita_id is None else str(entita_id),
            testo,
        ),
    )
