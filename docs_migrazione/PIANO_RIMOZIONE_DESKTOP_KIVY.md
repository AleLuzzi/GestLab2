# Piano per la rimozione sicura della UI desktop e di Kivy

## Obiettivo e decisione

Concentrare lo sviluppo del prodotto sulla console web SaaS (`web/` + API
FastAPI in `saas/`), rimuovendo in modo verificato la UI desktop Kivy/KivyMD e
le relative dipendenze. Non rimuovere il core applicativo, i servizi, i
repository, le API o il Local Print Agent: sono componenti riutilizzati dalla
SaaS o necessari per le periferiche locali.

Non risultano installazioni desktop da mantenere. Questo riduce il rischio di
compatibilità con utenti esistenti, ma non sostituisce la verifica dei flussi,
dei test e delle dipendenze prima di cancellare file.

## Stato rilevato nel repository

- L'avvio Kivy è in `main.py` e la UI principale è definita in `main.kv`.
- Le schermate Kivy/KivyMD si trovano sotto `desktop/`; `desktop/nuovo_lotto/`
  contiene anche una UI Tkinter.
- `recycleviews.py` è un helper della UI desktop.
- `requirements.txt` include `kivy` e `kivymd`; `requirements-web.txt` contiene
  già le dipendenze del backend senza Kivy.
- Il deploy Lightsail installa `requirements-web.txt` tramite
  `deploy/setup-server.sh` e `deploy/update-server.sh`.
- La guida `docs_migrazione/ISTRUZIONI_USO.md` documenta ancora l'avvio desktop.
- Il repository contiene una directory `kivymd/` e metadati
  `kivymd-2.0.1.dev0.dist-info/`. Prima di rimuoverli bisogna verificare se
  sono sorgenti tracciati, una copia vendorizzata necessaria o residui locali.
- Il print agent SaaS (`saas/print_agent.py`) gestisce la stampa locale senza
  dipendere dalla UI Kivy: non va eliminato insieme alla UI.
- I test `test_nuovo_lotto.py` e `test_ingresso_merce.py` verificano servizi,
  repository, validazione e API, non sono da considerare test desktop solo per
  il nome.

## Regole di sicurezza per la migrazione

1. **Non cancellare il core** (`core/`, `core/services/`,
   `core/repositories/`) né la UI web/API SaaS.
2. **Non rimuovere il print agent** o le librerie di stampa/barcode: verificare
   che restino utilizzabili dopo aver tolto Kivy.
3. **Non eliminare test sulla logica condivisa**. Spostare o rinominare test
   solo se la loro posizione o il nome sono fuorvianti, preservando la
   copertura.
4. **Non rimuovere `config.ini` o le configurazioni DB** in questo intervento:
   il core e l'agent possono ancora leggerle. La rimozione dei segreti è un
   lavoro separato e va gestita con rotazione delle credenziali.
5. Prima di ogni cancellazione, controllare lo stato Git e l'elenco dei file
   tracciati. Non usare cancellazioni ricorsive non revisionate; lavorare per
   gruppi piccoli e verificare ogni diff.
6. Eseguire i test di integrazione solo su un database di test: alcuni test
   e2e/bootstrap possono creare o modificare tabelle e dati.

## Fase 0 — Baseline e inventario

### Attività

- Creare un branch dedicato e registrare lo stato iniziale (`git status`,
  commit di partenza e diff vuoto o documentato).
- Eseguire l'intera suite Python esistente su un ambiente/database di test e
  salvare gli esiti come baseline.
- Cercare import, riferimenti e comandi di avvio di `kivy`, `kivymd`,
  `desktop`, `main.kv`, `recycleviews.py` e Buildozer in codice, workflow,
  script, documenti e configurazioni.
- Elencare i file effettivamente tracciati sotto `kivymd/`,
  `kivymd-2.0.1.dev0.dist-info/` e verificare l'origine degli import
  nell'ambiente Python. Verificare anche lo stato Git di `buildozer.spec`:
  benché compaia in `.gitignore`, risulta tracciato nel repository.
- Mappare ogni funzionalità desktop su un flusso SaaS equivalente oppure
  segnalarla come mancante. Includere almeno ingresso merce, nuovo lotto,
  chiusura lotto, vendita, menu, anagrafiche, barcode, DDT/etichette/scontrini
  e stampa.
