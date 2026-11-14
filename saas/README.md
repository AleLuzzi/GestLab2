# Backend SaaS GestLab

Backend FastAPI multi-tenant che riutilizza il core applicativo (`core.services`,
`core.repositories`) e l'architettura unificata della fusione GestLab2 + Laboratorio.
La console web è l'unica interfaccia applicativa supportata; Kivy/Tkinter sono
componenti legacy e non sono richiesti per lo sviluppo SaaS.

## Avvio

```bash
# installa le dipendenze
python -m pip install -r requirements-web.txt

# avvia il server di sviluppo
python -m uvicorn saas.main:app --reload
```

- **Console web (UI SaaS)**: <http://localhost:8000/>
- **Documentazione interattiva (OpenAPI)**: <http://localhost:8000/docs>

`GET /health` risponde 200 solo se il database esegue una lettura; se il
database non risponde, lo stato è 503 e `status` vale `degraded`. Il log
operativo in `logs/gestlab-saas.log` registra metodo, percorso, stato HTTP e
durata, con rotazione automatica (5 MB, fino a 5 file storici). Il health check
riuscito non viene scritto, per non riempire il file. Per scegliere un'altra
cartella, impostare `GESTLAB_LOG_DIR` prima di avviare il server. Un errore non
gestito riceve un riferimento assistenza, visibile nella risposta e nel log.
Con `SENTRY_DSN` e il pacchetto `sentry-sdk` lo stesso errore è inviato a
Sentry senza dati personali di default. Il riferimento consente di trovare il
traceback senza registrare token o dati del documento.

Il bootstrap consolida eventuali record `progressivi` duplicati per tenant,
conservando il valore massimo di ciascun contatore, e crea l'indice univoco
necessario anche sui database già esistenti. Aggiunge inoltre i campi EAN e
prezzo al catalogo `articoli` preesistente. Non cancella la vecchia tabella
`prodotti` né ne copia automaticamente i dati in `articoli_bilancia`: i database
di sviluppo già popolati vanno riconciliati esplicitamente.

Il bootstrap non crea più la tabella legacy `ingresso_merce`. Se la trova in un
database esistente, la rinomina atomicamente in
`ingresso_merce_legacy_archive`, preservandone schema e righe senza migrazione
automatica. Se esistono entrambe le tabelle, il bootstrap si interrompe per
evitare una riconciliazione ambigua. Dopo l'aggiornamento, verificare conteggi
e backup prima di pianificare un'eventuale migrazione dei record archiviati.

> La console web (`web/`) è una SPA vanilla (HTML/CSS/JS, nessuna build) servita
> direttamente dal backend FastAPI. Include login, dashboard, gestione dipendenti,
> articoli, lotti, menu, generazione DDT/scontrino/etichetta, lookup barcode EAN, coda di
> stampa e pannello admin (utenti + dispositivi).

Il catalogo operativo è `articoli`: nome, codice, categoria, unità di misura,
EAN e prezzo unitario sono condivisi da tracciabilità e lookup. I parametri
specifici delle bilance Bizerba sono separati in `articoli_bilancia` e collegati
all'articolo per tenant; la generazione dei file Bizerba non è ancora esposta
dal SaaS.

La console attuale consente la consultazione dei lotti aperti e del menu. La
chiusura/vendita lotti, la composizione del menu e il CRUD legacy dei tagli
sono fuori dal perimetro SaaS scelto. L'interfaccia non supporta l'uso offline.

## Struttura

```
saas/
├── main.py            # app FastAPI + route
├── auth.py            # JWT + bcrypt + dipendenze ruoli
├── schemas.py         # modelli Pydantic (request/response)
├── repositories/
│   ├── tenant_repo.py       # accesso DB tenant/utenti
│   ├── tracciabilita_repo.py # articoli, lotti e lavorazioni
│   └── print_repo.py        # dispositivi e coda di stampa
├── schema_multitenant.sql  # schema multi-tenant (tenant, utenti, print_jobs...)
└── __init__.py
```

