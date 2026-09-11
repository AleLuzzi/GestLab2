# Istruzioni d'Uso — GestLab (SaaS + Desktop)

Documento operativo per l'accesso alla **console web SaaS** (con credenziali)
e per l'esecuzione della **versione desktop**.

---

## 1. Requisiti

- **Python 3.10+** installato e nel PATH.
- **MySQL** attivo e raggiungibile (le credenziali sono in `config.ini`,
  sezione `[DataBase]`).
- Installare le dipendenze:

```bash
python -m pip install -r requirements.txt
```

> Se si usa un ambiente virtuale (consigliato):
> ```bash
> python -m venv venv
> venv\Scripts\activate        # Windows
> python -m pip install -r requirements.txt
> ```

---

## 2. Console Web SaaS

### 2.1 Avvio del server

```bash
python -m uvicorn saas.main:app --reload
```

Il server parte su **http://localhost:8000/**.

| Risorsa | URL |
|---|---|
| **Console web** | http://localhost:8000/ |
| API docs (OpenAPI) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

### 2.2 Bootstrap del DB (prima volta)

Al primo avvio è necessario creare tutte le tabelle (business + SaaS) e
l'utente admin iniziale. Esegui (una sola volta, da terminale nella cartella
del progetto):

```bash
python -m saas.bootstrap
```

Il comando:
- Legge il file `saas/init_database.sql` (schema unificato).
- Crea tutte le tabelle di business (dipendenti, fornitori, prodotti, reparti,
  ecc.) con il supporto multi-tenant (colonna `tenant_id`).
- Crea le tabelle SaaS (`tenant`, `utenti`, `dispositivi_stampa`, `print_jobs`).
- Crea un tenant di default e un utente **admin** iniziale.

> Il comando è **idempotente**: se le tabelle o l'utente esistono già, non li
> ricrea. Puoi eseguirlo più volte senza problemi.

> **Nota**: in precedenza erano necessari i comandi `bootstrap` + `migrate_tenant`.
> Ora la migrazione è gestita direttamente dal file `init_database.sql`.

### 2.3 Credenziali di accesso

Le credenziali iniziali (create dal bootstrap) sono:

| Campo | Valore |
|---|---|
| **Email** | `admin@gestlab.it` |
| **Password** | `Admin123!` |

Ruolo: **admin** (può gestire utenti, tenant e dispositivi di stampa).

> ⚠️ **Importante**: queste sono credenziali di **sviluppo/test**. In
> produzione vanno cambiate e gestite tramite variabili d'ambiente / Secret
> Manager (vedi `core/env.py`). Puoi sovrascriverle al bootstrap con:
> ```bash
> $env:GESTLAB_ADMIN_EMAIL="admin@mio.laboratorio.it"
> $env:GESTLAB_ADMIN_PASSWORD="PasswordFortissima1!"
> python -m saas.bootstrap
> ```

### 2.4 Come entrare

1. Apri nel browser: **http://localhost:8000/**
2. Inserisci **Email** e **Password** indicate sopra.
3. Clicca **Accedi**.
4. Nella dashboard hai a disposizione (in base al ruolo):
   - **Dipendenti**: crea, modifica, elimina (admin/operatore).
   - **Lotti aperti**: elenco dei lotti del tenant corrente.
   - **Menu**: prodotti raggruppati per merceologia.
   - **Stampa**: genera DDT (PDF), scontrino (ESC/POS), etichetta DYMO (PDF).
   - **Barcode**: lookup prodotto tramite codice EAN.
   - **Coda di stampa**: lista dei job di stampa del tenant.
   - **Admin**: crea utenti e registra dispositivi di stampa (Local Print Agent).

### 2.5 Creare un altro utente / tenant

Dal pannello **Admin** (solo ruolo `admin`) puoi creare nuovi **utenti** nel
tuo tenant. Per creare un **nuovo tenant** si usa l'API:

```bash
curl -X POST http://localhost:8000/api/v1/tenant \
  -H "Authorization: Bearer <TOKEN_ADMIN>" \
  -H "Content-Type: application/json" \
  -d '{"nome": "Nuovo Laboratorio", "piano": "basic"}'
```

### 2.6 Registrare un Local Print Agent

Per la stampa automatica su hardware locale (DYMO, scontrino termico):

1. Dal pannello **Admin** → **Dispositivi**, registra un dispositivo
   (ottieni un token).
2. Avvia l'agent sul PC del punto vendita:

```bash
python -m saas.print_agent --token <TOKEN_DISPOSITIVO> --interval 5
```

Il Local Print Agent fa polling sulla coda `print_jobs` e stampa i documenti
sull'hardware fisico.

---

## 3. Versione Desktop

La versione desktop è la UI **KivyMD** (l'app originale GestLab2), che usa i
repository del core condiviso. Resta utile per il lavoro locale offline.

### 3.1 Avvio

```bash
python main.py
```

### 3.2 Prerequisiti desktop

Serve KivyMD (già in `requirements.txt`). Se manca:

```bash
python -m pip install kivy==2.3.1 kivymd==2.0.0
```

### 3.3 Funzioni disponibili nel menu desktop

| Funzione | Descrizione |
|---|---|
| **Ingresso Merce** | Registrazione movimenti di ingresso merce |
| **Nuovo Lotto** | Crea un nuovo lotto (riusa Ingresso Merce) |
| **Chiudi Lotti** | Chiude i lotti aperti |
| **Vendita Lotti** | Gestione lotti in vendita |
| **Nuovo Menu** | Composizione del menu (primi, secondi, contorni) |
| **Anagrafica Dipendenti** | CRUD dipendenti (richiede le tabelle DB) |

> **Nota**: la UI desktop legge direttamente dal DB MySQL locale (via
> `core/db.py`), senza tenant (filtro `tenant_id=None`). È pensata per uso
> locale/di sviluppo.

---

## 4. Test end-to-end

Per verificare che tutto funzioni (bootstrap DB, auth, stampa, barcode,
coda di stampa):

```bash
python tests/test_saas_e2e.py
```

Il test crea/usa le tabelle multi-tenant e un admin di test
(`admin@test.local` / `Prova123!`). Non va confuso con l'admin di produzione
creato dal bootstrap (`admin@gestlab.it` / `Admin123!`).

---

## 5. Configurazione (config.ini / .env)

- **`config.ini`** — sezione `[DataBase]` con le credenziali MySQL locali.
- **`.env`** (opzionale) — per i segreti in produzione (JWT secret, ecc.).
  Priorità: variabili d'ambiente → `.env` → `config.ini` (vedi `core/env.py`).

---

## 6. Risoluzione problemi

| Problema | Soluzione |
|---|---|
| `MySQL Connection ...` | Verifica che MySQL sia attivo e le credenziali in `config.ini` |
| `ModuleNotFoundError` | Esegui `python -m pip install -r requirements.txt` |
| Porta 8000 occupata | Usa `--port 8001`: `python -m uvicorn saas.main:app --reload --port 8001` |
| Login fallito | Verifica credenziali; se serve, riesegui `python -m saas.bootstrap` per (ri)creare l'admin |
