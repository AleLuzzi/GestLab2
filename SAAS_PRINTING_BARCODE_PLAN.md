# Piano di Integrazione Stampa (DDT, Scontrini) e Lettori Barcode in SaaS

Documento di dettaglio che integra il piano generale `SAAS_MIGRATION_PLAN.md`
(trasformazione GestLab2 da desktop a SaaS multi-tenant) con tre funzionalità
critiche del laboratorio:

1. **Stampa Documenti di Trasporto (DDT)** — formato A4, carta bianca.
2. **Stampa Scontrini / Ricevute** — stampa termica (ESC/POS), formati fiscali.
3. **Lettori Barcode** — lettura EAN/QR sul punto vendita e in cucina.

Questi tre elementi sono tra i più delicati in migrazione cloud perché
dipendono da **hardware locale** (stampanti, lettori) e da **vincoli normativi**
(scontrino, DDT). Il documento chiarisce come preservarli in un'architettura
SaaS senza sacrificare l'esperienza dell'utente finale.

---

## 1. Perché stampa e barcode sono casi speciali nel SaaS

| Aspetto | App desktop (Tkinter/Kivy) | SaaS web |
|---|---|---|
| Stampante DYMO/termica | Accesso diretto via `win32print`/`win32api` | Il browser NON accede direttamente all'hardware |
| Scontrino fiscale | Generazione + stampa locale | Serve stampa locale o cloud printing |
| Lettore barcode | USB/HID = "tastiera" (nessun driver) | Il browser deve catturare l'input da tastiera |
| DDT | PDF + `ShellExecute("print")` | Generazione PDF remota + stampa locale |
| File bilancia (WinSwGx `.dat`) | Scrittura su share di rete | Necessario client/thin agent locale |

**Conclusione:** per queste funzionalità serve un **modello ibrido**:
- **SaaS cloud** per la gestione dati, autenticazione, multi-tenant, report.
- **Thin local agent o print spooler** per l'hardware fisico (stampanti, bilancia).

---

## 2. Architettura consigliata: "SaaS + local print agent"

```
┌──────────────────────────┐        ┌──────────────────────────┐
│   Browser (Web App)      │        │   Client "sottile" local │
│   - UI vendita/cucina    │        │   (Kivy refactorizzato)  │
│   - inserimento EAN      │        │   oppure Tray Agent)     │
└───────────┬──────────────┘        └───────────┬──────────────┘
            │  HTTPS + JWT                        │  HTTPS + JWT
            ▼                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Backend SaaS (FastAPI/Django)              │
│  - Auth multi-tenant          - API stoccaggio stampa       │
│  - Gestione dipendenti/lotti  - Coda stampa (print queue)   │
│  - Generazione PDF (DDT)      - Gestione scontrini          │
├─────────────────────────────────────────────────────────────┤
│  DB cloud multi-tenant (PostgreSQL) + Object Storage (S3)   │
└─────────────────────────────────────────────────────────────┘
            │ print job (job id)                       ▲ token
            ▼                                          │
┌──────────────────────────┐        ┌──────────────────────────┐
│  Local Print Agent       │        │  Lettore Barcode (USB)   │
│  - poll/websocket coda   │        │  Input HID = tastiera    │
│  - stampa DYMO/termica   │        │  → Web App o Agent locale│
│  - invio file bilancia   │        │  → lookup EAN su API     │
└──────────────────────────┘        └──────────────────────────┘
```

**Componenti chiave:**

1. **Backend SaaS** — genera i documenti (PDF DDT, dati scontrino, etichette DYMO)
   e li mette in una **coda di stampa** per tenant.
2. **Local Print Agent** — piccolo processo (o client Kivy refactorizzato) sul
   PC del punto vendita: autenticato via JWT, **polling o WebSocket** sulla coda,
   inoltra i job alla stampante fisica.
3. **Lettore barcode** — funziona ovunque perché è un **keyboard-wedge** (digit
   + `Enter`). La Web App o l'Agent catturano la stringa e chiamano l'API di lookup.

---

## 3. Stampa Documenti di Trasporto (DDT)

### 3.1 Stato attuale (Tkinter)
In `lotti_vendita.py` esiste già generazione PDF con **ReportLab**:
- `SimpleDocTemplate` + `Table` per il dettaglio lotto.
- `win32api.ShellExecute(None, "print", "traccia.pdf", ...)` per la stampa.
- L'intestazione DDT (numero documento, fornitore, data) è già in
  `ingresso_merce` (campo `NUMERO DOCUMENTO`, progressivo).

### 3.2 Target SaaS

**Generazione lato server (centrale):**
- Endpoint `POST /api/v1/ddt` — crea un DDT da un lotto / ingresso merce.
- Il backend genera il **PDF A4** con ReportLab (riusando la logica esistente)
  e lo salva su **Object Storage** (S3/GCS) con riferimento in DB.
- Il PDF è associato al `tenant_id` e al `lotto_id`.

