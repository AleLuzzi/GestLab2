# Backend SaaS GestLab

Backend FastAPI multi-tenant che riutilizza il core applicativo (`core.services`,
`core.repositories`) e l'architettura unificata della fusione GestLab2 + Laboratorio.

## Avvio

```bash
# installa le dipendenze
python -m pip install -r requirements.txt

# avvia il server di sviluppo
python -m uvicorn saas.main:app --reload
```

- **Console web (UI SaaS)**: <http://localhost:8000/>
- **Documentazione interattiva (OpenAPI)**: <http://localhost:8000/docs>

> La console web (`web/`) è una SPA vanilla (HTML/CSS/JS, nessuna build) servita
> direttamente dal backend FastAPI. Include login, dashboard, gestione dipendenti,
> lotti, menu, generazione DDT/scontrino/etichetta, lookup barcode EAN, coda di
> stampa e pannello admin (utenti + dispositivi).

## Struttura

```
saas/
├── main.py            # app FastAPI + route
├── auth.py            # JWT + bcrypt + dipendenze ruoli
├── schemas.py         # modelli Pydantic (request/response)
├── tenant_repo.py     # accesso DB tenant/utenti
├── schema_multitenant.sql  # schema multi-tenant (tenant, utenti, print_jobs...)
└── __init__.py
```

## Funzionalità esposte

| Metodo | Endpoint | Ruoli | Descrizione |
|---|---|---|---|
| POST | `/auth/login` | pubblico | Login, restituisce access+refresh |
| POST | `/auth/refresh` | pubblico | Rinnova i token |
| POST | `/api/v1/tenant` | admin | Crea tenant |
| POST | `/api/v1/utenti` | admin | Crea utente nel tenant |
| GET | `/api/v1/dipendenti` | autenticato | Elenco dipendenti |
| POST | `/api/v1/dipendenti` | admin/operatore | Crea dipendente |
| PUT | `/api/v1/dipendenti/{id}` | admin/operatore | Aggiorna dipendente |
| DELETE | `/api/v1/dipendenti/{id}` | admin | Elimina dipendente |
| GET | `/api/v1/lotti/aperti` | autenticato | Lotti aperti |
| GET | `/api/v1/menu` | autenticato | Prodotti del menu |
| GET | `/health` | pubblico | Health check |
| POST | `/api/v1/dispositivi` | admin | Registra un Local Print Agent (genera token) |
| POST | `/api/v1/print-jobs` | admin/operatore | Accoda un job di stampa |
| GET | `/api/v1/print-jobs` | autenticato | Elenco job di stampa (filtro stato) |
| GET | `/api/v1/print-jobs/{id}` | autenticato | Stato di un singolo job |
| GET | `/agent/next-job` | token dispositivo | L'agent preleva il prossimo job |
| POST | `/agent/{id}/done` | token dispositivo | L'agent segnala stampa completata |
| POST | `/agent/{id}/error` | token dispositivo | L'agent segnala errore |

## Coda di stampa e Local Print Agent

Il progetto implementa il modello "SaaS + local print agent" del piano
`SAAS_PRINTING_BARCODE_PLAN.md`:

1. **Generazione server-side**: i documenti (DDT, scontrini, etichette) sono
   generati dal service layer del core (`core/services/printing.py`).
2. **Coda `print_jobs`**: i job vengono accodati in DB per tenant
   (`saas/print_repo.py`), con stato `pending → printing → done/error`.
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

# 2) avvia il Local Print Agent sul PC del punto vendita
python -m saas.print_agent --token <TOKEN_DISPOSITIVO> --interval 5
```

Il token può anche essere letto da `config.ini` (sezione `[Stampante]`,
chiave `agent_token`) o dalla variabile d'ambiente `GESTLAB_AGENT_TOKEN`.

## Note multi-tenant

Il `tenant_id` viene estratto dal JWT lato server (mai dal client). I
repository del core (`core/repositories`) e i servizi (`core/services`)
filtrano i dati per `tenant_id` (modello A: schema condiviso). Il
`tenant_id` è **facoltativo** (`None` = nessun filtro, utile per la UI
desktop Kivy/Tkinter esistente).
