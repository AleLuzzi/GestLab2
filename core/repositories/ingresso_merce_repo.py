"""Repository per i movimenti di ingresso merce.

Operazioni CRUD sul modello ``MovIngressoMerce`` usando il context manager di
``core.db`` (niente connessione globale/cursore condiviso).
"""

from ..db import connection
from ..core_models import MovIngressoMerce
from . import soggetti as soggetti_repo


class FornitoreNonValido(Exception):
    """Fornitore inesistente, non attivo o non abilitato all'ingresso merce."""


def fetch_all(tenant_id=None):
    """Recupera tutti i movimenti di ingresso merce."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT progressivo_acq, data_acq, documento, fornitore, prodotto, "
                "quantita, residuo, lotto_chiuso, id_merc, fornitore_id "
                "FROM ingresso_merce WHERE tenant_id = %s "
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
                "SELECT progressivo_acq, data_acq, documento, fornitore, prodotto, "
                "quantita, residuo, lotto_chiuso, id_merc, fornitore_id "
                "FROM ingresso_merce "
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
            try:
                fornitore = soggetti_repo.fornitore_abilitato(
                    c, tenant_id, value.fornitore_id
                )
                if not fornitore:
                    raise FornitoreNonValido
                value.fornitore = fornitore["denominazione"][:50]
                c.execute(
                    "INSERT INTO ingresso_merce "
                    "(progressivo_acq, data_acq, documento, fornitore, prodotto, "
                    " quantita, residuo, lotto_chiuso, id_merc, tenant_id, fornitore_id) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (value.prog_acq, value.data, value.num_ddt, value.fornitore,
                     value.taglio, value.peso_i, value.peso_f, value.lotto_chiuso,
                     value.id_merc, tenant_id, value.fornitore_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return value
        value.insert(c, conn)
        return value


def insert_many(values, tenant_id):
    """Inserisce tutte le righe di un ingresso in un'unica transazione."""
    values = [
        value if isinstance(value, MovIngressoMerce) else MovIngressoMerce(**value)
        for value in values
    ]
    if not values:
        raise ValueError("Un ingresso merce deve contenere almeno una riga.")

    with connection() as conn:
        c = conn.cursor()
        try:
            fornitore = soggetti_repo.fornitore_abilitato(
                c, tenant_id, values[0].fornitore_id
            )
            if not fornitore:
                raise FornitoreNonValido
            for value in values:
                if value.fornitore_id != values[0].fornitore_id:
                    raise ValueError("Tutte le righe devono riferirsi allo stesso fornitore.")
                value.fornitore = fornitore["denominazione"][:50]
            c.executemany(
                "INSERT INTO ingresso_merce "
                "(progressivo_acq, data_acq, documento, fornitore, prodotto, "
                " quantita, residuo, lotto_chiuso, id_merc, tenant_id, fornitore_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        value.prog_acq,
                        value.data,
                        value.num_ddt,
                        value.fornitore,
                        value.taglio,
                        value.peso_i,
                        value.peso_f,
                        value.lotto_chiuso,
                        value.id_merc,
                        tenant_id,
                        value.fornitore_id,
                    )
                    for value in values
                ],
            )
            c.execute(
                "UPDATE progressivi "
                "SET prog_acq = prog_acq + 1 "
                "WHERE tenant_id = %s",
                (tenant_id,),
            )
            if c.rowcount != 1:
                raise RuntimeError(
                    "Impossibile aggiornare il progressivo acquisti del tenant."
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return values


def save(value, tenant_id=None):
    """Aggiorna un ``MovIngressoMerce`` esistente."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "UPDATE ingresso_merce "
                "SET progressivo_acq=%s, data_acq=%s, documento=%s, fornitore=%s, "
                "    prodotto=%s, quantita=%s, residuo=%s, lotto_chiuso=%s, "
                "    id_merc=%s, fornitore_id=%s "
                "WHERE progressivo_acq=%s AND tenant_id=%s",
                (value.prog_acq, value.data, value.num_ddt, value.fornitore,
                 value.taglio, value.peso_i, value.peso_f, value.lotto_chiuso,
                 value.id_merc, value.fornitore_id, value.prog_acq, tenant_id),
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
