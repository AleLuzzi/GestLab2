"""Repository per i tagli.

Operazioni CRUD sul modello ``Taglio`` usando il context manager di
``core.db`` e supportando il multi-tenancy SaaS tramite ``tenant_id``.
"""

from ..db import connection
from ..core_models import Taglio


def fetch_all(tenant_id=None):
    """Recupera tutti i tagli come oggetti ``Taglio``."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT t.id, t.taglio, t.id_merceologia, m.merceologia "
                "FROM tagli t "
                "LEFT JOIN merceologie m ON t.id_merceologia = m.id "
                "WHERE t.tenant_id = %s "
                "ORDER BY t.id",
                (tenant_id,),
            )
            return [Taglio.from_row(row) for row in c.fetchall()]
        return Taglio.fetch_all(c)


def find_by_id(taglio_id, tenant_id=None):
    """Cerca un taglio tramite il suo ID (opzionalmente scoped al tenant)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT t.id, t.taglio, t.id_merceologia, m.merceologia "
                "FROM tagli t "
                "LEFT JOIN merceologie m ON t.id_merceologia = m.id "
                "WHERE t.id = %s AND t.tenant_id = %s",
                (taglio_id, tenant_id),
            )
            row = c.fetchone()
            return Taglio.from_row(row) if row else None
        return Taglio.find_by_id(c, taglio_id)


def insert(value, tenant_id=None):
    """Inserisce un ``Taglio`` (o un dict) nel database."""
    if not isinstance(value, Taglio):
        value = Taglio(**value)
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "INSERT INTO tagli (taglio, id_merceologia, tenant_id) "
                "VALUES (%s, %s, %s)",
                (value.taglio, value.id_merceologia, tenant_id),
            )
            if hasattr(c, "lastrowid") and c.lastrowid:
                value.id = c.lastrowid
            conn.commit()
            return value
        value.insert(c, conn)
        return value


def save(value, tenant_id=None):
    """Aggiorna un ``Taglio`` (deve avere ``id``)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "UPDATE tagli SET taglio = %s, id_merceologia = %s "
                "WHERE id = %s AND tenant_id = %s",
                (value.taglio, value.id_merceologia, value.id, tenant_id),
            )
            conn.commit()
            return value
        value.save(c, conn)
        return value


def delete(value, tenant_id=None):
    """Elimina un ``Taglio`` dal database."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "DELETE FROM tagli WHERE id = %s AND tenant_id = %s",
                (value.id, tenant_id),
            )
            conn.commit()
            return
        value.delete(c, conn)
