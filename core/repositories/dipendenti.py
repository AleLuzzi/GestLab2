"""Repository per i dipendenti.

Operazioni CRUD sul modello ``Dipendente`` usando il context manager di
``core.db`` (elimina l'uso diretto di ``db.c``/``db.conn`` nei widget).
"""

from ..db import connection
from ..core_models import Dipendente


def fetch_all(tenant_id=None):
    """Recupera tutti i dipendenti come oggetti ``Dipendente``.

    Args:
        tenant_id: se valorizzato, filtra ``WHERE tenant_id = %s``
            (multi-tenancy SaaS). ``None`` = nessun filtro (UI desktop).
    """
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT d.id, d.nome, d.email, d.reparto, r.reparto "
                "FROM dipendenti d "
                "LEFT JOIN reparti r ON d.reparto = r.ID "
                "WHERE d.tenant_id = %s",
                (tenant_id,),
            )
            return [Dipendente.from_row(row) for row in c.fetchall()]
        return Dipendente.fetch_all(c)


def find_by_id(dipendente_id, tenant_id=None):
    """Cerca un dipendente tramite il suo ID (opzionalmente scoped al tenant)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT d.id, d.nome, d.email, d.reparto, r.reparto "
                "FROM dipendenti d "
                "LEFT JOIN reparti r ON d.reparto = r.ID "
                "WHERE d.id = %s AND d.tenant_id = %s",
                (dipendente_id, tenant_id),
            )
            row = c.fetchone()
            return Dipendente.from_row(row) if row else None
        return Dipendente.find_by_id(c, dipendente_id)


def insert(value, tenant_id=None):
    """Inserisce un ``Dipendente`` (o un dict) nel database."""
    if not isinstance(value, Dipendente):
        value = Dipendente(**value)
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "INSERT INTO dipendenti (nome, email, reparto, tenant_id) "
                "VALUES (%s, %s, %s, %s)",
                (value.nome, value.email, value.reparto, tenant_id),
            )
            if hasattr(c, "lastrowid") and c.lastrowid:
                value.id = c.lastrowid
            conn.commit()
            return value
        value.insert(c, conn)
        return value


def save(value, tenant_id=None):
    """Aggiorna un ``Dipendente`` (deve avere ``id``)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "UPDATE dipendenti SET nome = %s, email = %s, reparto = %s "
                "WHERE id = %s AND tenant_id = %s",
                (value.nome, value.email, value.reparto, value.id, tenant_id),
            )
            conn.commit()
            return value
        value.save(c, conn)
        return value


def delete(value, tenant_id=None):
    """Elimina un ``Dipendente`` dal database."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "DELETE FROM dipendenti WHERE id = %s AND tenant_id = %s",
                (value.id, tenant_id),
            )
            conn.commit()
            return
        value.delete(c, conn)
