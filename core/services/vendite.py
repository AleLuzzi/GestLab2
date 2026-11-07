"""Servizio vendite e chiusura operativa dei lotti.

La chiusura non scarica giacenza: ogni variazione deve appartenere a un flusso
tracciato (per esempio lavorazione o vendita).
"""

from core.db import connection
from core.repositories import lotti as lotti_repo


class LottoNonEsaurito(Exception):
    """Il lotto ha ancora giacenza e non può essere chiuso."""


def lotti_aperti(tenant_id=None):
    """Restituisce i lotti aperti disponibili alla vendita."""
    return lotti_repo.lotti_aperti(tenant_id)


def chiudi_lotto(lotto_id, tenant_id=None):
    """Chiude un lotto solo se la giacenza è già stata scaricata."""
    if lotto_id is None:
        raise ValueError("lotto_id non puo' essere nullo")

    with connection() as conn:
        cursor = conn.cursor()
        try:
            query = "SELECT quantita_disponibile FROM lotti WHERE id = %s"
            params = (lotto_id,)
            if tenant_id is not None:
                query += " AND tenant_id = %s"
                params += (tenant_id,)
            cursor.execute(query + " FOR UPDATE", params)
            lotto = cursor.fetchone()
            if lotto is None:
                conn.commit()
                return False
            if lotto[0] > 0:
                raise LottoNonEsaurito(
                    "Il lotto ha giacenza disponibile: registrare prima il movimento."
                )

            query = "UPDATE lotti SET attivo = 0 WHERE id = %s AND quantita_disponibile = 0"
            params = (lotto_id,)
            if tenant_id is not None:
                query += " AND tenant_id = %s"
                params += (tenant_id,)
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
