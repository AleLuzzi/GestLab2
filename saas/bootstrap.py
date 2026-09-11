"""Bootstrap del DB multi-tenant e dell'utente admin iniziale.

Legge e esegue il file init_database.sql (schema unificato) per creare tutte
le tabelle di business e SaaS. Quindi crea un tenant e un utente admin
iniziali.

Esecuzione:
    python -m saas.bootstrap

Variabili d'ambiente (opzionali, per sovrascrivere le credenziali di default):
    GESTLAB_ADMIN_EMAIL     (default: admin@gestlab.it)
    GESTLAB_ADMIN_PASSWORD  (default: Admin123!)
    GESTLAB_TENANT_NOME     (default: Laboratorio Principale)
"""

import os
import sys

# Assicura che il progetto sia nel path (se eseguito da altrove).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import connection
from saas import auth, tenant_repo

# Credenziali admin di default (sovrascrivibili via env).
ADMIN_EMAIL = os.environ.get("GESTLAB_ADMIN_EMAIL", "admin@gestlab.it")
ADMIN_PASSWORD = os.environ.get("GESTLAB_ADMIN_PASSWORD", "Admin123!")
TENANT_NOME = os.environ.get("GESTLAB_TENANT_NOME", "Laboratorio Principale")

# Percorso del file SQL unificato.
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "init_database.sql")


def _remove_sql_comments(sql_line):
    """Rimuove commenti SQL da una riga."""
    # Rimuove commenti -- (SQL standard)
    idx = sql_line.find("--")
    if idx != -1:
        sql_line = sql_line[:idx]
    return sql_line.strip()


def _parse_sql_statements(sql_content):
    """Parsifica il file SQL rimuovendo commenti e dividendo gli statement.
    
    Args:
        sql_content: contenuto grezzo del file SQL
        
    Returns:
        list: lista di statement SQL validi (non vuoti, senza commenti)
    """
    statements = []
    current_stmt = []
    
    for line in sql_content.split("\n"):
        # Rimuove commenti da questa riga
        clean_line = _remove_sql_comments(line)
        if not clean_line:
            continue
        
        current_stmt.append(clean_line)
        
        # Se la riga termina con ;, abbiamo uno statement completo
        if clean_line.endswith(";"):
            stmt = " ".join(current_stmt)
            # Rimuove il ; finale e il whitespace
            stmt = stmt.rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            current_stmt = []
    
    # Aggiunge l'ultimo statement se c'è
    if current_stmt:
        stmt = " ".join(current_stmt).rstrip(";").strip()
        if stmt:
            statements.append(stmt)
    
    return statements


def crea_tabelle():
    """Esegue init_database.sql per creare tutte le tabelle (idempotente)."""
    if not os.path.exists(SCHEMA_FILE):
        raise FileNotFoundError(f"Schema file non trovato: {SCHEMA_FILE}")

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Parsifica gli statement rimuovendo commenti
    statements = _parse_sql_statements(sql_content)
    
    if not statements:
        raise ValueError(f"Nessuno statement SQL trovato in {SCHEMA_FILE}")
    
    print(f"  Info: trovati {len(statements)} statement da eseguire")

    with connection() as conn:
        c = conn.cursor()
        executed = 0
        errors = 0
        
        for i, stmt in enumerate(statements, 1):
            try:
                c.execute(stmt)
                executed += 1
            except Exception as e:
                errors += 1
                error_msg = str(e).lower()
                # Ignora errori per tabelle già esistenti (IF NOT EXISTS).
                if "already exists" not in error_msg and "duplicate" not in error_msg:
                    print(f"  [err] Statement {i}: {e}")
                    print(f"        SQL: {stmt[:100]}...")
                else:
                    print(f"  [ok]  Statement {i} (tabella già esistente)")
        
        conn.commit()
    
    print(f"  OK  schema eseguito: {executed}/{len(statements)} statement completati, {errors} errori")
    if errors > 0:
        print(f"  Nota: alcuni errori potrebbero essere ignorabili (es. tabelle già esistenti)")


def crea_admin():
    """Crea tenant + admin iniziale se non esistono (idempotente)."""
    existing = tenant_repo.trova_utente_by_email(ADMIN_EMAIL)
    if existing:
        print(f"  OK  utente admin gia' presente (tenant {existing['tenant_id']})")
        return existing["tenant_id"]

    tid = tenant_repo.crea_tenant(TENANT_NOME, "basic")
    tenant_repo.crea_utente(tid, ADMIN_EMAIL, auth.hash_password(ADMIN_PASSWORD), "admin")
    print(f"  OK  tenant '{TENANT_NOME}' (id={tid}) creato")
    print(f"  OK  admin '{ADMIN_EMAIL}' creato")
    return tid


def main():
    print("=== Bootstrap GestLab SaaS ===\n")
    print(f"1. Creazione schema da: {SCHEMA_FILE}")
    crea_tabelle()
    print(f"\n2. Creazione tenant e admin iniziale")
    tid = crea_admin()
    print(f"\n✓ Setup completato!\n")
    print(f"Credenziali di accesso alla console web:")
    print(f"  URL:      http://localhost:8000/")
    print(f"  Email:    {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print(f"  Ruolo:    admin")
    print(f"\nAvvia il server con:")
    print(f"  python -m uvicorn saas.main:app --reload")


if __name__ == "__main__":
    main()