## Funzionalità esposte

| Metodo | Endpoint | Ruoli | Descrizione |
|---|---|---|---|
| POST | `/auth/login` | pubblico | Login, restituisce access+refresh. Dopo 10 errori sullo stesso indirizzo, o 50 dallo stesso IP in 15 minuti, risponde 429 |
| POST | `/auth/refresh` | pubblico | Ruota il refresh token e revoca quello presentato |
| POST | `/auth/logout` | pubblico | Revoca la famiglia del refresh token |
| POST | `/auth/password-dimenticata` | pubblico | Invia il collegamento di reset se l'email è di un utente attivo |
| POST | `/auth/password-reimposta` | pubblico | Imposta una nuova password con un token monouso |
| POST | `/api/v1/tenant` | admin | Crea tenant |
| POST | `/api/v1/utenti` | admin | Crea utente nel tenant |
| GET | `/api/v1/soggetti` | autenticato | Elenco anagrafiche clienti/fornitori |
| POST | `/api/v1/soggetti` | admin/operatore | Crea anagrafica e assegna uno o entrambi i ruoli |
| PUT | `/api/v1/soggetti/{id}` | admin/operatore | Aggiorna dati, ruoli e stato dell'anagrafica |
| DELETE | `/api/v1/soggetti/{id}` | admin | Disattiva l'anagrafica senza cancellare lo storico |
| GET | `/api/v1/dipendenti` | autenticato | Elenco dipendenti |
| POST | `/api/v1/dipendenti` | admin/operatore | Crea dipendente |
| PUT | `/api/v1/dipendenti/{id}` | admin/operatore | Aggiorna dipendente |
| DELETE | `/api/v1/dipendenti/{id}` | admin | Elimina dipendente |
| GET | `/api/v1/lotti/aperti` | autenticato | Lotti aperti |
| POST | `/api/v1/tracciabilita/lotti/{id}/rettifiche` | admin/operatore | Rettifica atomica della giacenza con delta e motivo |
| GET | `/api/v1/tracciabilita/lotti/{id}/scheda.pdf` | autenticato | Scheda PDF del lotto con genealogia e DDT d'ingresso, non certificativa |
| GET | `/api/v1/vendite/lotti-disponibili` | autenticato | Lotti attivi con giacenza e non scaduti, ordinati FEFO; la UI vendita non è ancora collegata |
| GET | `/api/v1/menu` | autenticato | Listino operativo degli articoli attivi. `solo_disponibili=true` (default) tiene solo quelli con almeno un lotto vendibile; `false` include anche gli articoli attivi senza giacenza |
| GET | `/health` | pubblico | Health check |
| POST | `/api/v1/dispositivi` | admin | Registra un Local Print Agent (genera token) |
| POST | `/api/v1/print-jobs` | admin/operatore | Accoda un job di stampa |
| GET | `/api/v1/print-jobs` | autenticato | Elenco job di stampa (filtro stato) |
| GET | `/api/v1/print-jobs/{id}` | autenticato | Stato di un singolo job |
| GET | `/agent/next-job` | token dispositivo | L'agent preleva il prossimo job |
| POST | `/agent/{id}/done` | token dispositivo | L'agent segnala stampa completata |
| POST | `/agent/{id}/error` | token dispositivo | L'agent segnala errore |

## Anagrafiche clienti e fornitori

I dati comuni sono memorizzati in `soggetti`; `soggetti_ruoli` consente di
assegnare al medesimo soggetto il ruolo cliente, fornitore o entrambi. Le
impostazioni di ingresso merce e inventario restano specifiche dei fornitori.
I due flussi di ingresso accettano `fornitore_id` e salvano anche il nome
visualizzato sul documento come snapshot storico.

Il backup si crea con `python -m core.backup_database` e si ricarica solo in un
database vuoto, diverso da quello configurato:

```text
python -m core.backup_database --ripristina backups\gestlab_backup_AAAAMMGG_HHMMSS.sql --database gestlab_restore
```

