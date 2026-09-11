# Guida: Come Creare un Nuovo Tenant

Questa guida ti spiega come creare un nuovo tenant (cliente) nel sistema GestLab SaaS passo dopo passo.

---

## 📋 Prerequisiti

- Accesso al backend SaaS di GestLab
- Python 3.7+ installato
- Le variabili d'ambiente configurate (credenziali database)

---

## ✅ Passo 1: Preparare le Credenziali

Prima di creare il tenant, assicurati di avere:

- **Nome del tenant**: es. "Azienda XYZ Srl"
- **Piano di abbonamento**: `basic`, `pro`, `enterprise`
- **Email admin**: es. admin@aziendaxyz.it
- **Password admin**: una password sicura

**Esempio:**
```
Nome tenant: Ospedale Sant'Anna
Piano: pro
Email admin: admin@santanna.it
Password admin: SecurePass2024!
```

---

## ✅ Passo 2: Accedere al Backend

Apri il terminale e accedi alla cartella del progetto SaaS:

```bash
cd c:\Users\Ale\GestLab2\GestLab2
```

Attiva l'ambiente virtuale Python:

```bash
# Windows
venv\Scripts\activate

# MacOS/Linux
source venv/bin/activate
```

**Risultato atteso:** vedrai `(venv)` all'inizio della riga del terminale.

---

## ✅ Passo 3: Creare il Tenant con Python

Usa Python per creare il nuovo tenant. Esegui questo comando:

```bash
python -c "
from saas.tenant_repo import crea_tenant, crea_utente
from saas.auth import hash_password

# 1. Crea il tenant
tenant_id = crea_tenant('Ospedale SantAnna', 'pro')
print(f'✓ Tenant creato con ID: {tenant_id}')

# 2. Crea l'utente admin per questo tenant
password_hash = hash_password('SecurePass2024!')
utente_id = crea_utente(tenant_id, 'admin@santanna.it', password_hash, ruolo='admin')
print(f'✓ Utente admin creato con ID: {utente_id}')
print(f'Email: admin@santanna.it')
print(f'Password: SecurePass2024!')
"
```

**Risultato atteso:**
```
✓ Tenant creato con ID: 5
✓ Utente admin creato con ID: 42
Email: admin@santanna.it
Password: SecurePass2024!
```

---

## 💾 Passo 3bis: Come Viene Salvato nel Database

Quando esegui il comando precedente, accadono queste operazioni:

### 1️⃣ Salvataggio della Tabella `tenant`

Il tenant viene salvato nella tabella `tenant` con i seguenti campi:

| Campo | Valore | Tipo |
|-------|--------|------|
| `id` | 5 | Numero (generato automaticamente) |
| `nome` | Ospedale Sant'Anna | Testo (max 255 caratteri) |
| `piano` | pro | Testo: `basic`, `pro`, `enterprise` |
| `attivo` | 1 | Numero: 1=attivo, 0=disattivo |
| `creato_il` | 2026-09-11 15:30:45 | Data/Ora (automatica) |

**Query SQL eseguita internamente:**
```sql
INSERT INTO tenant (nome, piano) 
VALUES ('Ospedale Sant\'Anna', 'pro');
```

### 2️⃣ Salvataggio della Tabella `utenti`

L'utente admin viene salvato nella tabella `utenti` collegato al tenant:

| Campo | Valore | Tipo |
|-------|--------|------|
| `id` | 42 | Numero (generato automaticamente) |
| `tenant_id` | 5 | **Collegamento al tenant creato** |
| `email` | admin@santanna.it | Email unica nel database |
| `password_hash` | $2b$12$... | Hash sicuro della password (mai la password in chiaro!) |
| `ruolo` | admin | `admin`, `operatore`, `viewer` |
| `attivo` | 1 | Numero: 1=attivo, 0=disattivo |
| `creato_il` | 2026-09-11 15:31:02 | Data/Ora (automatica) |

**Query SQL eseguita internamente:**
```sql
INSERT INTO utenti (tenant_id, email, password_hash, ruolo, attivo) 
VALUES (5, 'admin@santanna.it', '$2b$12$...', 'admin', 1);
```

### 🔐 Sicurezza: La Password Non Viene Mai Salvata in Chiaro

La funzione `hash_password()` converte la password in un hash sicuro:

```
Password originale:    SecurePass2024!
                              ↓
                        [hash_password()]
                              ↓
Hash nel database:     $2b$12$x7nK9mQ2Pr5...z9K3xL2mN
```

Nessuno può leggere la password dal database, neanche un amministratore. L'hash viene verificato al login usando la funzione `verifica_password()`.

### 📊 Struttura Relazionale

```
┌─────────────────────────────────────────────────────────────┐
│                    TABELLA: tenant                           │
├─────────────────────────────────────────────────────────────┤
│ id: 5 (PRIMARY KEY)                                         │
│ nome: "Ospedale Sant'Anna"                                   │
│ piano: "pro"                                                 │
│ attivo: 1                                                    │
│ creato_il: 2026-09-11 15:30:45                              │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ FOREIGN KEY: tenant_id
                           │
┌─────────────────────────────────────────────────────────────┐
│                   TABELLA: utenti                            │
├─────────────────────────────────────────────────────────────┤
│ id: 42 (PRIMARY KEY)                                        │
│ tenant_id: 5 ← Collegato al tenant                          │
│ email: "admin@santanna.it" (UNIQUE)                          │
│ password_hash: "$2b$12$x7nK9mQ2Pr5...z9K3xL2mN"            │
│ ruolo: "admin"                                               │
│ attivo: 1                                                    │
│ creato_il: 2026-09-11 15:31:02                              │
└─────────────────────────────────────────────────────────────┘
```

