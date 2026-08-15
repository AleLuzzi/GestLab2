"""Repository per i fornitori.

Operazioni CRUD sul modello ``Fornitore`` usando il context manager di
``core.db`` (niente connessione globale).
"""

from ..db import connection
from ..core_models import Fornitore


def fetch_all(tenant_id=None):
    """Recupera tutti i fornitori come oggetti ``Fornitore``."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT id, azienda, flag1_ing_merce, flag2_inventario "
                "FROM fornitori WHERE tenant_id = %s",
                (tenant_id,),
            )
            return [Fornitore.from_row(row) for row in c.fetchall()]
        return Fornitore.fetch_all(c)


def find_by_id(fornitore_id, tenant_id=None):
    """Cerca un fornitore tramite il suo ID (opzionalmente scoped al tenant)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT id, azienda, flag1_ing_merce, flag2_inventario "
                "FROM fornitori WHERE id = %s AND tenant_id = %s",
                (fornitore_id, tenant_id),
            )
            row = c.fetchone()
            return Fornitore.from_row(row) if row else None
        return Fornitore.find_by_id(c, fornitore_id)


def abilitati_ingresso_merce(tenant_id=None):
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


def insert(value, tenant_id=None):
    """Inserisce un ``Fornitore`` (o un dict) nel database."""
    if not isinstance(value, Fornitore):
        value = Fornitore(**value)
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "INSERT INTO fornitori (azienda, flag1_ing_merce, flag2_inventario, tenant_id) "
                "VALUES (%s, %s, %s, %s)",
                (value.azienda, value.flag1_ing_merce, value.flag2_inventario, tenant_id),
            )
            if hasattr(c, "lastrowid") and c.lastrowid:
                value.id = c.lastrowid
            conn.commit()
            return value
        value.insert(c, conn)
        return value


def save(value, tenant_id=None):
    """Aggiorna un ``Fornitore`` (deve avere ``id``)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "UPDATE fornitori SET azienda = %s, flag1_ing_merce = %s, "
                "flag2_inventario = %s WHERE id = %s AND tenant_id = %s",
                (value.azienda, value.flag1_ing_merce, value.flag2_inventario,
                 value.id, tenant_id),
            )
            conn.commit()
            return value
        value.save(c, conn)
        return value


def delete(value, tenant_id=None):
    """Elimina un ``Fornitore`` dal database."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "DELETE FROM fornitori WHERE id = %s AND tenant_id = %s",
                (value.id, tenant_id),
            )
            conn.commit()
            return
        value.delete(c, conn)
