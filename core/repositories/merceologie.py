"""Repository per le merceologie.

Operazioni CRUD sul modello ``Merceologia`` usando il context manager di
``core.db`` (elimina l'uso diretto di ``db.c``/``db.conn`` nei widget).
"""

from ..db import connection
from ..core_models import Merceologia

def _has_tenant_id_column():
    """True quando il DB ha la colonna tenant_id nella tabella merceologie."""
    with connection() as conn:
        c = conn.cursor()
        c.execute("SHOW COLUMNS FROM merceologie LIKE 'tenant_id'")
        return c.fetchone() is not None


def fetch_all(tenant_id=None):
    """Recupera tutte le merceologie come oggetti ``Merceologia``.

    Args:
        tenant_id: se valorizzato, filtra ``WHERE tenant_id = %s``
            (multi-tenancy SaaS). ``None`` = nessun filtro (UI desktop).
    """
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None and _has_tenant_id_column():
            c.execute(
                "SELECT m.id, m.merceologia, m.id_reparto, m.flag1_inv, m.flag2_taglio, m.flag3_ing_base, r.reparto "
                "FROM merceologie m "
                "LEFT JOIN reparti r ON m.id_reparto = r.ID "
                "WHERE m.tenant_id = %s",
                (tenant_id,),
            )
            return [Merceologia.from_row(row) for row in c.fetchall()]
        return Merceologia.fetch_all(c)


def find_by_id(merceologia_id, tenant_id=None):
    """Cerca una merceologia tramite il suo ID (opzionalmente scoped al tenant)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None and _has_tenant_id_column():
            c.execute(
                "SELECT m.id, m.merceologia, m.id_reparto, m.flag1_inv, m.flag2_taglio, m.flag3_ing_base, r.reparto "
                "FROM merceologie m "
                "LEFT JOIN reparti r ON m.id_reparto = r.id "
                "WHERE m.id = %s AND m.tenant_id = %s",
                (merceologia_id, tenant_id),
            )
            row = c.fetchone()
            return Merceologia.from_row(row) if row else None
        return Merceologia.find_by_id(c, merceologia_id)


def insert(value, tenant_id=None):
    """Inserisce una ``Merceologia`` (o un dict) nel database."""
    if not isinstance(value, Merceologia):
        value = Merceologia(**value)
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None and _has_tenant_id_column():
            c.execute(
                "INSERT INTO merceologie (merceologia, id_reparto, flag1_inv, flag2_taglio, flag3_ing_base, tenant_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (value.merceologia, value.id_reparto, value.flag1_inv, value.flag2_taglio, value.flag3_ing_base, tenant_id),
            )
            if hasattr(c, "lastrowid") and c.lastrowid:
                value.id = c.lastrowid
            conn.commit()
            return value
        value.insert(c, conn)
        return value


def save(value, tenant_id=None):
    """Aggiorna una ``Merceologia`` (deve avere ``id``)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None and _has_tenant_id_column():
            c.execute(
                "UPDATE merceologie SET merceologia = %s, id_reparto = %s, flag1_inv = %s, flag2_taglio = %s, flag3_ing_base = %s "
                "WHERE id = %s AND tenant_id = %s",
                (value.merceologia, value.id_reparto, value.flag1_inv, value.flag2_taglio, value.flag3_ing_base, value.id, tenant_id),
            )
            conn.commit()
            return value
        value.save(c, conn)
        return value


def delete(value, tenant_id=None):
    """Elimina una ``Merceologia`` dal database."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None and _has_tenant_id_column():
            c.execute(
                "DELETE FROM merceologie WHERE id = %s AND tenant_id = %s",
                (value.id, tenant_id),
            )
            conn.commit()
            return
        value.delete(c, conn)
