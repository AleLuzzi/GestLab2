"""Repository per ingresso merce e lotti.

Migra ``_recupera_progressivo_ingresso``, ``_recupera_lista_fornitori`` e
``_recupera_lotti_aperti`` da ``controller_db.py`` usando il context manager.
"""

from ..db import connection


def recupera_progressivo_ingresso(tenant_id=None):
    """Recupera il progressivo di ingresso corrente."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT prog_acq FROM progressivi WHERE tenant_id = %s",
                (tenant_id,),
            )
        else:
            c.execute("SELECT prog_acq FROM progressivi")
        row = c.fetchone()
        return int(row[0]) if row else None


def recupera_lista_fornitori(tenant_id=None):
    """Restituisce l'elenco dei fornitori abilitati all'ingresso merce."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT azienda FROM fornitori "
                "WHERE flag1_ing_merce = 1 AND tenant_id = %s",
                (tenant_id,),
            )
        else:
            c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1")
        return [row[0] for row in c]


def lotti_aperti(tenant_id=None):
    """Restituisce i lotti aperti (lotto_chiuso = 'no')."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT progressivo_acq, fornitore, prodotto, residuo "
                "FROM ingresso_merce WHERE lotto_chiuso = 'no' AND tenant_id = %s",
                (tenant_id,),
            )
        else:
            c.execute(
                "SELECT progressivo_acq, fornitore, prodotto, residuo "
                "FROM ingresso_merce WHERE lotto_chiuso = 'no'"
            )
        return [
            {"number": str(x[0]), "fornit": str(x[1]),
             "name": str(x[2]), "peso": str(x[3])}
            for x in c
        ]
