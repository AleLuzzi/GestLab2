"""Servizio Vendite: business logic per la vendita dei lotti.

Orchestra i repository ``lotti`` per i lotti aperti e gestisce la chiusura
operativa del lotto quando la giacenza è completamente scaricata.
"""

from core.db import connection
from core.repositories import lotti as lotti_repo


def lotti_aperti(tenant_id=None):
    """Restituisce i lotti aperti disponibili alla vendita."""
    return lotti_repo.lotti_aperti(tenant_id)


def chiudi_lotto(lotto_id, tenant_id=None):
    """Segna un lotto come chiuso impostando giacenza e attivita' a zero.

    Questa implementazione e' la base del flusso di vendita: la chiusura del lotto
    avviene nella stessa transazione del decremento giacenza, e non solleva piu'
    NotImplementedError.
    """
    if lotto_id is None:
        raise ValueError("lotto_id non puo' essere nullo")

    with connection() as conn:
        cursor = conn.cursor()
        if tenant_id is None:
            cursor.execute(
                "UPDATE lotti SET quantita_disponibile = 0, attivo = 0 WHERE id = %s",
                (lotto_id,),
            )
        else:
            cursor.execute(
                "UPDATE lotti SET quantita_disponibile = 0, attivo = 0 "
                "WHERE tenant_id = %s AND id = %s",
                (tenant_id, lotto_id),
            )
        conn.commit()
        return cursor.rowcount > 0
