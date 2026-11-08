# Schema Consolidation - Database Setup Simplification

## Overview

As of 2026-09-11, the database schema initialization has been consolidated from multiple files and manual steps into a unified system.

## What Changed

### Before (Fragmented)
- **Multiple SQL files:**
  - `docs_migrazione/gestlab_schema.sql` — auto-exported schema dump
  - `saas/schema_multitenant.sql` — added SaaS tables (tenant, utenti, dispositivi_stampa, print_jobs)
  
- **Multiple manual steps:**
  - `python -m saas.bootstrap` — created SaaS tables only
  - `python -m core.migrate_tenant` — added `tenant_id` columns to business tables
  - Manual verification of schema state

- **Pain points:**
  - Schema split across 2 files with overlapping definitions
  - Unclear execution order and dependencies
  - Risk of FK conflicts if steps executed in wrong order
  - Difficult to track what's deployed in different environments

### Now (Unified)
- **Single SQL file:**
  - `saas/init_database.sql` — unified schema with all tables (business + SaaS) in correct dependency order

- **Single bootstrap step:**
  - `python -m saas.bootstrap` — reads `init_database.sql`, creates all tables, seeds initial admin user

- **Benefits:**
  - Single source of truth for schema
  - Idempotent: safe to run multiple times
  - Clear table dependency ordering (tenant → utenti → dispositivi_stampa → print_jobs → business tables)
  - Works seamlessly for local dev, cloud RDS, and any MySQL-compatible database

## Legacy Files (No Longer Active)

The following files are now superseded and archived for reference only:

### `docs_migrazione/gestlab_schema.sql`
- **Reason:** Replaced by `saas/init_database.sql`
- **What it was:** Auto-exported schema dump from the legacy database
- **When to delete:** Once `init_database.sql` is validated in production
- **Archive date:** 2026-09-11

### `saas/schema_multitenant.sql`
- **Reason:** Replaced by `saas/init_database.sql`
- **What it was:** Manual schema additions for SaaS tables (tenant, utenti, etc.)
- **When to delete:** Once `init_database.sql` is validated in production
- **Archive date:** 2026-09-11

### `core/migrate_tenant.py`
- **Reason:** Replaced by `init_database.sql` (tenant_id columns pre-defined)
- **What it was:** Migration script to add `tenant_id` column to business tables
- **When to delete:** Once `init_database.sql` is validated in production
- **Archive date:** 2026-09-11
- **Note:** The logic is now baked into the initial table creation (no migration needed)

## How to Use the New System

### First-Time Setup (Local or Cloud)

```bash
# Install dependencies
python -m pip install -r requirements-web.txt

# Initialize database (creates all tables + initial admin user)
python -m saas.bootstrap
```

### Idempotency

The bootstrap script is fully idempotent. You can run it multiple times without error:
- If tables already exist, `IF NOT EXISTS` clause skips recreation
- If admin user already exists, it skips user creation

### Environment Variables

Override default credentials via env vars:

```bash
# Windows PowerShell
$env:GESTLAB_ADMIN_EMAIL="admin@my-lab.it"
$env:GESTLAB_ADMIN_PASSWORD="SuperSecure123!"
$env:GESTLAB_TENANT_NOME="My Laboratory"
python -m saas.bootstrap
```

```bash
# Linux/Mac
export GESTLAB_ADMIN_EMAIL="admin@my-lab.it"
export GESTLAB_ADMIN_PASSWORD="SuperSecure123!"
export GESTLAB_TENANT_NOME="My Laboratory"
python -m saas.bootstrap
```

## Schema Structure in `init_database.sql`

Tables are organized in sections:

1. **Tenant & Auth Layer** (parents)
   - `tenant` — laboratory/company
   - `utenti` — users with roles

2. **Print Infrastructure** (depends on tenant)
   - `dispositivi_stampa` — physical printers with tokens
   - `print_jobs` — print queue

3. **Business Tables** (multi-tenant via tenant_id)
   - `articoli` — catalogo operativo condiviso con la tracciabilità
   - `articoli_bilancia` — configurazione Bizerba per articolo
   - `reparti`, `dipendenti`, `fornitori`, `merceologie`, etc.
   - Tenant-scoped tables use tenant keys and indexes appropriate to the relation

