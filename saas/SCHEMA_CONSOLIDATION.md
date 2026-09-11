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
python -m pip install -r requirements.txt

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
   - `reparti`, `dipendenti`, `fornitori`, `merceologie`, `prodotti`, etc.
   - All include `tenant_id` column with `idx_tenant_id` index

4. **Reference/Legacy Tables**
   - `ingredienti_base`, `inventari`, `lotti_vendita_cucina`, etc.
   - Kept for backward compatibility; may be archived later

## Migration Path for Existing Databases

If migrating from the old schema:

1. **Backup your data** (always!)
2. **Run** `python -m saas.bootstrap`
   - If tables already exist, they're left unchanged (IF NOT EXISTS)
   - If `tenant_id` columns already exist, they're preserved
3. **Verify** all tables exist: `SHOW TABLES;`
4. **Test** login at `http://localhost:8000/`

## Verification Checklist

After running `python -m saas.bootstrap`:

- [ ] `SHOW TABLES;` returns 20+ tables
- [ ] `tenant` table exists and is empty (or has 1+ row)
- [ ] `utenti` table has the initial admin user
- [ ] `dispositivi_stampa` and `print_jobs` tables exist
- [ ] Business tables (`dipendenti`, `fornitori`, etc.) all have `tenant_id` column
- [ ] All `tenant_id` columns have `idx_tenant_id` index
- [ ] FK constraints are valid: `SHOW CREATE TABLE utenti;` shows CONSTRAINT
- [ ] Login works at `http://localhost:8000/` with credentials from bootstrap output

## Questions or Issues?

Refer to `docs_migrazione/ISTRUZIONI_USO.md` (Section 2.2) for troubleshooting.