- Provare i flussi prioritari su tablet reali o emulatori rappresentativi,
  includendo dimensioni e orientamenti effettivamente usati.

### Criteri di uscita

- Esiste una lista affidabile dei soli file desktop e delle dipendenze Kivy.
- Ogni funzione desktop è classificata come coperta dalla SaaS, non più
  necessaria, oppure bloccante da implementare prima della rimozione.
- La baseline dei test e le eventuali anomalie preesistenti sono documentate.

**Gate:** se un flusso operativo necessario non è coperto o il test di
baseline non è riproducibile, non procedere alle cancellazioni.

### Esito dell'esecuzione — 2026-10-31

#### Repository e ambiente

- Branch creato: `chore/rimozione-desktop-kivy-fase0`.
- Commit di partenza: `3c9cba3` (branch iniziale `master`).
- All'avvio del lavoro l'unico elemento non committato era questo piano,
  creato nella richiesta precedente; non sono state modificate altre
  modifiche preesistenti.
- Ambiente rilevato: Python 3.10.11. Le chiavi DB locali sono configurate, ma
  il database non è identificabile come ambiente di test; i valori non sono
  stati stampati né inclusi in questo documento.

#### Inventario verificato

- Sono tracciati gli entry point `main.py`, `main.kv` e `recycleviews.py`,
  oltre a 31 file sotto `desktop/`.
- `buildozer.spec` è tracciato nel repository.
- `kivymd/` contiene 205 file tracciati e
  `kivymd-2.0.1.dev0.dist-info/` ne contiene 9. L'import runtime risolve la
  copia KivyMD nel repository (`2.0.1.dev0`), mentre `requirements.txt`
  dichiara `kivymd==2.0.0`; la provenienza e la necessità della copia locale
  vanno chiarite prima di rimuoverla.
- Kivy 2.3.1 è installato nell'interprete locale. Nessun riferimento runtime
  a Kivy/KivyMD o alla UI desktop è emerso nelle directory `core/`, `saas/`,
  `web/`, `tests/` e `deploy/`. I riferimenti residui rilevati sono nelle
  guide e nei documenti di migrazione.
- Il Local Print Agent e i servizi di stampa appartengono al percorso SaaS e
  non risultano dipendere dai widget desktop.

#### Mappatura funzionale preliminare

| Flusso desktop | Evidenza SaaS | Esito fase 0 |
|---|---|---|
| Ingresso merce | Schermata web e `POST /api/v1/ingresso-merce` | Presente; collaudo tablet e test end-to-end ancora necessari |
| Nuovo lotto | La UI desktop riusa il flusso di ingresso; API SaaS di ingresso presente | Possibile corrispondenza, non ancora provata come flusso completo |
| Chiusura lotto | Esiste logica core, ma non è emerso un endpoint/UI SaaS di chiusura | Esclusa dal perimetro SaaS scelto dall'utente |
| Vendita lotti | SaaS espone lotti aperti e tracciabilità; non è emerso un flusso web di vendita/chiusura | Esclusa dal perimetro SaaS scelto dall'utente |
| Nuovo menu | UI web e `GET /api/v1/menu`; non è emerso un endpoint di salvataggio del menu | Consultazione inclusa; composizione esclusa dal perimetro SaaS scelto |
| Dipendenti, reparti, merceologie, fornitori | Schermate web e API CRUD | Copertura candidata; collaudo funzionale ancora necessario |
| Tagli | Desktop usa tagli; SaaS adotta articoli e non espone CRUD tagli | CRUD tagli escluso dal perimetro SaaS scelto dall'utente |
| Barcode | Campo web e lookup `GET /api/v1/prodotti/ean/{codice}` | Implementato lato software; test con scanner e tablet pendente |
| DDT, scontrino, etichetta | API di generazione e coda/Local Print Agent | Architettura presente; prova con hardware reale pendente |
| Impostazioni desktop | Il pulsante desktop era un placeholder senza azione | Non costituisce una funzione da migrare, salvo nuovi requisiti |

La mappatura è basata sui file e sugli endpoint presenti, non certifica che i
flussi siano equivalenti sul piano operativo.

#### Baseline test

- Comando eseguito: `python -m unittest discover -s tests -p "test_*.py" -v`.
- Esito: 30 test individuati; 27 passati e 3 errori, tutti in
  `tests/test_nuovo_lotto.py`. I test si aspettano
  `core.repositories.lotti.salva_lotti_vendita`, che non è presente nel
  repository corrente. È un test legacy non allineato al codice, non una
  dipendenza runtime desktop della SaaS; resta una anomalia nota e non è stata
  cancellata né mascherata.
