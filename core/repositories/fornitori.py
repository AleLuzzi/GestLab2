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
                "SELECT f.ID, s.denominazione, f.flag1_ing_merce, "
                "f.flag2_inventario, f.soggetto_id "
                "FROM fornitori f "
                "JOIN soggetti s ON s.tenant_id = f.tenant_id AND s.id = f.soggetto_id "
                "JOIN soggetti_ruoli r ON r.tenant_id = s.tenant_id "
                "AND r.soggetto_id = s.id AND r.ruolo = 'fornitore' "
                "WHERE f.tenant_id = %s AND s.attivo = 1 "
                "ORDER BY s.denominazione, f.ID",
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
                "SELECT f.ID, s.denominazione, f.flag1_ing_merce, "
                "f.flag2_inventario, f.soggetto_id "
                "FROM fornitori f "
                "JOIN soggetti s ON s.tenant_id = f.tenant_id AND s.id = f.soggetto_id "
                "JOIN soggetti_ruoli r ON r.tenant_id = s.tenant_id "
                "AND r.soggetto_id = s.id AND r.ruolo = 'fornitore' "
                "WHERE f.ID = %s AND f.tenant_id = %s AND s.attivo = 1",
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
                "SELECT s.denominazione FROM fornitori f "
                "JOIN soggetti s ON s.tenant_id = f.tenant_id AND s.id = f.soggetto_id "
                "JOIN soggetti_ruoli r ON r.tenant_id = s.tenant_id "
                "AND r.soggetto_id = s.id AND r.ruolo = 'fornitore' "
                "WHERE f.flag1_ing_merce = 1 AND f.tenant_id = %s AND s.attivo = 1 "
                "ORDER BY s.denominazione",
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
            try:
                c.execute(
                    "INSERT INTO soggetti (tenant_id, denominazione, tipo_soggetto) "
                    "VALUES (%s, %s, 'azienda')",
                    (tenant_id, value.azienda),
                )
                soggetto_id = c.lastrowid
                c.execute(
                    "INSERT INTO soggetti_ruoli (tenant_id, soggetto_id, ruolo) "
                    "VALUES (%s, %s, 'fornitore')",
                    (tenant_id, soggetto_id),
                )
                c.execute(
                    "INSERT INTO fornitori "
                    "(azienda, flag1_ing_merce, flag2_inventario, tenant_id, soggetto_id) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        value.azienda[:50],
                        value.flag1_ing_merce,
                        value.flag2_inventario,
                        tenant_id,
                        soggetto_id,
                    ),
                )
                if hasattr(c, "lastrowid") and c.lastrowid:
                    value.id = c.lastrowid
                value.soggetto_id = soggetto_id
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return value
        value.insert(c, conn)
        return value


def save(value, tenant_id=None):
    """Aggiorna un ``Fornitore`` (deve avere ``id``)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            try:
                c.execute(
                    "SELECT soggetto_id FROM fornitori "
                    "WHERE ID = %s AND tenant_id = %s",
                    (value.id, tenant_id),
                )
                row = c.fetchone()
                if row:
                    c.execute(
                        "UPDATE soggetti SET denominazione = %s "
                        "WHERE tenant_id = %s AND id = %s",
                        (value.azienda, tenant_id, row[0]),
                    )
                    c.execute(
                        "UPDATE fornitori SET azienda = %s, flag1_ing_merce = %s, "
                        "flag2_inventario = %s WHERE ID = %s AND tenant_id = %s",
                        (
                            value.azienda[:50],
                            value.flag1_ing_merce,
                            value.flag2_inventario,
                            value.id,
                            tenant_id,
                        ),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return value
        value.save(c, conn)
        return value


def delete(value, tenant_id=None):
    """Elimina un ``Fornitore`` dal database."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            try:
                c.execute(
                    "UPDATE soggetti s "
                    "JOIN fornitori f ON f.tenant_id = s.tenant_id "
                    "AND f.soggetto_id = s.id "
                    "SET s.attivo = 0 "
                    "WHERE f.ID = %s AND f.tenant_id = %s",
                    (value.id, tenant_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return
        value.delete(c, conn)