4. **Traceability Tables**
   - `documenti_ingresso`, `lavorazioni`, `lotti`, and related movement/detail tables
   - `vendite` and `righe_vendita` — tenant-scoped sales document aggregate and lot-linked lines

The consolidated schema defines a primary key for every table, uses
`DECIMAL(12,3)` for quantities, requires tenant ownership with tenant foreign
keys, and uses `utf8mb4`. Department and operator relations are also
tenant-scoped. These definitions apply when creating tables; `CREATE TABLE IF
NOT EXISTS` does not update an existing table. Existing databases must receive
the corresponding versioned migrations before they can be considered aligned.
After creating tables and applying migrations, the bootstrap checks that every
table and column declared in `init_database.sql` exists and that every such
table has a primary key. It stops with the missing table, columns, or key rather
than reporting a successful setup for a partial schema. The same check runs for
new and existing databases.

The bootstrap also consolidates duplicate `progressivi` rows per tenant by
keeping the highest counters, then enforces `tenant_id NOT NULL` and a primary
key on `tenant_id`. Rows without a tenant cannot be assigned safely, so the
bootstrap stops and requests manual reconciliation instead of deleting them.

## Migration Path for Existing Databases

`python -m saas.bootstrap` is the single supported schema and migration entry
point for both new and existing databases. Back up existing databases before
running it. The canonical migration order is:

1. `20261003_stock_traceability.sql`
2. `20261031_articoli_input_lavorazione.sql`
3. `20261031_lotti_data_index.sql`
4. `20261031_soggetti_clienti_fornitori.sql`
5. `20261031_work_operator_id.sql`
6. `20261107_lotti_metadata.sql`
7. `20261107_lotti_tmc.sql`
8. `20261107_note_lotto.sql`
9. `20261107_movimenti_lotto_vendita.sql`
10. `20261108_ricette.sql`
11. `20261108_ricetta_ingredienti.sql`
12. `20261108_ricetta_allergeni_durata.sql`
13. `20261108_lavorazioni_ricetta.sql`
14. `20261108_dati_osa_tenant.sql`
15. `20261108_motivo_rettifica_lotto.sql`
16. `20261108_vendite.sql`

The order is explicit in `saas.bootstrap`; a test fails if a migration file is
added without being included. The bootstrap first runs `init_database.sql` to
create missing tables, then applies each unrecorded migration in the order
above. Successful versions are stored in `schema_migrations`, making later
runs skip only migrations already applied. A failure stops the bootstrap and
leaves that migration unrecorded.

On an empty database, the current `init_database.sql` is the schema baseline;
the bootstrap records all listed migrations as satisfied without replaying
historical `ALTER TABLE` statements. On an existing database without migration
history, the bootstrap recognizes migration effects already present and
records them; missing effects are applied. This also adopts changes made
manually before `schema_migrations` was introduced.

Before upgrading an existing schema:

1. **Back up the database.**
2. **Run** `python -m saas.bootstrap`.
   - If `ingresso_merce` exists, it is atomically renamed to
     `ingresso_merce_legacy_archive`; its rows are preserved without automatic
     conversion to tracked lots.
   - If both the legacy table and archive exist, bootstrap stops and requires
     manual reconciliation.
3. **Verify** `schema_migrations`, the schema and archived row counts against
   the pre-migration backup.
4. **Test** login at `http://localhost:8000/`.

Do not run individual migration files manually; use the bootstrap so the
version table remains authoritative.

## Verification Checklist

After running `python -m saas.bootstrap`:

- [ ] `SHOW TABLES;` returns 20+ tables
- [ ] `tenant` table exists and is empty (or has 1+ row)
- [ ] `utenti` table has the initial admin user
- [ ] `dispositivi_stampa` and `print_jobs` tables exist
- [ ] Business tables (`dipendenti`, `fornitori`, etc.) all have `tenant_id` column
- [ ] All `tenant_id` columns have `idx_tenant_id` index
- [ ] FK constraints are valid: `SHOW CREATE TABLE utenti;` shows CONSTRAINT
- [ ] Bootstrap reports schema validation successful for all required columns and primary keys
- [ ] Login works at `http://localhost:8000/` with credentials from bootstrap output

## Questions or Issues?

Refer to `docs_migrazione/ISTRUZIONI_USO.md` (Section 2.2) for troubleshooting.
