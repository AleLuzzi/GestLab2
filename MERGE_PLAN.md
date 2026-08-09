# Piano di Fusione GestLab2 + Laboratorio → Base SaaS

Documento strategico per unificare i due progetti (evitando la doppia
manutenzione) e predisporre la migrazione SaaS descritta in
`SAAS_MIGRATION_PLAN.md` e `SAAS_PRINTING_BARCODE_PLAN.md`.

---

## 1. Stato attuale dei due progetti

| Aspetto | **GestLab2** (KivyMD) | **Laboratorio** (CustomTkinter) |
|---|---|---|
| GUI | KivyMD desktop (`main.py` + `main.kv`) | CustomTkinter/Tkinter (`main.pyw` + `main_TKinter.py`) |
| Data layer | `controller_db.py` (connessione globale + cursore `c`) | `db.py` (context manager `connection()`) |
| Config | inline `_leggi_config()` | `config.py` (`get_config()` con cache) |
| Moduli | 5: anag_dipendenti, chiudi_lotto, ingresso_merce, lotti_vendita, nuovo_menu | ~15 completi (fornitori, ingredienti, merceologie, reparti, tagli, dosi, inventario, nuovo_lotto, cucina...) |
| Pattern | Query SQL nei widget | Model/Controller/Repository |
| Stampa/PDF | Assente | ReportLab (DDT, etichette DYMO), win32 |
| Piano SaaS | Documentazione completa | Assente |

**Scelta di fondo:** il progetto **Laboratorio** è funzionalmente il più
completo e ha il data layer migliore (`db.py`, repository). Il progetto
**GestLab2** ha l'UI più moderna (KivyMD) e già i piani SaaS.

Per il SaaS il framework GUI è secondario (il frontend sarà ricostruito/web).
La priorità è **unificare la business logic e il data layer** in un *core*
condiviso e framework-agnostico.

---

## 2. Principio guida della fusione

> **"Un solo core di dominio, UI intercambiabile."**

Creare un progetto unico con struttura a 3 livelli:

```
gestlab/                      # ← progetto unificato (riferimento)
├── core/                     # business logic + data layer (framework-agnostico)
│   ├── db.py                 # connessione/pool (da Laboratorio/db.py)
│   ├── config.py             # lettura config (da Laboratorio/config.py)
│   ├── models/               # ORM/repository (da Laboratorio: fornitore, taglio, mov...)
│   ├── services/             # servizi (lotti, ingresso_merce, menu, vendite, stampa)
│   └── repositories/         # accesso dati per entità
├── ui_tkinter/               # UI CustomTkinter (mantiene tutte le feature esistenti)
├── ui_kivy/                  # (opzionale) UI KivyMD riusando il core
└── saas/                     # backend FastAPI + agent locale (fase 2 SaaS)
```

Regole:
1. **Nessuna query SQL dentro i widget** → tutto finisce in `core/`.
2. **Un solo file di connessione DB** (`core/db.py`) adottato da entrambe le UI.
3. **Config unificata** (`core/config.py`) con segreti esternalizzati.
4. Le UI (Tkinter/Kivy) diventano **sottili**: chiamano i servizi del core.

---

## 3. Passi operativi della fusione

### Fase A — Preparazione & inventario
- [ ] **A1.** Creare repo unico `gestlab/` e spostare sotto di esso i sorgenti.
- [ ] **A2.** Inventario delle funzionalità: mappa modulo → file in *entrambi*
      i progetti, evidenziando i duplicati (es. `ingresso_merce`, `chiudi_lotto`,
      `lotti_vendita`, `nuovo_menu`, `anag_dipendenti` presenti in entrambi).
- [ ] **A3.** Definire il **modulo di riferimento** per ogni funzionalità
      (consigliato: prendere la versione più completa — laboratorio — come base).
- [ ] **A4.** Unificare `requirements.txt` (kivy+kivymd NON servono per il
      backend; servono solo per la UI scelta).

### Fase B — Unificazione del data layer (priorità alta)
- [ ] **B1.** Adottare `core/db.py` (context manager `connection()`) al posto di
      `controller_db.py`. Eliminare la connessione globale `c`.
- [ ] **B2.** Adottare `core/config.py` da `Laboratorio/config.py`.
- [ ] **B3.** Portare i **model/repository** di Laboratorio nel core
      (`fornitore.py`, `tagli.py`, `mov_ingresso_merce.py`, `dipendente.py`, ...).