**Nota:** Ogni utente è collegato a un tenant tramite `tenant_id`. Quando un utente accede con la sua email, il sistema:
1. Trova l'utente nel database
2. Verifica la password tramite hash
3. Recupera il `tenant_id` associato
4. Carica i dati specifici di quel tenant

---

## ✅ Passo 4: Verificare la Creazione

Verifica che il tenant sia stato creato correttamente:

```bash
python -c "
from saas.tenant_repo import trova_tenant

# Cerca il tenant con ID 5 (o l'ID che hai ricevuto)
tenant = trova_tenant(5)
if tenant:
    print(f'✓ Tenant trovato:')
    print(f'  - Nome: {tenant[\"nome\"]}')
    print(f'  - Piano: {tenant[\"piano\"]}')
    print(f'  - Attivo: {tenant[\"attivo\"]}')
else:
    print('✗ Tenant non trovato')
"
```

---

## 📝 Metodo Alternativo: Script Python

Se preferisci usare uno script, crea un file `crea_tenant.py` nella cartella `saas/`:

```python
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
```

Esegui lo script:
```bash
python saas/crea_tenant.py
```

---

## 🚀 Passo 5: Accedere al Sistema

Ora l'utente admin può accedere al sistema:

1. Apri l'applicazione web/desktop
2. Vai alla schermata di login
3. Inserisci:
   - **Email:** admin@santanna.it
   - **Password:** SecurePass2024!

4. Accesso concesso! ✅

---

## 🔧 Configurazione Aggiuntiva (Opzionale)

Dopo la creazione, puoi:

### Creare altri utenti per lo stesso tenant

```bash
python -c "
from saas.tenant_repo import crea_utente
from saas.auth import hash_password

tenant_id = 5  # L'ID del tenant
password_hash = hash_password('Operatore123!')
utente_id = crea_utente(tenant_id, 'operatore@santanna.it', password_hash, ruolo='operatore')
print(f'✓ Utente creato: {utente_id}')
"
```

### Cambiare il piano di abbonamento

```bash
python -c "
from core.db import connection

# Aggiorna il piano del tenant
with connection() as conn:
    c = conn.cursor()
    c.execute('UPDATE tenant SET piano = %s WHERE id = %s', ('enterprise', 5))
    conn.commit()
    print('✓ Piano aggiornato a enterprise')
"
```

---

## ❌ Troubleshooting

### Errore: "ModuleNotFoundError: No module named 'saas'"
**Soluzione:** Assicurati di essere nella cartella corretta e che l'ambiente virtuale sia attivato.

### Errore: "Connection refused" al database
**Soluzione:** Verifica che le credenziali database nelle variabili d'ambiente siano corrette (vedi `core/env.py`).

### Errore: "Duplicate entry for key 'email'"
**Soluzione:** L'email è già utilizzata da un altro tenant. Usa un'email diversa.

---

## � Visualizzare i Dati Salvati nel Database

Se vuoi verificare direttamente i dati nel database (per debugging), puoi usare questi comandi:

### Query 1: Visualizzare Tutti i Tenant

```bash
python -c "
from core.db import connection

with connection() as conn:
    c = conn.cursor()
    c.execute('SELECT id, nome, piano, attivo, creato_il FROM tenant')
    for row in c.fetchall():
        print(f'ID: {row[0]}, Nome: {row[1]}, Piano: {row[2]}, Attivo: {row[3]}, Creato: {row[4]}')
"
```

**Output:**
```
ID: 1, Nome: Laboratorio Principale, Piano: basic, Attivo: 1, Creato: 2026-09-10 10:15:00
ID: 5, Nome: Ospedale Sant'Anna, Piano: pro, Attivo: 1, Creato: 2026-09-11 15:30:45
```

### Query 2: Visualizzare Tutti gli Utenti di un Tenant

```bash
python -c "
from core.db import connection

tenant_id = 5
with connection() as conn:
    c = conn.cursor()
    c.execute('''
        SELECT id, email, ruolo, attivo, creato_il 
        FROM utenti 
        WHERE tenant_id = %s
    ''', (tenant_id,))
    for row in c.fetchall():
        print(f'ID: {row[0]}, Email: {row[1]}, Ruolo: {row[2]}, Attivo: {row[3]}, Creato: {row[4]}')
"
```

**Output:**
```
ID: 42, Email: admin@santanna.it, Ruolo: admin, Attivo: 1, Creato: 2026-09-11 15:31:02
```

### Query 3: Visualizzare un Utente Specifico con Password Hash

```bash
python -c "
from core.db import connection

email = 'admin@santanna.it'
with connection() as conn:
    c = conn.cursor()
    c.execute('''
        SELECT id, tenant_id, email, password_hash, ruolo, attivo
        FROM utenti 
        WHERE email = %s
    ''', (email,))
    row = c.fetchone()
    if row:
        print(f'ID Utente: {row[0]}')
        print(f'Tenant ID: {row[1]}')
        print(f'Email: {row[2]}')
        print(f'Password Hash: {row[3][:20]}...{row[3][-10:]}')  # Mostra solo inizio e fine
        print(f'Ruolo: {row[4]}')
        print(f'Attivo: {row[5]}')
"
```

---

## �📞 Supporto

Se riscontri problemi:
1. Leggi il file `saas/README.md` per dettagli tecnici
2. Controlla i log del database in `core/db.py`
3. Verifica che il file `saas/init_database.sql` sia presente e valido

---

**Ultimo aggiornamento:** Settembre 2026