**Stampa lato locale:**
- Opzione A (consigliata): il job di stampa finisce nella *print queue* del
  tenant → il **Local Print Agent** lo scarica e lo manda alla stampante di rete.
- Opzione B: l'utente dal browser scarica il PDF e lo stampa manualmente
  (0 installazione, ma meno automatico).

**Riepilogo campi DDT da presidiare:**
| Campo | Origine | Note |
|---|---|---|
| Numero progressivo DDT | Sequence DB per tenant | Deve essere unico per tenant |
| Data documento | Generata + modificabile | Formato `dd/mm/yy` |
| Fornitore | Tabella fornitori | `flag1_ing_merce = 1` |
| Articoli / tagli | Tabella tagli/prodotti | merceologici |
| Quantità/peso | Righe ingresso merce | `peso_i`, `peso_f` |
| Merceologia | Tabella merceologie | es. Primi, Secondi, Contorni |

---

## 4. Stampa Scontrini / Ricevute

### 4.1 Stato attuale
- Nel progetto originale esistono moduli di **etichette DYMO** (`lotti_vendita_cucina.py`)
  via ReportLab `canvas` su formato `54 x 101 mm`.
- Non c'è ancora un modulo scontrino fiscale completo; va introdotto.
- `config.ini` ha già la sezione `[Stampante] stampa = DYMO LabelWriter 450 Turbo`.

### 4.2 Target SaaS

**Due formati distinti da supportare:**

1. **Etichetta DYMO** (etichette prodotto, già esistente):
   - Generata come **PDF** (ReportLab) o direttamente come **ZPL/ESC-POS**.
   - Stampata dal **Local Print Agent** sulla DYMO.
   - Da preservare: PLU, ingredienti, prezzo €/kg, codice.

2. **Scontrino / ricevuta termica** (nuovo):
   - Generato lato server come **testo ESC/POS** (larghezza 80mm o 58mm).
   - La coda di stampa lo consegna all'Agent che lo invia alla **stampante
     termica** (via `python-escpos` o `win32print` raw).
   - Se il cliente richiede **scontrino fiscale** (RT), va gestito un modulo
     certificato (misuratore fiscale / registratore telematico): in questo caso
     **la stampa NON può essere remota** → serve il **Local Print Agent**
     obbligatorio, oppure un **server RT** dedicato.

**Librerie server-side consigliate:**
- `reportlab` — PDF DDT ed etichette DYMO.
- `python-escpos` — scontrini termici (ESC/POS) via rete/USB.
- `qrcode` / `barcode` — generazione QR/EAN nel documento.

**Flusso scontrino:**
1. L'operatore seleziona lotti/barcode nella **Web App**.
2. Il backend calcola totale, IVA, dati scontrino → invia job alla coda.
3. Il **Local Print Agent** stampa la ricevuta termica.
4. (Opzionale) Il backend salva copia digitale dello scontrino per audit/GDPR.

---

## 5. Lettori Barcode

### 5.1 Stato attuale
- In `ingredienti.py` c'è il campo **EAN** (inserimento codice + pezzi/quantità).
- Il lettore barcode è un dispositivo **USB/HID keyboard-wedge**: quando legge
  un codice invia i caratteri + `Enter`, esattamente come una tastiera.
- Non servono driver particolari → questo è il punto di forza per il SaaS.

### 5.2 Target SaaS

**Approccio Web App (consigliato):**
- Un campo di input con **focus fisso** cattura la stringa del barcode.
- Gestione dell'evento `Enter` (o un prefisso/suffisso configurabile) per
  distinguere la lettura da una digitazione manuale.
- La stringa viene inviata a `GET /api/v1/prodotti/ean/{codice}` (con `tenant_id`).
- La risposta popola il campo prodotto/quantità e richiama il flusso di vendita.

**Accorgimenti anti-errori:**
- **Timeout** tra letture consecutive (evita letture multiple accidentali).
- **Debounce**: piccola attesa per verificare che la stringa sia completa.
- **Validazione** del codice (EAN-13 check digit) lato server.

**Confronto opzioni:**
| Opzione | Pro | Contro |
|---|---|---|
| **A. Web App + HID** (consigliata) | Zero installazione | Dipende dal focus del browser |
| **B. Local Agent che inoltra letture** | Più robusto, offline | Richiede installazione |
| **C. Scanner 2D con API nativa** | Massima precisione | Costo hardware superiore |

**Sconsigliato:** usare librerie di acquisizione video (OpenCV) per leggere
barcode dalla webcam: lente, imprecise e meno affidabili di un HID.

---

## 6. Modello dati multi-tenant da aggiungere