- [ ] **B4.** Migrare le query sparse di GestLab2 nei repository del core
      (`_recupera_primi`, `_lista_tagli`, `_recupera_lotti_aperti`, ...).
- [ ] **B5.** Aggiungere `tenant_id` a ogni repository (già pianificato nei
      piani SaaS) → predisporre multi-tenancy sin d'ora.

### Fase C — Scelta UI e unificazione moduli
- [ ] **C1.** **Decidere la UI di riferimento.** Consiglio: mantenere la UI
      **Tkinter/CustomTkinter** per desktop (più completa) e **non** portare
      avanti KivyMD (Kivy non gira in browser, per il SaaS serve comunque una
      Web App). KivyMD va **congelato** e sostituito dalla Web App.
- [ ] **C2.** Per ogni modulo: mantenere la versione più completa (da
      Laboratorio) e rimuovere il duplicato in GestLab2.
- [ ] **C3.** Eliminare i file orfani di GestLab2 (`main.kv`, screens Kivy che
      non verranno usati) oppure spostarli in `ui_kivy/` come riferimento.

### Fase D — Service layer condiviso
- [ ] **D1.** Estrarre la logica applicativa in `core/services/`
      (`lotti.py`, `ingresso_merce.py`, `menu.py`, `vendite.py`, `dipendenti.py`).
- [ ] **D2.** Spostare stampa/PDF in `core/services/printing.py` (ReportLab)
      e barcode in `core/services/barcode.py` (già pianificati).
- [ ] **D3.** Le UI chiamano solo i servizi → drastica riduzione duplicazione.

### Fase E — Verifica e pulizia
- [ ] **E1.** `python -m py_compile` su tutti i file.
- [ ] **E2.** Test manuale di tutti i moduli (ingresso merce, chiudi lotto,
      vendite, menu, anagrafiche, stampa).
- [ ] **E3.** Aggiornare `config.ini` unificato; spostare i segreti in `.env`.
- [ ] **E4.** Aggiornare `TODO.md` e i documenti SaaS con la nuova struttura.

---

## 4. Passi per la migrazione SaaS (dopo la fusione)

Vedi anche `SAAS_MIGRATION_PLAN.md` e `SAAS_PRINTING_BARCODE_PLAN.md`.
La fusione rende il SaaS molto più semplice:

1. **Backend FastAPI** che importa `core/services/*` e `core/repositories/*`
   (già framework-agnostici) → niente più logica nelle UI.
2. **Models con `tenant_id`** già in `core/` → multi-tenancy immediata.
3. **`core/db.py`** sostituito da **pool + SQLAlchemy/Alembic** per il cloud.
4. **Web App** (React/Vue o Flet/NiceGUI) che sostituisce Tkinter/Kivy.
5. **Local Print Agent** per hardware locale (DYMO, scontrini, bilancia)
   riusando `core/services/printing.py`.
6. **Segreti** (DB, token Facebook) fuori da `config.ini` → Secret Manager/env.

---

## 5. Roadmap sintetica

| # | Azione | Priorità |
|---|---|---|
| 1 | Fusione: unico repo + inventario funzionalità | Alta |
| 2 | Unificare data layer (`core/db.py`, `core/config.py`, repository) | Alta |
| 3 | Scelta UI (mantenere Tkinter, congelare KivyMD) | Alta |
| 4 | Service layer condiviso `core/services/` | Alta |
| 5 | Refactoring `controller_db.py` → pool + `tenant_id` | Alta |
| 6 | Backend FastAPI + API REST | Alta |
| 7 | Web App frontend | Media |
| 8 | Local Print Agent + coda `print_jobs` | Media |
| 9 | Migrazione DB cloud + secret management | Media |
| 10 | Sicurezza, GDPR, monitoring, pagamenti | Media/Bassa |

---

## 6. Decisioni da prendere (open questions)

- [ ] **Q1.** Quale framework UI mantenere per il desktop nella fase di
      transizione? (Consiglio: Tkinter/CustomTkinter, più completo)
- [ ] **Q2.** KivyMD va **eliminato** o **preservato come riferimento**? 
      (Consiglio: eliminare, sostituito dalla Web App SaaS)
- [ ] **Q3.** Il DB di riferimento è quello di Laboratorio (più schema completo)?
      (Consiglio: sì, `data.sql` di Laboratorio come base schema)
- [ ] **Q4.** Si vuole migrare subito a PostgreSQL/SQLAlchemy o restare su
      MySQL per ridurre il refactoring iniziale?
- [ ] **Q5.** Quale modello di isolamento tenant (A/B/C del piano generale)?