Il comando rifiuta il database in uso e una destinazione che contiene già
tabelle. Non cancella la copia: al termine della prova va eliminata a parte.

Per un database già esistente, `saas.bootstrap` applica le migrazioni mancanti
in ordine e registra ogni versione in `schema_migrations`. Prima
dell'aggiornamento eseguire un backup. Le modifiche di schema già presenti
prima dell'introduzione del registro vengono riconosciute e registrate senza
riapplicare lo script; gli errori interrompono il bootstrap e non vengono
ignorati. L'ordine canonico e il comportamento per database nuovi ed esistenti
sono documentati in `saas/SCHEMA_CONSOLIDATION.md`.

## Coda di stampa e Local Print Agent

Il progetto implementa il modello "SaaS + local print agent" del piano
`SAAS_PRINTING_BARCODE_PLAN.md`:

1. **Generazione server-side**: i documenti (DDT, scontrini, etichette) sono
   generati dal service layer del core (`core/services/printing.py`).
2. **Coda `print_jobs`**: i job vengono accodati in DB per tenant
   (`saas/repositories/print_repo.py`), con stato `pending → printing → done/error`.
3. **Local Print Agent**: processo locale (`saas/print_agent.py`) che fa
   polling su `/agent/next-job`, stampa il documento sull'hardware fisico
   (DYMO, scontrino termico, PDF) e aggiorna lo stato.

### Registrare un dispositivo e avviare l'agent

```bash
# 1) (admin) registra il dispositivo via API -> ottieni un token
curl -X POST http://localhost:8000/api/v1/dispositivi \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"nome": "Pdv 1", "stampante_dymo": "DYMO LabelWriter 450 Turbo"}'
# -> {"id":1, "token":"<TOKEN_DISPOSITIVO>", ...}

# 2) sul PC di banco, in PowerShell come amministratore:
.\deploy\installa-print-agent.ps1 -Url "https://app.example.com" -Token "<TOKEN_DISPOSITIVO>"
```

Il token viene chiesto solo in questa installazione e salvato in
`%ProgramData%\GestLab\print-agent.env`. Lo script non lo ristampa. Il servizio
`GestLabPrintAgent` ha avvio automatico ritardato e, se il processo termina,
Windows lo riavvia. Al riavvio del PC parte da solo. La procedura completa è in
`docs_migrazione/PRINT_AGENT_WINDOWS.md`.

Sul PC Windows dell'agent installare anche il driver DYMO per tutti gli utenti.
`pywin32` serve alla stampa e al servizio; lo script di installazione lo
aggiunge nell'ambiente del banco. Non fa parte delle dipendenze del backend
SaaS, che può girare su Linux.

Il token può anche essere letto da `config.ini` (sezione `[Stampante]`,
chiave `agent_token`) solo in sviluppo. In produzione impostare
`GESTLAB_ENV=production` e fornire `GESTLAB_AGENT_TOKEN` tramite variabile
d'ambiente o Secret Manager; il fallback a `config.ini` è disabilitato.

Per stampare un'etichetta dalla console usare **Stampa su DYMO**: l'API
risolve i dati del lotto nel tenant, accoda il job e l'agent lo invia al nome
stampante `stampante_dymo` registrato per il dispositivo. Il nome deve
corrispondere a una stampante installata su Windows. Lo stato `done` indica
che Windows ha accettato il comando di stampa; verificare comunque la stampa
fisica e la resa dell'etichetta sul modello DYMO previsto.

## Note multi-tenant

Il `tenant_id` viene estratto dal JWT lato server (mai dal client). I
repository del core (`core/repositories`) e i servizi (`core/services`)
filtrano i dati per `tenant_id` (modello A: schema condiviso). Gli endpoint SaaS
ricavano il `tenant_id` dal token autenticato e non devono accettarlo dal client.
Il parametro facoltativo `tenant_id=None` resta solo per compatibilità interna
con componenti legacy; non è il percorso di accesso SaaS.
