"""Repository per i movimenti di ingresso merce.

Operazioni CRUD sul modello ``MovIngressoMerce`` usando il context manager di
``core.db`` (niente connessione globale/cursore condiviso).
"""

from ..db import connection
from ..core_models import MovIngressoMerce


def fetch_all(tenant_id=None):
    """Recupera tutti i movimenti di ingresso merce."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT * FROM ingresso_merce WHERE tenant_id = %s "
                "ORDER BY data_acq DESC, progressivo_acq DESC",
                (tenant_id,),
            )
            return [MovIngressoMerce.from_row(row) for row in c.fetchall()]
        return MovIngressoMerce.fetch_all(c)


def fetch_by_progressivo(progressivo_acq, tenant_id=None):
    """Recupera i movimenti associati a un dato ``progressivo_acq``."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT * FROM ingresso_merce "
                "WHERE progressivo_acq = %s AND tenant_id = %s",
                (progressivo_acq, tenant_id),
            )
            return [MovIngressoMerce.from_row(row) for row in c.fetchall()]
        return MovIngressoMerce.fetch_by_progressivo(c, progressivo_acq)


def find_by_key(key, tenant_id=None):
    """Cerca un movimento tramite chiave composta."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            return MovIngressoMerce.find_by_key(c, key)
        return MovIngressoMerce.find_by_key(c, key)


def insert(value, tenant_id=None):
    """Inserisce un ``MovIngressoMerce`` (o un dict) nel database."""
    if not isinstance(value, MovIngressoMerce):
        value = MovIngressoMerce(**value)
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "INSERT INTO ingresso_merce "
                "(progressivo_acq, data_acq, documento, fornitore, prodotto, "
                " quantita, residuo, lotto_chiuso, id_merc, tenant_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (value.prog_acq, value.data, value.num_ddt, value.fornitore,
                 value.taglio, value.peso_i, value.peso_f, value.lotto_chiuso,
                 value.id_merc, tenant_id),
            )
            conn.commit()
            return value
        value.insert(c, conn)
        return value


def save(value, tenant_id=None):
    """Aggiorna un ``MovIngressoMerce`` esistente."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "UPDATE ingresso_merce "
                "SET progressivo_acq=%s, data_acq=%s, documento=%s, fornitore=%s, "
                "    prodotto=%s, quantita=%s, residuo=%s, lotto_chiuso=%s, id_merc=%s "
                "WHERE progressivo_acq=%s AND tenant_id=%s",
                (value.prog_acq, value.data, value.num_ddt, value.fornitore,
                 value.taglio, value.peso_i, value.peso_f, value.lotto_chiuso,
                 value.id_merc, value.prog_acq, tenant_id),
            )
            conn.commit()
            return value
        value.save(c, conn)
        return value


def delete(value, tenant_id=None):
    """Elimina un ``MovIngressoMerce`` dal database."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "DELETE FROM ingresso_merce WHERE progressivo_acq = %s AND tenant_id = %s",
                (value.prog_acq, tenant_id),
            )
            conn.commit()
            return
        value.delete(c, conn)