- `tests/test_saas_e2e.py` ricrea tabelle SaaS e non può essere eseguito sul DB
  configurato normalmente. È stato corretto il setup del test per sospendere i
  controlli FK durante il reset; il test legacy dei tagli è stato tolto
  dall'e2e SaaS perché il relativo CRUD è fuori dal perimetro scelto e la
  tabella non è nello schema SaaS corrente.
- L'e2e è stato eseguito su un database usa-e-getta con nome casuale, creato e
  rimosso nello stesso run. Esito: 25 controlli passati, 0 falliti; schema
  creato con 29 statement. Il DB configurato normalmente non è stato scritto.
- Durante l'e2e PyJWT ha segnalato che la chiave HMAC configurata è più corta
  dei 32 byte raccomandati; l'avviso non ha fatto fallire il test ed è una
  questione separata dalla rimozione desktop.

#### Gate e decisione

La Fase 0 è **eseguita per inventario e baseline locale**. L'utente ha scelto
di escludere dal prodotto SaaS i flussi mancanti elencati sopra; non vanno
trattati come funzioni da implementare prima della dismissione desktop. Il DB
e2e temporaneo è stato isolato e la verifica automatica SaaS è passata.

Il test legacy `test_nuovo_lotto.py` resta un'anomalia nota: i suoi tre errori
sono stati riprodotti e risultano indipendenti dalla UI Kivy. Viene mantenuto
per non eliminare copertura di logica condivisa; il gate di rimozione è stato
esplicitamente derogato dall'utente, non considerato superato dai test.

## Fase 1 — Rendere la SaaS il percorso ufficiale

### Attività

- [x] Definire `saas.main:app` e la console web come unico client applicativo
  supportato per il prodotto.
- [x] Aggiornare `ISTRUZIONI_USO.md` con installazione backend, avvio SaaS e
  uso del Local Print Agent, rimuovendo le istruzioni desktop.
- [x] Aggiornare i piani SaaS e le guide di deploy per indicare Kivy come
  legacy, non richiesto per il server né previsto come alternativa per l'agent.
- [ ] Collaudare l'interfaccia tablet scelta: input touch, tastiera virtuale,
  form, navigazione, login e gestione degli errori di rete. **Deroga utente:**
  rimozione autorizzata prima del collaudo; il target iPad/Safari resta da
  verificare.
- [ ] Verificare barcode HID e stampa con la console web e il Local Print
  Agent. **Deroga utente:** scanner e stampanti non disponibili; prova hardware
  rinviata.
- [x] Documentare come fuori perimetro la modalità offline e i flussi desktop
  che l'utente ha escluso.

### Criteri di uscita

- Le istruzioni per un nuovo sviluppatore non richiedono Kivy per avviare e
  verificare il prodotto.
- La copertura dei flussi prioritari e dei dispositivi locali è verificata.
- La UI desktop non è più necessaria per sviluppo, test o operatività prevista.

### Stato corrente

Documentazione e direzione SaaS aggiornate. L'utente ha autorizzato di
procedere rinviando il collaudo tablet/periferiche: target iPad con Safari,
scanner e stampanti non disponibili. La Fase 1 è chiusa **per deroga esplicita**,
non perché il collaudo manuale sia stato superato.

## Fase 2 — Separare e semplificare le dipendenze

### Attività

- [x] Mantenere `requirements.txt` come manifest installabile per SaaS/agent
  e `requirements-web.txt` per il deploy; entrambi sono senza dipendenze UI.
- [x] Rimuovere Kivy/KivyMD dal manifest comune e aggiornare le guide.
- [x] Conservare Pillow e le dipendenze di stampa/barcode.
- [x] Installare e validare in un ambiente virtuale pulito senza Kivy.

### Criteri di uscita

- Un'installazione pulita senza Kivy avvia `saas.main:app`, il bootstrap
  previsto e il Local Print Agent.
- Nessun import runtime della parte SaaS richiede `kivy` o `kivymd`.
- I manifest e i comandi documentati concordano.

### Esito

`requirements.txt` e `requirements-web.txt` non includono più Kivy/KivyMD.
Il deploy Lightsail richiede esplicitamente `requirements-web.txt` e non ha più
il fallback che filtrava Kivy da `requirements.txt`.

