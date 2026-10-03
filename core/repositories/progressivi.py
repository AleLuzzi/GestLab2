"""Repository per i contatori progressivi."""

from ..db import connection
from ..core_models import Progressivi


def fetch_all(tenant_id=None):
    """Recupera tutti i record progressivi, opzionalmente filtrati per tenant."""
    with connection() as conn:
        cursor = conn.cursor()
        if tenant_id is None:
            return Progressivi.fetch_all(cursor)
        return Progressivi.fetch_by_tenant(cursor, tenant_id)


def insert(value, tenant_id=None):
    """Inserisce un record progressivi per il tenant."""
    if not isinstance(value, Progressivi):
        value = Progressivi(**value)
    if tenant_id is not None:
        value.tenant_id = tenant_id
    with connection() as conn:
        value.insert(conn.cursor(), conn)
    return value


def save(value, tenant_id=None):
    """Aggiorna il record progressivi."""
    if tenant_id is not None:
        value.tenant_id = tenant_id
    with connection() as conn:
        value.save(conn.cursor(), conn)
    return value


def delete(value, tenant_id=None):
    """Elimina il record progressivi."""
    if tenant_id is not None:
        value.tenant_id = tenant_id
    with connection() as conn:
        value.delete(conn.cursor(), conn)