```sql
-- Tenant (azienda/laboratorio)
CREATE TABLE tenant (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    piano VARCHAR(50) DEFAULT 'basic',
    attivo BOOLEAN DEFAULT TRUE,
    creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Utenti (admin, operatore, viewer) con tenant_id
CREATE TABLE utenti (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL REFERENCES tenant(id),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    ruolo VARCHAR(20) NOT NULL DEFAULT 'operatore',
    attivo BOOLEAN DEFAULT TRUE
);

-- Macchina fisica che esegue il Local Print Agent
CREATE TABLE dispositivi_stampa (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL REFERENCES tenant(id),
    nome VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,   -- JWT/API key dell'agent
    stampante_dymo VARCHAR(255),
    stampante_termica VARCHAR(255),
    ultimo_heartbeat TIMESTAMP NULL
);

-- Coda di stampa (job)
CREATE TABLE print_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL REFERENCES tenant(id),
    dispositivo_id BIGINT REFERENCES dispositivi_stampa(id),
    tipo VARCHAR(20) NOT NULL,            -- ddt | scontrino | etichetta
    stato VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending|printing|done|error
    payload TEXT NOT NULL,                -- JSON/ZPL/ESC-POS/PDF url
    creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stampato_il TIMESTAMP NULL
);
```

**Nota:** ogni tabella business esistente (`ingresso_merce`, `lotti_vendita`,
`dipendenti`, ecc.) dovrà avere la colonna `tenant_id` (modello A: schema
condiviso) oppure essere replicata per schema (modello B). Vedi
`SAAS_MIGRATION_PLAN.md` Fase 0.

---

## 7. Roadmap operativa integrata

| # | Step | Priorità | Collegamento |
|---|---|---|---|
| 1 | Refactoring `controller_db.py` (pool + repository + `tenant_id`) | Alta | Fase 1/2 piano generale |
| 2 | Backend FastAPI/Django con API auth + tenant | Alta | Fase 1 |
| 3 | Service layer stampa: `services/printing.py` (DDT, etichette, scontrini) | Alta | Nuovo |
| 4 | Service layer barcode: `services/barcode.py` (lookup EAN) | Alta | Nuovo |
| 5 | Coda `print_jobs` + endpoint `POST /api/v1/print-jobs` | Media | Nuovo |
| 6 | **Local Print Agent** (polling coda + stampa locale) | Media | Nuovo |
| 7 | Web App: campo barcode HID + UI vendita | Media | Nuovo |
| 8 | Migrazione dati per tenant + export | Media | Fase 9 |
| 9 | Sicurezza, GDPR, audit (scontrini) | Media | Fase 5 |
| 10 | Test, pilot, go-live | Bassa | Fase 10 |

---

## 8. Criticità specifiche da risolvere subito

1. **`controller_db.py`** ha una connessione globale condivisa → incompatibile
   con multi-tenancy e con il backend asincrono. Prima di tutto refactoring.
2. **`config.ini` contiene segreti** (password DB, token Facebook) → vanno
   spostati in env/Secret Manager; il nome stampante (`[Stampante]`) resta un
   dato di configurazione del **dispositivo locale**, non del tenant centrale.
3. **Stampa DYMO/termica locale** → il vincolo fisico impone il **Local Print
   Agent**; senza di esso la stampa non è automatica nel SaaS.
4. **Scontrino fiscale** → se richiesto, la stampa RT non può essere remota:
   richiede modulo certificato o server RT dedicato.
5. **Lettore barcode HID** → gestire focus, debounce e validazione EAN; in caso
   di client Kivy refactorizzato, gestire l'input come tastiera.

---

## 9. Stack tecnologico di dettaglio (nuove funzionalità)

- **Generazione PDF DDT**: ReportLab (già usato) — `services/printing/ddt.py`.
- **Etichette DYMO**: ReportLab `canvas` su formato `54x101mm` oppure ZPL.
- **Scontrini termici**: `python-escpos` (USB/network) o raw `win32print`.
- **Local Print Agent**: Python leggero (FastAPI/WebSocket client + win32print)
  oppure client Kivy refactorizzato (strada "Opzione B" del piano generale).
- **Barcode**: zero driver (HID keyboard-wedge); validazione EAN-13.
- **Coda stampa**: DB `print_jobs` + polling/WebSocket; per volumi alti
  valutare Redis/Celery come worker.

---

## 10. Riferimenti ai file esistenti

| Funzione | File sorgente attuale | Da migrare/riusare |
|---|---|---|
| PDF lotto (base per DDT) | `Laboratorio/lotti_vendita.py` → `crea_pdf()` | Riusare ReportLab |
| Etichetta DYMO | `Laboratorio/lotti_vendita_cucina.py` → `stp_etichetta()` | Riusare + adattare |
| Invio bilancia (WinSwGx) | `Laboratorio/lotti_vendita*.py` → `crea_bz00varp/vate()` | Spostare nell'Agent |
| Inserimento EAN | `Laboratorio/ingredienti.py` | Riusare logica lookup |
| Selezione stampante | `Laboratorio/anagrafica_impostazioni.py` | Da spostare su dispositivo locale |
| Config stampante | `config.ini` → `[Stampante]` | Da esternalizzare |
| Intestazione DDT | `GestLab2/ingresso_merce` (campo numero documento) | Riusare |

---

*Documento di supporto a `SAAS_MIGRATION_PLAN.md`. Per la roadmap generale,
sicurezza e GDPR fare riferimento al piano principale.*