## Fase 3 — Rimozione del codice UI desktop

Procedere con una modifica Git revisionabile, cancellando esclusivamente i
componenti UI identificati e non più referenziati:

- `main.py` e `main.kv`;
- `desktop/`, incluse le schermate Kivy e l'eventuale schermata Tkinter
  `desktop/nuovo_lotto/`, dopo la verifica delle dipendenze condivise;
- `recycleviews.py`;
- `kivymd/` e `kivymd-2.0.1.dev0.dist-info/`, copia vendorizzata non usata dal
  runtime SaaS e priva di riferimenti attivi una volta rimossa la UI;
- `buildozer.spec`, perché non è più previsto un pacchetto Android nativo;
- eventuali asset o file KV usati esclusivamente dalla UI desktop, ma solo
  dopo aver verificato che non siano usati da web, report, stampa o test.

Non includere nella cancellazione:

- `core/`, `saas/`, `web/`, `deploy/` e i test SaaS/core;
- `saas/print_agent.py`, `core/services/printing.py` e le dipendenze necessarie
  alla stampa;
- dati, schemi DB, file di configurazione o segreti come effetto collaterale.

### Verifica della sorgente Kivy vendorizzata

La presenza di `kivymd/` e dei relativi metadati va trattata separatamente
dalla cancellazione di `desktop/`:

1. controllare con Git quali file sono tracciati e da quale versione o
   distribuzione provengono;
2. verificare se l'app importava la copia locale o il pacchetto installato;
3. verificare licenze, file di packaging e riferimenti prima della rimozione;
4. rimuovere la copia vendorizzata e i metadati solo se nessun percorso
   supportato li usa e non sono necessari ad altri strumenti.

`buildozer.spec` era tracciato nonostante la sua voce in `.gitignore`; è stato
rimosso insieme alla regola di ignore, non all'ambiente locale.

### Esito

Rimossi gli entry point Kivy, `desktop/` (31 file), `recycleviews.py`, la copia
KivyMD vendorizzata (205 file), i metadati (9 file) e `buildozer.spec`. Non
sono stati rimossi `core/`, `saas/`, `web/`, il Local Print Agent, i servizi di
stampa/barcode o i test di logica condivisa. Nessun asset condiviso è stato
cancellato.

### Criteri di uscita

- La diff contiene solo rimozione desktop e riferimenti strettamente
  dipendenti, senza variazioni di schema o dati.
- Non esistono import o entry point attivi verso la UI rimossa.
- Le funzioni condivise e il print agent restano presenti.

## Fase 4 — Aggiornare documentazione e automazioni

### Attività

- [x] Rimuovere istruzioni di avvio desktop dalle guide attive.
- [x] Aggiornare documentazione architetturale, test e Local Print Agent.
- [x] Aggiornare il setup Lightsail per installare esclusivamente il manifest
  SaaS e non applicare workaround Kivy.
- [x] Cercare i riferimenti runtime residui: non restano dipendenze o import
  desktop; i riferimenti storici sono conservati nella documentazione.
- Se si decide di cancellare un documento ormai obsoleto, aggiornare i link
  che lo citano e preservare le informazioni ancora valide nel documento
  attivo.

## Fase 5 — Verifica funzionale e regressione

### Controlli automatici

Eseguire dall'ambiente pulito e, per i test con DB, su un database isolato:

1. tutti i test unitari esistenti (`test_dipendenti.py`,
   `test_ingresso_merce.py`, `test_nuovo_lotto.py`,
   `test_tracciabilita.py`);
2. bootstrap e test SaaS (`test_bootstrap.py`, `test_saas_e2e.py`) secondo le
   loro modalità documentate e senza puntare a dati reali;
3. avvio dell'app FastAPI e verifica di `/health`, `/`, `/docs`, login e asset
   statici;
4. import/avvio del print agent e test controllato dei formati di stampa,
   senza inviare job a stampanti di produzione;
5. ricerca finale di import o riferimenti runtime a `kivy`, `kivymd`,
   `desktop`, `main.kv`, `recycleviews` e Buildozer;
6. controllo del diff, dei file cancellati e dell'installazione da manifest.

### Controlli manuali

- Login, ruoli e navigazione sui browser tablet supportati.
- Inserimento e conferma di un ingresso merce completo, con errori di
  validazione.
