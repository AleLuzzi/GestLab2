"""Migrazione multi-tenant: aggiunge la colonna ``tenant_id`` alle tabelle core.

Le tabelle originali del desktop (dipendenti, ingresso_merce, progressivi,
fornitori, prodotti, tagli) sono state create prima della migrazione SaaS e
non hanno la colonna ``tenant_id``. I repository condividono lo schema
(modello A: schema condiviso) e filtrano ``WHERE tenant_id = %s``, quindi
senza colonna le API SaaS falliscono con
``ProgrammingError: Unknown column 'tenant_id'``.

Questo script è idempotente e sicuro da rieseguire:
  - aggiunge ``tenant_id BIGINT NULL`` se mancante;
  - backfilla le righe esistenti con il primo tenant admin trovato;
  - crea un indice su ``tenant_id``.

Esecuzione:
    python -m core.migrate_tenant
"""

import sys

from core.db import connection

# Tabelle core da migrare (nome tabella -> colonna usata dalla query).
TABLES = [
    "dipendenti",
    "ingresso_merce",
    "progressivi",
    "fornitori",
    "prodotti",
    "tagli",
]


def _colonne(conn, tabella):
    """Restituisce l'insieme dei nomi di colonna della tabella."""
    c = conn.cursor()
    c.execute(f"SHOW COLUMNS FROM `{tabella}`")
    return {row[0] for row in c.fetchall()}


def trova_primo_tenant_admin():
    """Trova il tenant_id del primo utente admin (per il backfill)."""
    from saas import tenant_repo

    # Cerca l'admin di default; fallback: primo tenant esistente.
    for email_candidata in ("admin@gestlab.it", "admin@test.local"):
        u = tenant_repo.trova_utente_by_email(email_candidata)
        if u:
            return u["tenant_id"]
    # Fallback: primo tenant in ordine di id.
    with connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM tenant ORDER BY id LIMIT 1")
        row = c.fetchone()
    return row[0] if row else None


def migra():
    """Esegue la migrazione (idempotente)."""
    tenant_id = trova_primo_tenant_admin()
    print(f"Backfill tenant_id -> {tenant_id}")

    with connection() as conn:
        c = conn.cursor()
        for tabella in TABLES:
            cols = _colonne(conn, tabella)
            print(f"\n== {tabella} ==")
            if "tenant_id" not in cols:
                c.execute(
                    f"ALTER TABLE `{tabella}` "
                    "ADD COLUMN tenant_id BIGINT NULL"
                )
                print(f"  + colonna tenant_id aggiunta")
            else:
                print(f"  - colonna tenant_id già presente")

            if tenant_id is not None:
                c.execute(
                    f"UPDATE `{tabella}` SET tenant_id = %s "
                    "WHERE tenant_id IS NULL",
                    (tenant_id,),
                )
                print(f"  + righe backfillate: {c.rowcount}")

            # Crea indice se non esiste
            c.execute(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() "
                "AND table_name = %s "
                "AND index_name = 'idx_tenant_id'",
                (tabella,),
            )
            if c.fetchone()[0] == 0:
                c.execute(
                    f"ALTER TABLE `{tabella}` ADD INDEX idx_tenant_id (tenant_id)"
                )
                print(f"  + indice idx_tenant_id creato")
            else:
                print(f"  - indice idx_tenant_id già presente")

        conn.commit()

    print("\nMigrazione completata.")


if __name__ == "__main__":
    migra()
