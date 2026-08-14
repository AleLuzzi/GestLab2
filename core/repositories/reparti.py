"""Repository per i reparti.

Migra ``_recupera_reparti`` da ``controller_db.py`` e aggiunge operazioni CRUD
sul modello ``Reparto`` usando il context manager di ``core.db``.
"""

from ..db import connection
from ..core_models import Reparto

def reparti_abilitati(tenant_id=None):
    """Recupera i reparti abilitati per i dipendenti (flag1_dip = 1)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None :
            c.execute(
                "SELECT ID, reparto FROM reparti "
                "WHERE flag1_dip = 1 AND tenant_id = %s ORDER BY ID",
                (tenant_id,),
            )
        else:
            c.execute(
                "SELECT ID, reparto FROM reparti WHERE flag1_dip = 1 ORDER BY ID"
            )
        return [{"id": str(x[0]), "reparto": str(x[1])} for x in c]


def fetch_all(tenant_id=None):
    """Recupera tutti i reparti come oggetti ``Reparto``."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None :
            c.execute(
                "SELECT id, reparto, flag1_dip, flag2_prod "
                "FROM reparti WHERE tenant_id = %s",
                (tenant_id,),
            )
            return [Reparto.from_row(row) for row in c.fetchall()]
        return Reparto.fetch_all(c)


def find_by_id(reparto_id, tenant_id=None):
    """Cerca un reparto tramite il suo ID (opzionalmente scoped al tenant)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None :
            c.execute(
                "SELECT id, reparto, flag1_dip, flag2_prod "
                "FROM reparti WHERE id = %s AND tenant_id = %s",
                (reparto_id, tenant_id),
            )
            row = c.fetchone()
            return Reparto.from_row(row) if row else None
        return Reparto.find_by_id(c, reparto_id)


def insert(value, tenant_id=None):
    """Inserisce un ``Reparto`` (o un dict con i campi) nel database."""
    if not isinstance(value, Reparto):
        value = Reparto(**value)
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None :
            c.execute(
                "INSERT INTO reparti (reparto, flag1_dip, flag2_prod, tenant_id) "
                "VALUES (%s, %s, %s, %s)",
                (value.reparto, value.flag1_dip, value.flag2_prod, tenant_id),
            )
            if hasattr(c, "lastrowid") and c.lastrowid:
                value.id = c.lastrowid
            conn.commit()
            return value
        value.insert(c, conn)
        return value


def save(value, tenant_id=None):
    """Aggiorna un ``Reparto`` (deve avere ``id``)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None :
            c.execute(
                "UPDATE reparti SET reparto = %s, flag1_dip = %s, flag2_prod = %s "
                "WHERE id = %s AND tenant_id = %s",
                (value.reparto, value.flag1_dip, value.flag2_prod, value.id, tenant_id),
            )
            conn.commit()
            return value
        value.save(c, conn)
        return value


def delete(value, tenant_id=None):
    """Elimina un ``Reparto`` dal database."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None :
            c.execute(
                "DELETE FROM reparti WHERE id = %s AND tenant_id = %s",
                (value.id, tenant_id),
            )
            conn.commit()
            return
        value.delete(c, conn)
