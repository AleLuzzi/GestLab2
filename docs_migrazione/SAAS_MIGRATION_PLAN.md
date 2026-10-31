# Piano di Migrazione GestLab2 → SaaS

Documento strategico per lo sviluppo di **GestLab SaaS**, applicazione
multi-tenant accessibile via web. La decisione di prodotto è usare la console
web come unica interfaccia applicativa supportata; Kivy/KivyMD e la UI desktop
sono legacy e non sono il percorso di sviluppo.

Perimetro concordato: consultazione del menu e dei lotti/tracciabilità,
ingresso merce, anagrafiche web disponibili, barcode e stampa via agent. La
chiusura/vendita lotti, la composizione del menu, il CRUD legacy dei tagli e
l'uso offline sono fuori dal perimetro SaaS attuale.

---

## 1. Analisi dello stato attuale

| Componente | Stato attuale | Lavoro residuo |
|---|---|---|
| Frontend | Console web responsive in `web/` servita da FastAPI | Collaudo sui browser/tablet target |
| Backend | API FastAPI in `saas/` e servizi condivisi in `core/` | Completare solo i flussi inclusi nel prodotto |
| Database | MySQL/MariaDB con schema multi-tenant | Hardening e operatività di produzione |
| Credenziali | Variabili d'ambiente/.env con fallback legacy a `config.ini` | Rimuovere il fallback legacy in un intervento dedicato |
| Stampa/barcode | API e coda stampa; Local Print Agent per hardware locale | Collaudo sulle periferiche target |
| Utenti | Login, ruoli e tenant implementati | Revisione e hardening prima del go-live |
| Desktop | UI Kivy/KivyMD rimossa dal repository | Nessun client desktop supportato |

---

## 2. Fasi del percorso di migrazione

### Fase 0 — Definizione del modello SaaS
1. **Definire il mercato target**: ogni cliente è un laboratorio/ristorante
   (multi-tenancy per "azienda").
2. **Modello attuale**: **A) Database condiviso, schema condiviso** +
   colonna `tenant_id` (richiede disciplina nell'applicazione dei filtri).
   - [ ] **B) Database condiviso, schema separato per tenant**
     (bilanciato: isolamento logico + costi contenuti).
   - [ ] **C) Database separato per tenant**
     (isolamento massimo, più costoso, adatto a clienti enterprise).
3. Ruoli presenti: `admin` e `operatore`; permessi da verificare prima del
   rilascio.
4. Piani e limiti commerciali restano da definire.

### Fase 1 — Backend e API REST (realizzazione corrente)

Il backend è FastAPI (`saas.main:app`), con autenticazione JWT/ruoli,
validazione Pydantic e servizi/repository condivisi in `core/`. Sono presenti
API per login, tenant/utenti, anagrafiche supportate, ingresso merce, lotti
aperti, menu in consultazione, tracciabilità e stampa/barcode.

Lo stack e il perimetro non sono più scelte aperte: la console web è il client
ufficiale. Le API o funzioni non comprese nel perimetro concordato non vanno
date per disponibili solo perché comparivano nel piano iniziale.

### Fase 2 — Database cloud
1. **Sostituire la connessione globale singola** di `controller_db.py` con:
   - **Connection Pool** o **ORM** (SQLAlchemy / Django ORM) + **migrazioni**
     (Alembic / Django migrations).
2. **Provisioning DB gestito**: AWS RDS / Google Cloud SQL / Azure Database
   (PostgreSQL consigliato per funzionalità multi-tenant) oppure MySQL
   gestito per minimizzare il refactoring delle query.
3. **Abilitare**:
   - Backup automatici + snapshot + point-in-time recovery;
   - TLS in transito e crittografia a riposo;
   - Replica read-only per reportistica.
4. **Spostare le credenziali** da `config.ini` a un **Secret Manager**
   (AWS Secrets Manager / GCP Secret Manager / env del container).
5. **Pianificare la migrazione dati** per ciascun tenant (ETL dal MySQL
   locale → DB cloud), con mapping dello schema e pulizia dati.

### Fase 3 — Frontend

La direzione scelta è la console web responsive già presente in `web/`, servita
da `saas.main:app`. Non è prevista una seconda UI desktop Kivy. Le operazioni
che richiedono hardware locale usano il Local Print Agent, indipendente dalla
UI. L'eventuale supporto offline non è incluso: richiede un requisito e una
progettazione dedicati.

### Fase 4 — Infrastruttura cloud
1. **Containerizzare** il backend con **Docker** (Dockerfile + docker-compose
   per sviluppo).
2. **CI/CD**: GitHub Actions / GitLab CI (test → build immagine → deploy).
3. **Deploy** su servizi managed:
   - **Google Cloud Run** / **AWS ECS Fargate** (scaling automatico, semplice)
     oppure **Kubernetes** (EKS/GKE) se il progetto cresce.