- Consultazione e gestione dei lotti, tracciabilità e menu secondo i flussi
  effettivamente esposti dalla SaaS.
- Barcode HID con tastiera virtuale e scanner fisico.
- DDT, etichetta e scontrino tramite agent, inclusi errore o indisponibilità
  della stampante.
- Comportamento in rete lenta/interrotta e messaggi presentati all'operatore.

I test esistenti potrebbero non coprire tutte queste interazioni browser e
hardware: registrare i controlli manuali o automatizzarli dove il progetto ha
già un harness adeguato.

### Criteri di uscita

- Tutti i test di baseline passano oppure ogni differenza è spiegata e
  approvata; nessun fallimento viene nascosto come effetto della rimozione.
- La SaaS funziona in ambiente pulito senza dipendenze Kivy.
- I flussi operativi e stampa/barcode passano sui dispositivi target.
- La ricerca finale non trova dipendenze runtime desktop residue.

### Esito delle verifiche eseguite

- Installazione di `requirements-web.txt` in un ambiente virtuale temporaneo
  pulito completata; `kivy` e `kivymd` non risultano installati o importabili.
- Import di `saas.main` e `saas.print_agent` riuscito. Con Uvicorn locale hanno
  risposto HTTP 200 `/`, `/health`, `/docs`, `/static/app.css` e
  `/static/js/app.js`.
- L'utente ha inoltre provato localmente l'avvio del server Uvicorn e riferisce
  che l'applicazione funziona regolarmente. Questo conferma il collaudo locale
  della web app, ma non sostituisce le prove su iPad/Safari e sulle periferiche.
- Bootstrap dello schema ed e2e eseguiti su un database MySQL temporaneo
  isolato: **25 controlli superati**, database poi eliminato.
- Suite unit eseguita escludendo il test legacy rotto: **27 test superati**.
  `test_nuovo_lotto.py` è stato verificato separatamente e mantiene i 3 errori
  già presenti nella baseline perché `core.repositories.lotti` non espone
  `salva_lotti_vendita`; non sono stati introdotti dalla rimozione desktop.
- `TestClient` non è stato usato perché l'ambiente pulito non include
  `httpx2`; lo smoke test è stato effettuato via richieste HTTP reali a Uvicorn,
  senza aggiungere dipendenze di test ai manifest runtime.
- Il controllo automatico di whitespace non ha rilevato errori. La ricerca
  runtime non ha trovato riferimenti Kivy/KivyMD/Buildozer; i riferimenti alla
  UI precedente restano solo in documentazione storica.

La Fase 5 è **parzialmente verificata**: i controlli automatizzati disponibili
sono stati eseguiti, ma il test legacy fallisce come nella baseline e restano
da svolgere i controlli manuali su iPad/Safari, scanner e stampanti, rinviati
per esplicita decisione dell'utente. La Fase 6 non è stata eseguita: nessun
deploy, merge o commit è stato effettuato.

## Fase 6 — Rilascio e rollback

1. Revisionare il branch e il diff completo prima del merge.
2. Eseguire il deploy in test/staging usando il manifest aggiornato e verificare
   bootstrap, health check, login, flussi operativi e agent.
3. Fare backup del DB prima di un rilascio, pur non essendo previste migrazioni
   schema/dati in questa rimozione.
4. Promuovere il rilascio solo dopo il collaudo; osservare errori API e log
   dell'agent dopo l'aggiornamento.
5. In caso di regressione, ripristinare il commit applicativo precedente e il
   relativo manifest, senza cancellare o ricreare il database.

Se durante il collaudo emerge un caso d'uso realmente offline o una periferica
non gestibile dalla web app/agent, sospendere la cancellazione dei soli
componenti necessari e rivalutare un client sottile dedicato. Non mantenere
automaticamente l'intera UI desktop come risposta: delimitare il requisito e
valutare un agente locale indipendente dalla UI.

## Sequenza consigliata dei cambiamenti

Per facilitare la revisione, preferire PR/commit separati:

1. documentazione SaaS e inventario dei flussi;
2. semplificazione manifest e verifica ambiente pulito;
3. rimozione UI e file Kivy non ambigui;
4. rimozione eventuale copia Kivy vendorizzata/Buildozer, solo dopo verifica;
5. test finale, pulizia dei riferimenti e aggiornamento documentazione.

Ogni passaggio deve restare reversibile tramite Git e superare i propri
criteri di uscita prima di iniziare il successivo.
