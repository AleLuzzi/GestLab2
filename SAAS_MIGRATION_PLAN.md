# Piano di Migrazione GestLab2 → SaaS

Documento strategico per trasformare **GestLab2** da applicazione desktop
(KivyMD + MySQL locale) a software **SaaS** multi-tenant accessibile via web.

---

## 1. Analisi dello stato attuale

| Componente | Stato attuale | Impatto per il SaaS |
|---|---|---|
| Frontend | KivyMD desktop (`main.kv`, schermate MD) | Da riprogettare come Web App (o client "fat" che chiama API) |
| Backend | Inesistente: la logica vive dentro i widget Kivy | Da estrarre in un vero backend con API |
| Database | MySQL locale, connessione globale singola (`controller_db.py`) | Da migrare su DB cloud con multi-tenancy |
| Credenziali | In chiaro in `config.ini` (password MySQL, token Facebook) | Da spostare in Secret Manager server-side |
| Integrazioni | Stampante DYMO locale, token Facebook | Da ripensare per il contesto cloud |
| Utenti | Nessun concetto di utente/login | Da introdurre autenticazione e ruoli |

---

## 2. Fasi del percorso di migrazione

### Fase 0 — Definizione del modello SaaS
1. **Definire il mercato target**: ogni cliente è un laboratorio/ristorante
   (multi-tenancy per "azienda").
2. **Scegliere il modello di isolamento dati**:
   - [ ] **A) Database condiviso, schema condiviso** + colonna `tenant_id`
     (più economico, richiede massima disciplina nelle query).
   - [ ] **B) Database condiviso, schema separato per tenant**
     (bilanciato: isolamento logico + costi contenuti).
   - [ ] **C) Database separato per tenant**
     (isolamento massimo, più costoso, adatto a clienti enterprise).
3. **Definire ruoli**: `admin` (configurazione, utenti), `operatore`
   (operatività quotidiana), eventuale `viewer`.
4. **Definire piani/pricing**: funzionalità per piano, limiti di utenti/lotti.

### Fase 1 — Backend e API REST
1. **Scegliere lo stack backend** (consigliato: **Python** per riusare la
   logica esistente):
   - **FastAPI** (moderno, async, documentazione OpenAPI automatica)
     oppure **Django + DRF** (admin pronto) o **Flask** (leggero).
2. **Estrarre la business logic dai widget Kivy** in un *service layer*:
   - `services/dipendenti.py`, `services/lotti.py`,
     `services/ingresso_merce.py`, `services/menu.py`, `services/vendite.py`.
3. **Esporre le API REST**:
   - `POST /auth/login` → JWT + refresh token
   - `GET/POST/PUT/DELETE /api/v1/dipendenti`
   - `GET /api/v1/fornitori`, `/api/v1/prodotti`, `/api/v1/tagli`,
     `/api/v1/merceologie`
   - `GET /api/v1/lotti/aperti`, `POST /api/v1/lotti/chiudi`
   - `POST /api/v1/ingresso-merce`
   - `GET/POST /api/v1/menu`
4. **Autenticazione e autorizzazione**: JWT (access+refresh), password
   hashing (bcrypt/argon2), middleware per tenant + ruolo.
5. **Validazione input lato server** (Pydantic/Schema).
6. **Audit log** per le operazioni sensibili (es. eliminazione dipendenti).

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
> Kivy/KivyMD non è eseguibile in browser. Due strade possibili:

- [ ] **Opzione A — Web App responsive** (consigliata per SaaS vero):
  React / Vue / Angular, oppure **Flet** o **NiceGUI** se si vuole restare
  in Python. Accessibile da browser, zero installazione per il cliente.
- [ ] **Opzione B — Client "fat" Kivy refactorizzato**: l'app desktop diventa
  un semplice client HTTP che chiama le API remote (login + server config),
  utile se serve stampa locale DYMO senza modifiche.

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
1. **Stampa DYMO**:
   - Web App → browser printing (formati ZPL/Esc-POS) oppure
     **client desktop sottile** per la sola stampa locale;
   - In alternativa servizi di cloud printing.
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

## 3. Criticità specifiche di GestLab2 da risolvere subito

1. **`controller_db.py`**: usa una **connessione globale condivisa** e un
   cursore unico (`c`). → Va sostituita con pool/ORM + repository pattern.
   È il refactoring **prioritario** prima di qualsiasi passo cloud.
2. **`config.ini` contiene segreti** (password DB, token Facebook). → Da
   eliminare/gestire via environment variables o Secret Manager.
3. **Logica UI accoppiata al DB**: i moduli (`anag_dipendenti`, `ingresso_merce`,
   ecc.) chiamano direttamente `db.*` dentro i widget. → Estrarre la logica
   in service layer e usare **chiamate HTTP asincrone** (lato client).
4. **Nessun concetto di utente/tenant** nello schema dati. → Aggiungere
   tabelle `utenti`, `tenant`/`aziende` e colonne `tenant_id`.
5. **Stampante DYMO locale**: è un vincolo fisico → valutare client sottile
   o cloud printing.

---

## 4. Roadmap consigliata (ordine di esecuzione)

| # | Step | Priorità |
|---|---|---|
| 1 | Refactoring `controller_db.py` (pool + repository) | Alta |
| 2 | Introduzione modello utenti/tenant nello schema | Alta |
| 3 | Creazione backend FastAPI/Django con API REST | Alta |
| 4 | Estrarre service layer dalla logica Kivy | Alta |
| 5 | Frontend web (o client Kivy refactorizzato) | Media |
| 6 | Migrazione DB su cloud + secret management | Media |
| 7 | Docker + CI/CD + deploy | Media |
| 8 | Sicurezza, GDPR, monitoring | Media |
| 9 | Pagamenti, onboarding tenant, migrazione dati clienti | Bassa |
| 10 | Test, pilot, go-live | Bassa |

---

## 5. Stack tecnologico consigliato (sintesi)

- **Backend**: Python + FastAPI + SQLAlchemy/Alembic
- **Auth**: JWT (access+refresh) + bcrypt; opzionale OAuth2
- **DB**: PostgreSQL gestito (AWS RDS / GCP Cloud SQL / Azure) multi-tenant
- **Frontend**: React/Vue (web) — o Flet/NiceGUI se si preferisce Python
- **Infra**: Docker + Cloud Run / ECS + Cloudflare/Let's Encrypt + S3/GCS
- **Background**: Celery / Cloud Tasks
- **Monitoring**: Sentry + Prometheus/Grafana + Loki
- **CI/CD**: GitHub Actions / GitLab CI