4. **Networking**: dominio + HTTPS (Let's Encrypt / CDN tipo Cloudflare),
   Load Balancer.
5. **Storage oggetti** (S3 / GCS) per eventuali immagini/file.
6. **Worker asincroni** (Celery / RQ / Cloud Tasks) per operazioni lunghe
   (stampe, notifiche, esportazioni).

### Fase 5 — Sicurezza e GDPR
1. **Autenticazione robusta**: hashing password, rate limiting su login,
   opzionale **2FA**.
2. **Isolamento tenant**: test dedicati per garantire che un tenant non
   acceda ai dati di un altro (IDOR prevention).
3. **GDPR** (dati personali dei dipendenti!):
   - Informativa privacy e base giuridica;
   - Diritto di accesso, rettifica, **cancellazione** (già presente la
     funzione di delete, va resa conforme);
   - **Portabilità** (export dati tenant);
   - Data Processing Agreement (DPA) con i cloud provider;
   - Eventuale **DPO** e registro dei trattamenti.
4. **OWASP Top 10**: input validation, authN/authZ, security headers, WAF.
5. **Backup & Disaster Recovery** con RPO/RTO definiti.

### Fase 6 — Integrazioni esterne
1. **Stampa DYMO, DDT e scontrini + lettori barcode**:
   - Vedi il documento dedicato **`SAAS_PRINTING_BARCODE_PLAN.md`**.
   - Approccio consigliato: generazione **server-side** (PDF DDT, dati
     scontrino, etichette DYMO) + **Local Print Agent** per l'hardware.
   - Scontrino fiscale (se richiesto): stampa locale obbligatoria (modulo
     certificato / registratore telematico).
   - Lettori barcode: **HID keyboard-wedge** (zero driver) → lookup EAN via API.
2. **Token Facebook**: il token in `config.ini` scade → gestirlo
   **server-side** con refresh automatico (nessun segreto nel client).
3. **Altre integrazioni** (eventuali): fatturazione elettronica, contabilità,
   notifiche email (SMTP/SES).

### Fase 7 — Pagamenti e fatturazione (opzionale)
1. Integrazione **Stripe** / PayPal / billing provider per abbonamenti.
2. Gestione piani, sconti, fatture, portale clienti.

### Fase 8 — Monitoring e manutenzione
1. **Logging centralizzato** (ELK / Loki + Grafana).
2. **Error tracking** (Sentry) per backend e frontend.
3. **Metriche** (Prometheus): latenza, errori, utilizzo risorse.
4. **Alerting** e definizione **SLA**.
5. **Documentazione operativa** (runbook).

### Fase 9 — Onboarding e provisioning tenant
1. **Registrazione** (self-service o onboarding manuale).
2. **Provisioning automatico** del tenant: creazione schema/tenant_id,
   dati di default, utente admin iniziale.
3. **Strumento di migrazione dati** per i clienti esistenti (import dal
   vecchio MySQL locale → nuovo DB cloud).

### Fase 10 — Test e go-live
1. **Test unitari + integrazione** su API e isolamento tenant.
2. **Ambiente di staging** identico alla produzione.
3. **Piano di rollback**.
4. **Migrazione pilot** con 1 cliente reale → poi rollout progressivo.
5. **Formazione** e manuale utente.

---

## 3. Stato delle criticità individuate nel progetto originale

1. La connessione globale legacy è stata sostituita dal layer `core/db.py`
   con connessioni gestite a contesto e repository.
2. `config.ini` conserva credenziali legacy; rimuovere il fallback e ruotare i
   segreti resta un intervento separato.
3. La logica condivisa è esposta tramite `core/services` e repository; le UI
   Kivy/Tkinter sono state rimosse e non sono client supportati.
4. Tenant, utenti e filtro tenant sono presenti nello schema/API SaaS.
5. La stampa locale usa `saas/print_agent.py`; non è prevista una UI Kivy come
   sostituto dell'agent.

---

## 4. Roadmap consigliata (ordine di esecuzione)

| # | Step | Priorità |
|---|---|---|
| # | Step | Stato |
|---|---|---|
| 1 | Layer DB, repository e service layer | Implementato; verifiche specifiche restano |
| 2 | Tenant, utenti e API FastAPI | Implementato; hardening pre go-live |
| 3 | Stampa/barcode SaaS e Local Print Agent | Implementato; test hardware pendente |
| 4 | Console web responsive | Percorso ufficiale; collaudo iPad/Safari pendente |
| 5 | Infrastruttura Lightsail e guide deploy | Presente; validare staging/produzione |
| 6 | Hardening sicurezza, GDPR e monitoraggio | Da completare |
| 7 | Pricing, onboarding e migrazione dati | Da definire |
| 8 | Pilot e go-live | Da completare |

> Per DDT, scontrini e barcode vedi il documento dettagliato
> **`SAAS_PRINTING_BARCODE_PLAN.md`**.

---

## 5. Stack tecnologico consigliato (sintesi)

- **Backend**: Python + FastAPI + SQLAlchemy/Alembic
- **Auth**: JWT (access+refresh) + bcrypt; opzionale OAuth2
- **DB**: PostgreSQL gestito (AWS RDS / GCP Cloud SQL / Azure) multi-tenant
- **Frontend**: console responsive HTML/CSS/JavaScript servita da FastAPI
- **Infra**: Docker + Cloud Run / ECS + Cloudflare/Let's Encrypt + S3/GCS
- **Background**: Celery / Cloud Tasks
- **Monitoring**: Sentry + Prometheus/Grafana + Loki
- **CI/CD**: GitHub Actions / GitLab CI
