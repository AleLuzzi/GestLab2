#!/usr/bin/env python
"""Script per creare un nuovo tenant."""

import sys
from saas.tenant_repo import crea_tenant, crea_utente
from saas.auth import hash_password

def main():
    # Configurazione
    NOME_TENANT = "Azienda Esempio Srl"
    PIANO = "basic"
    EMAIL_ADMIN = "admin@azienda.it"
    PASSWORD_ADMIN = "Admin123!"
    
    print("📋 Creazione nuovo tenant...")
    print(f"   Nome: {NOME_TENANT}")
    print(f"   Piano: {PIANO}")
    
    try:
        # Crea il tenant
        tenant_id = crea_tenant(NOME_TENANT, PIANO)
        print(f"✓ Tenant creato con ID: {tenant_id}")
        
        # Crea l'utente admin
        password_hash = hash_password(PASSWORD_ADMIN)
        utente_id = crea_utente(tenant_id, EMAIL_ADMIN, password_hash, ruolo='admin')
        print(f"✓ Utente admin creato con ID: {utente_id}")
        
        # Stampa le credenziali
        print("\n📝 Credenziali di accesso:")
        print(f"   Email: {EMAIL_ADMIN}")
        print(f"   Password: {PASSWORD_ADMIN}")
        print(f"   Tenant ID: {tenant_id}")
        
        return 0
    except Exception as e:
        print(f"✗ Errore: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())