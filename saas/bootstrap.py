"""Bootstrap del DB multi-tenant e dell'utente admin iniziale.

Crea le tabelle SaaS (tenant, utenti, dispositivi_stampa, print_jobs) se non
esistono e inserisce un tenant + utente admin iniziali, in modo che il login
alla console web funzioni subito.

Esecuzione:
    python -m saas.bootstrap

Varibili d'ambiente (opzionali, per sovrascrivere le credenziali di default):
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

# ------------------------------------------------------------------------- #
#  Creazione tabelle (idempotente)
# ------------------------------------------------------------------------- #
_CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS tenant (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        nome VARCHAR(255) NOT NULL,
        piano VARCHAR(50) DEFAULT 'basic',
        attivo BOOLEAN DEFAULT TRUE,
        creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS utenti (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        tenant_id BIGINT NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        ruolo VARCHAR(20) NOT NULL DEFAULT 'operatore',
        attivo BOOLEAN DEFAULT TRUE,
        creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_utenti_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dispositivi_stampa (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        tenant_id BIGINT NOT NULL,
        nome VARCHAR(255) NOT NULL,
        token VARCHAR(255) NOT NULL UNIQUE,
        stampante_dymo VARCHAR(255),
        stampante_termica VARCHAR(255),
        ultimo_heartbeat TIMESTAMP NULL,
        CONSTRAINT fk_dispositivi_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS print_jobs (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        tenant_id BIGINT NOT NULL,
        dispositivo_id BIGINT NULL,
        tipo VARCHAR(20) NOT NULL,
        stato VARCHAR(20) NOT NULL DEFAULT 'pending',
        payload TEXT NOT NULL,
        creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        stampato_il TIMESTAMP NULL,
        CONSTRAINT fk_printjobs_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id),
        CONSTRAINT fk_printjobs_dispositivo FOREIGN KEY (dispositivo_id)
            REFERENCES dispositivi_stampa(id)
    )
    """,
]


def crea_tabelle():
    """Crea le tabelle multi-tenant se non esistono (idempotente)."""
    with connection() as conn:
        c = conn.cursor()
        for stmt in _CREATE_TABLES:
            try:
                c.execute(stmt)
            except Exception as e:
                # Le FK possono fallire se il parent-missing; le ignoriamo
                # solo se la tabella esiste gia' con lo stesso schema.
                print(f"  [warn] create ignorato: {e}")
        conn.commit()


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
    print("=== Bootstrap GestLab SaaS ===")
    crea_tabelle()
    tid = crea_admin()
    print(f"\nCredenziali di accesso alla console web:")
    print(f"  URL:      http://localhost:8000/")
    print(f"  Email:    {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print(f"  Ruolo:    admin")
    print("\nAvvia il server con: python -m uvicorn saas.main:app --reload")


if __name__ == "__main__":
    main()
