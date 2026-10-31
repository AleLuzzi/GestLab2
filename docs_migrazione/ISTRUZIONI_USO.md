# Istruzioni d'uso — GestLab SaaS

La console web SaaS è l'unica interfaccia applicativa supportata per lo
sviluppo e l'uso di GestLab. Si accede da browser, inclusi i browser dei
tablet supportati; non è richiesta l'installazione di Kivy o di un'app
desktop. L'interfaccia richiede una connessione al server e non offre modalità
offline.

## 1. Requisiti

- Python 3.10+ per sviluppo e server.
- MySQL/MariaDB raggiungibile, configurato tramite variabili d'ambiente o
  `.env`; `config.ini` resta un fallback locale legacy.
- Dipendenze backend:

```bash
python -m pip install -r requirements-web.txt
```

In un ambiente virtuale (consigliato):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-web.txt
```

## 2. Avvio locale

Dalla cartella principale del repository:

```bash
python -m uvicorn saas.main:app --reload
```

Il server usa `http://localhost:8000/`.

| Risorsa | URL |
|---|---|
| Console web | http://localhost:8000/ |
| Documentazione API | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

## 3. Preparare il database

Per una nuova installazione, configura un database MySQL/MariaDB vuoto e
dedicato, poi esegui:

```bash
python -m saas.bootstrap
```

Il bootstrap crea lo schema business e SaaS e un tenant/admin iniziale. Per
istruzioni su credenziali iniziali e variabili d'ambiente consulta
`core/env.py` e le guide di deploy. Non usare credenziali di sviluppo in
produzione.

**Non puntare i test a un database con dati da conservare.** Il test
`tests/test_saas_e2e.py` ricrea alcune tabelle SaaS; va eseguito soltanto su
un database usa-e-getta e isolato.

## 4. Funzioni disponibili

La console web espone, in base al ruolo:

- ingresso merce;
- consultazione dei lotti aperti e tracciabilità;
- consultazione del menu;
- gestione di dipendenti, reparti, merceologie e fornitori;
- stampa di DDT, scontrini e etichette tramite la coda di stampa;
- lookup barcode EAN;
- amministrazione di utenti e dispositivi di stampa.

La composizione del menu, la chiusura/vendita lotti e il CRUD legacy dei
tagli non fanno parte del perimetro SaaS attuale e non sono funzioni supportate
da queste istruzioni.

## 5. Barcode e stampa locale

Uno scanner USB/HID che si comporta come una tastiera può inserire il codice
nel campo barcode della console. L'effettivo comportamento va verificato con
lo scanner e il browser scelti, in particolare focus e tastiera virtuale su
tablet.

Per stampare automaticamente su hardware locale:

1. un admin registra un dispositivo dalla console e genera il token;
2. sul PC collegato alla stampante si installano le dipendenze backend;
3. si avvia il Local Print Agent:

```bash
python -m saas.print_agent --token <TOKEN_DISPOSITIVO> --interval 5
```

L'agent contatta il backend e invia i job alla stampante configurata sul
dispositivo locale. Non è un client desktop Kivy e non sostituisce la console
web. Per l'installazione e la configurazione dettagliate, consultare
`SAAS_PRINTING_BARCODE_PLAN.md`.

## 6. Eseguire i test

Test unitari:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Test end-to-end SaaS: usare esclusivamente un database temporaneo dedicato,
poiché il test elimina e ricrea tabelle SaaS:

```bash
python tests/test_saas_e2e.py
```

Non eseguire il comando e2e finché la configurazione DB attiva non è stata
verificata come isolata e usa-e-getta.

## 7. Configurazione

- Le variabili d'ambiente prevalgono su `.env`; `config.ini` è un fallback
  locale legacy (`core/env.py`).
- Non committare file `.env`, configurazioni con credenziali o token.
- Per produzione usare segreti dedicati all'ambiente e HTTPS.

## 8. Limiti e collaudo tablet

La rimozione della UI desktop non equivale a certificare ogni browser o
dispositivo. Prima di dichiarare supportato un tablet, verificare su quel
modello/browser: login, navigazione, moduli e tastiera virtuale, uso in
orientamento previsto, barcode HID, messaggi in caso di rete non disponibile
e flusso di stampa tramite Local Print Agent.
