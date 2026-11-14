# Checklist per completare GestLab vendibile

Checklist operativa basata su [PIANO_PRODOTTO_VENDIBILE.md](PIANO_PRODOTTO_VENDIBILE.md), aggiornato il 2026-11-07.

## Come usarla

- Seguire le fasi nell'ordine indicato: il debito tecnico e la Fase A precedono le vendite.
- Spuntare una voce solo dopo aver verificato il criterio indicato; registrare eventuali decisioni di prodotto nel piano.
- Le voci marcate `[rinviato]` sono escluse dalle prossime elaborazioni della checklist e non vanno riproposte finché non viene richiesto esplicitamente di riaprirle.
- Le voci già spuntate risultano implementate nel piano aggiornato, ma vanno comunque incluse nei controlli di regressione.
- La Fase C va completata prima di rendere ripetibile il servizio SaaS; alcuni adempimenti legali richiedono conferma del professionista competente.
- HACCP lite, billing self-service, 2FA, FE e RT non sono requisiti per il primo prodotto vendibile.

## 0. Debito tecnico bloccante

### Già implementato (da mantenere e verificare)

- [x] Usare l'ingresso tracciato come flusso supportato; l'endpoint legacy restituisce `410 Gone` ed è escluso da OpenAPI.
- [x] Usare `articoli` come catalogo unico per anagrafica, EAN e prezzo; mantenere `articoli_bilancia` come configurazione specifica Bizerba.
- [x] Rifiutare il secret JWT predefinito in ambiente production.
- [x] Ammettere il movimento `VENDITA` nello schema nuovo e predisporre la migrazione per i database esistenti.
- [x] Rendere disponibili in schema/API i metadati lotto supportati e predisporre la migrazione relativa.

### Da completare

- [x] Definire e automatizzare l'archiviazione non distruttiva di `ingresso_merce`: il bootstrap la rinomina in `ingresso_merce_legacy_archive` senza trasformare dati con corrispondenze non verificate.
- [x] Eseguire il bootstrap sui database esistenti; verificare che la tabella legacy sia assente e confrontare il numero di righe archiviate con un backup. Verificato il 2026-11-07 sul database `data`: backup `../backups/gestlab_backup_20261107_161449.sql`, bootstrap completato senza errori; `ingresso_merce` e `ingresso_merce_legacy_archive` assenti (0 righe da archiviare e confrontare).
- [x] Rendere coerente lo schema consolidato per i database nuovi: chiavi primarie, quantità `DECIMAL(12,3)`, `tenant_id NOT NULL` con FK, charset `utf8mb4` e FK mancanti; coperto da `tests/test_schema_consolidation.py`.
- [x] Definire e documentare l'ordine unico delle migrazioni per database nuovi ed esistenti; il bootstrap registra il baseline dei database nuovi, applica o riconosce le migrazioni esistenti e interrompe l'esecuzione sugli errori. Ordine e verifica automatica in `saas/SCHEMA_CONSOLIDATION.md` e `tests/test_bootstrap_migrations.py`.
- [x] Verificare che un database nuovo e uno migrato espongano le stesse colonne richieste dal codice e che nessuna tabella usata accetti insert senza PK. Il bootstrap confronta le tabelle con `init_database.sql` dopo creazione e migrazioni e si interrompe indicando colonne o PK mancanti; coperto da test. Verificato il 2026-11-07 sul database migrato `data`, inclusa la normalizzazione di `progressivi`.
- [x] Completare il modello unico dei lotti: ingresso e lavorazione registrano i movimenti nella stessa transazione; la chiusura può solo disattivare un lotto già esaurito e non azzera la giacenza. Testata anche la rollback se fallisce la registrazione del movimento.
- [x] Configurare TLS verso MySQL/RDS in produzione: le connessioni remote richiedono `DB_SSL_CA` in produzione e verificano certificato e identità del server; il database locale su loopback resta supportato. Coperto da `tests/test_db.py`.
- [x] Aggiungere un pool di connessioni e verificare il riuso sotto carico: pool condiviso per processo, configurabile con `DB_POOL_SIZE` (default 10, massimo 32); test di riuso concorrente in `tests/test_db.py`.
- [x] Rimuovere il fallback a `config.ini` per le credenziali di produzione; usare solo variabili d'ambiente o Secret Manager. `core.env.get_secret` e il token del Print Agent ignorano `config.ini` con `GESTLAB_ENV=production`; coperto da `tests/test_env.py`.

## 1. Fase A — Laboratorio vendibile

### Metadati, scadenze e FEFO

- [x] Aggiornare il wizard d'ingresso per raccogliere lotto fornitore, origine e scadenza o TMC; raccogliere la temperatura d'ingresso quando applicabile. Campi facoltativi mostrati nel riepilogo e inviati per ciascuna riga; temperatura limitata a -100..100 °C con due decimali.
- [x] Definire e implementare la distinzione tra scadenza e TMC e le regole operative: date alternative, origine e data dichiarate per ogni lotto prodotto, scadenze trascorse bloccate e TMC trascorso soggetto a conferma. Decisione e copertura in `PIANO_PRODOTTO_VENDIBILE.md` § 5.1.
- [x] Decidere se e come registrare note di lotto (per esempio “bio” o razza) e, se incluse, aggiungerle al flusso. Scelta: nota descrittiva facoltativa fino a 500 caratteri, raccolta in ingresso, salvata sul lotto e visibile nel riepilogo e dettaglio; non è una certificazione e non si propaga automaticamente ai lotti `V`. Coperta da `tests/test_tracciabilita.py` e dalla migrazione `20261107_note_lotto.sql`.
- [x] Mostrare nel dettaglio lotto i metadati, il fornitore e il DDT d'ingresso; la scheda mostra lotto fornitore, origine, scadenza o TMC e temperatura, oltre a data, numero DDT e fornitore d'ingresso.
- [x] Definire come i lotti `V` dichiarano origine e data (scadenza o TMC): inserimento operatore per ogni output, senza copia o aggregazione automatica dagli input. Una durata di ricetta approvata dall'OSA potrà solo proporre una data da confermare.
- [x] Applicare la selezione FEFO predefinita in lavorazione: il lotto con la data applicabile più vicina è preselezionato, i lotti senza data sono in coda, le scadenze trascorse non sono selezionabili e il TMC trascorso richiede conferma esplicita.
- [x] Applicare la selezione FEFO predefinita in vendita in Fase B; consentire la scelta di un altro lotto disponibile. La schermata Vendite usa `GET /api/v1/vendite/lotti-disponibili`, preseleziona il primo lotto FEFO dell'articolo scelto e permette di selezionare le alternative; la registrazione della vendita resta nel successivo flusso di Fase B.
- [x] Mostrare in dashboard lotti scaduti o in scadenza (entro 48 ore e da 3 a 7 giorni), giacenze a zero e job di stampa in errore; conteggi e liste sono filtrati per tenant dagli endpoint esistenti.
- [x] Verificare che i metadati e le regole siano coperti da test e funzionino anche sui database migrati: aggiunto `data_tmc` con migrazione additiva ordinata dal bootstrap, controllo di esclusività nello schema/API, test per ingresso, output `V`, FEFO, scadenza bloccante, conferma TMC e riconoscimento/applicazione della migrazione. Coperto da `tests/test_tracciabilita.py`, `tests/test_vendite.py`, `tests/test_schema_consolidation.py` e `tests/test_bootstrap_migrations.py`.

**Verifica di fase:** un operatore registra un ingresso con lotto fornitore, origine e scadenza, ritrova i dati insieme a fornitore e DDT e vede in dashboard i lotti in scadenza. I lotti prodotti dichiarano origine e scadenza.

### Genealogia ed export

- [x] Realizzare in UI la genealogia all'indietro: lotto `V` → lavorazione → lotti input → ingresso → fornitore. Dal dettaglio del lotto prodotto si aprono i lotti input e si torna al passaggio precedente; il dettaglio del lotto `A` mostra ingresso, DDT e fornitore.
- [x] Realizzare in UI la genealogia in avanti: lotto `A` → lavorazioni → lotti `V` (e, in Fase B, vendite); il dettaglio del lotto mostra le lavorazioni che lo hanno consumato e permette di aprire i lotti prodotti. Query e test sono tenant-scoped; i collegamenti alle vendite restano nel punto dedicato della Fase B.
- [x] Generare una scheda lotto PDF per controlli, presentandola come riepilogo e non come certificazione legale. Il dettaglio lotto permette di scaricare un PDF con metadati, genealogia degli input e DDT/fornitore d'origine; il documento dichiara che non è una certificazione legale.
- [x] Verificare con un caso reale che dalla UI e dal PDF si risalga dal preparato al DDT fornitore in meno di un minuto. Verificato l'8 novembre 2026 sul caso di test 2280V (Salsicce Fresche) → 1565A (Mezzena): dalla UI il DDT 666 e il fornitore AIA sono stati raggiunti in 0,94 secondi; la richiesta live della scheda PDF ha restituito HTTP 200 (`application/pdf`). Passa anche `tests/test_tracciabilita.py::test_scheda_lotto_pdf_includes_tenant_scoped_source_lot`, che verifica il passaggio del DDT alla genealogia PDF.

### Ricette, ingredienti ed etichette

- [x] Creare l'anagrafica ricette per tenant, collegando articolo prodotto, rese e scarti attesi. API tenant-scoped `GET/POST/PUT/DELETE /api/v1/ricette`; resa e scarto attesi sono quantità nell'unità di misura dell'articolo prodotto. Schema consolidato e migrazione `20261108_ricette.sql`; verificato da `tests/test_ricette.py` e `tests/test_schema_consolidation.py`.
- [x] Gestire righe ricetta con articoli input, quantità per kg di prodotto o percentuali e indicazione di obbligatorietà. API e schema persistono righe ordinate con articolo input attivo dello stesso tenant, quantità/percentuale validata e flag obbligatorio; migrazione `20261108_ricetta_ingredienti.sql`, coperta da `tests/test_ricette.py` e `tests/test_schema_consolidation.py`.
- [x] Strutturare ingredienti e allergeni nella ricetta; definire i giorni di vita e le istruzioni di conservazione/cottura. Ingredienti e quantità sono collegati agli articoli; allergeni scelti dall'elenco controllato dei 14 gruppi; giorni di vita e istruzioni di conservazione/cottura sono facoltativi e tenant-scoped. L'OSA definisce i valori: non sono certificazioni né impostano automaticamente la scadenza. Coperto da `tests/test_ricette.py`, `tests/test_schema_consolidation.py` e migrazione `20261108_ricetta_allergeni_durata.sql`.
- [x] Realizzare la UI tenant-scoped di gestione ricette: creazione e modifica di prodotto, resa/scarto, ingredienti con quantità o percentuale e obbligatorietà, allergeni, durata e istruzioni; consentire la disattivazione senza cancellare la ricetta. La sezione Ricette nella UI Tracciabilità crea e modifica tramite API tenant-scoped, consente la disattivazione senza cancellazione e mostra nella lavorazione solo le ricette attive; la registrazione ricontrolla tenant e stato attivo. Coperto da `tests/test_ricette.py` e `tests/test_tracciabilita.py`.
- [x] Guidare la lavorazione da ricetta: precompilare input e lotti FEFO, poi registrare i pesi reali confermati dall'operatore. Per un articolo prodotto in kg, la UI permette di scegliere la ricetta e la quantità prevista, calcola le stime da quantità per kg o percentuali, alloca sui lotti disponibili in ordine FEFO e propone il prodotto output; quantità e lotti restano modificabili, la disponibilità insufficiente è segnalata e gli ingredienti obbligatori e il prodotto ricetta sono richiesti. La registrazione richiede la conferma esplicita dei pesi reali, invalidata quando cambiano input o output; gli ingredienti facoltativi non usati possono essere rimossi.
- [x] Generare etichette dal lotto (o da articolo e lotto) con denominazione, ingredienti, allergeni evidenziati, lotto, scadenza, conservazione e dati OSA; includere peso/prezzo quando disponibili. La scheda Stampa seleziona un lotto e genera un PDF con denominazione, lotto, scadenza o TMC, origine e prezzo commerciale canonico dell'articolo; peso confezione, ingredienti, allergeni evidenziati e conservazione sono disponibili. Gli admin configurano ragione sociale, sede, laboratorio e P.IVA OSA del tenant; la migrazione è applicata dal bootstrap. Ingredienti e allergeni derivati dalla ricetta restano nel punto successivo.
- [x] Derivare ingredienti e allergeni dai dati della ricetta senza ricopiatura manuale; limitare eventuali override al ruolo admin. La lavorazione conserva la ricetta scelta tramite migrazione `20261108_lavorazioni_ricetta.sql`; il dettaglio del lotto espone ingredienti/allergeni della ricetta, la UI li carica automaticamente e solo l'admin può modificarli. Coperto da `tests/test_etichette.py`, `tests/test_tracciabilita.py` e `tests/test_bootstrap_migrations.py`.
- [rinviato] Completare il collaudo di stampa con coda `print_jobs`, Local Print Agent e stampante prevista (DYMO). La UI ora accoda l'etichetta risolta dal lotto e l'agent la invia alla DYMO configurata; il passaggio software è coperto da `tests/test_etichette.py` e `tests/test_print_agent.py`. Il collaudo fisico della stampante e della resa dell'etichetta è rimandato e non va riproposto nelle prossime elaborazioni della checklist, salvo richiesta esplicita di riaprirlo.
- [x] Verificare con una ricetta reale che una lavorazione guidata produca un'etichetta completa e coerente. Verificato il 14 novembre 2026 sul tenant GestLabProva con la ricetta attiva «Salsicce fresche» (ingrediente Pancia, allergeni sedano e solfiti, conservazione «conservare in frigo a 4 gradi», 4 giorni di vita). Ingresso DDT `COLLAUDO-RICETTA-20261114` (lotto 1567A, 0,100 kg) e lavorazione guidata 15, che ha prodotto il lotto 2284V (0,010 kg, origine Italia, scadenza dichiarata 2026-11-17 e non calcolata dai giorni di vita). `POST /api/v1/etichetta` ha restituito HTTP 200 `application/pdf` con denominazione, prezzo 10,90 €/kg, peso, lotto, scadenza, origine, ingredienti e allergeni della ricetta, conservazione e dati OSA. La fixture automatica resta in `tests/test_etichette.py::test_salsiccia_recipe_lot_generates_complete_operator_label`.

**Verifica di fase:** è possibile produrre un preparato, ad esempio salsicce fresche, partendo da una ricetta; l'etichetta riporta ingredienti, allergeni, lotto interno e scadenza tramite il Local Print Agent.

### Inventario

- [x] Realizzare la UI/API di rettifica per lotto, delta e motivo (inventario, calo, reso o errore). La scheda lotto consente ad admin e operatori di registrare delta positivi o negativi con motivo; l'API ricava il tenant dal JWT.
- [x] Aggiornare giacenza e movimento `RETTIFICA` in modo coerente e tracciabile; non consentire di correggere la giacenza modificando il lotto. Aggiornamento e movimento con motivo avvengono nella stessa transazione; migrazione additiva `20261108_motivo_rettifica_lotto.sql`.
- [x] Mostrare il confronto tra conteggio fisico per articolo e quantità teorica, sommando i lotti. La sezione Lotti mostra per ogni articolo la giacenza teorica aggregata tenant-scoped, consente di inserire il conteggio fisico e calcola lo scostamento senza modificare la giacenza; coperto da `tests/test_tracciabilita.py`.
- [x] Testare, tra gli altri casi, una rettifica di −0,250 kg su un lotto `V` e verificare giacenza e storico movimenti. Coperta da `tests/test_tracciabilita.py`, inclusi giacenza insufficiente e rollback.

### HACCP lite (opzionale, solo su richiesta del pilota)

- [ ] Confermare con il cliente che il registro semplificato delle temperature è necessario.
- [ ] Se approvato, registrare temperatura all'ingresso e in cella con un registro giornaliero semplice.
- [ ] Mantenere esplicito che la funzione non fornisce un manuale HACCP né firme o certificazioni ASL.

## 2. Fase B — Vendite interne

### Documento e scarico di magazzino

- [x] Definire l'aggregato persistente di vendita e le relative migrazioni. Lo schema consolidato e la migrazione `20261108_vendite.sql` introducono testata tenant-scoped (`numero` univoco per tenant, data, cliente opzionale e tipo `DDT`/`RICEVUTA`) e righe collegate a lotto e articolo, con quantità, unità, prezzo e IVA informativa; vincoli e riconoscimento del bootstrap sono coperti da `tests/test_schema_consolidation.py` e `tests/test_bootstrap_migrations.py`.
- [x] Registrare tenant, data, numero progressivo per tenant, cliente opzionale (o banco) e tipo documento `DDT`/`RICEVUTA`. `POST /api/v1/vendite` crea una testata tenant-scoped usando il tenant del JWT, valida un cliente attivo dello stesso tenant o accetta banco senza cliente e assegna il progressivo in modo serializzato; coperto da `tests/test_vendite.py`.
- [x] Registrare per ogni riga lotto, articolo, quantità, unità di misura, prezzo unitario e IVA a solo scopo informativo. `POST /api/v1/vendite/{vendita_id}/righe` salva righe tenant-scoped validate e collegate alla testata; quantità, prezzo e IVA sono persistiti senza scaricare la giacenza, che resta nel punto successivo. Coperto da `tests/test_vendite.py`.
- [x] Implementare lo scarico parziale, il movimento `VENDITA` e la chiusura del lotto a giacenza zero, in un'unica transazione. L'inserimento delle righe di vendita blocca i lotti tenant-scoped, scala la quantità, registra il movimento negativo `VENDITA` e disattiva il lotto esaurito nella stessa transazione; i test verificano scarico parziale, esaurimento e rollback in errore.
- [x] Rifiutare con HTTP 409 una vendita che eccede la giacenza disponibile; verificare concorrenza e rollback in caso di errore. L'endpoint traduce `GiacenzaInsufficiente` in HTTP 409; il repository blocca la testata e i lotti tenant-scoped con `SELECT ... FOR UPDATE`, aggrega le righe per lotto e applica scarico, righe e movimenti in un'unica transazione. `tests/test_vendite.py` verifica il lock sul lotto, il rifiuto delle quantità aggregate insufficienti, il rollback e la risposta 409.
- [x] Estendere il servizio vendite e il repository di tracciabilità senza usare il modello legacy. Gli endpoint di vendita passano da `saas/services/vendite.py` al repository tracciabile; il test del servizio verifica la delega e quelli API la propagazione degli errori del repository.
- [x] Collegare le vendite alla genealogia in avanti dei lotti. Il dettaglio tenant-scoped del lotto mostra i documenti collegati con progressivo, data, tipo, cliente o banco e quantità venduta; coperto da `tests/test_tracciabilita.py`.
- [x] Aggiungere test per scarico parziale, lotto esaurito, quantità insufficiente, numerazione e isolamento tenant. `tests/test_vendite.py` verifica scarico e movimento, esaurimento, rollback per giacenza insufficiente, numerazione tenant-scoped e rifiuto di vendite o lotti appartenenti a un altro tenant.

### Banco, listini e documenti

- [x] Realizzare una UI vendita adatta al tablet: ricerca articolo, lotto FEFO modificabile, quantità/peso, totale e stampa, senza passaggi tecnici. La schermata Vendite consente la ricerca e la scelta dell'articolo, preseleziona il lotto FEFO modificabile, valida quantità fino a 3 decimali, calcola il totale e registra in modo atomico scarichi e documento; la ricevuta non fiscale viene accodata al Local Print Agent. Coperta da `tests/test_vendite.py` e `tests/test_print_agent.py`.
- [x] Usare il prezzo commerciale canonico dell'articolo per vendita ed etichetta; non usare `articoli_bilancia.prezzo1` come fonte del prezzo commerciale. I lotti disponibili espongono `articoli.prezzo_unitario`, il server rifiuta prezzi non più coerenti o non configurati e l'etichetta continua a leggere lo stesso campo. Coperto da `tests/test_vendite.py` e `tests/test_etichette.py`.
- [rinviato] Decidere se il listino HORECA distinto dal banco serve al pilota; in assenza di necessità, rinviarlo a v1.1. Non va riproposto nelle prossime elaborazioni della checklist, salvo richiesta esplicita di riaprirlo.
- [x] Generare il DDT dal documento persistito, con mittente OSA, destinatario cliente, righe e lotto, numero progressivo e possibilità di ristampa dallo storico. La vendita permette di scegliere DDT e cliente; `GET /api/v1/vendite/{id}/ddt.pdf` compone il PDF dai dati tenant-scoped salvati e lo storico DDT consente di scaricarlo/ristamparlo. Coperto da `tests/test_vendite.py`.
- [x] Verificare che ristampare lo stesso DDT mantenga numero e righe e non generi un documento orfano. La ristampa rilegge la stessa vendita e non crea una nuova testata; un test verifica progressivo e righe invariati tra generazioni successive (`tests/test_vendite.py`).
- [x] Generare la ricevuta non fiscale dallo stesso documento di vendita tramite Local Print Agent. `POST /api/v1/vendite/{id}/ricevuta` legge testata e righe persistite, calcola totale e IVA e accoda un job `scontrino`; la ristampa riusa lo stesso documento e non crea una nuova vendita. La UI Vendite non compone più il payload dal carrello. Coperto da `tests/test_vendite.py` e `tests/test_print_agent.py`.
- [x] Inserire in modo visibile la dicitura: “Documento non fiscale — non sostituisce lo scontrino del registratore telematico”. La dicitura è in testata e a piè di pagina della ricevuta ESC/POS, su righe intere da 32 colonne, ed è ripetuta nella schermata Vendite e nello storico. Il test dell’agent verifica che compaia due volte, anche dopo il totale.
- [x] Mostrare nel menu/listino operativo solo articoli attivi con almeno un lotto disponibile, con possibilità di disattivare il filtro. `GET /api/v1/menu` elenca gli articoli attivi del tenant e, con `solo_disponibili=true` (default), solo quelli con almeno un lotto vendibile (attivo, giacenza positiva, non scaduto; il TMC trascorso resta incluso). `solo_disponibili=false` mostra anche gli articoli attivi senza giacenza. Il Listino e la schermata Vendite applicano il filtro e permettono di disattivarlo; gli articoli inattivi restano esclusi. Coperto da `tests/test_catalogo_articoli.py`.
- [x] Verificare il flusso completo: vendita a cliente anagrafico, scarico corretto dei lotti e stampa del DDT. Verificato il 14 novembre 2026 sul tenant GestLabProva: `POST /api/v1/vendite/complete` ha registrato il DDT n. 5 per il cliente ALTech_mod spa, scaricando 0,005 kg dal lotto 2284V (Salsicce Fresche, giacenza da 0,010 a 0,005 kg) con movimento `VENDITA` di −0,005 kg nella stessa transazione. `GET /api/v1/vendite/6/ddt.pdf` ha restituito HTTP 200 `application/pdf` con mittente OSA, destinatario, lotto e quantità; la ristampa ha lo stesso testo e non crea un altro documento. Una vendita da 1,000 kg sullo stesso lotto è rifiutata con HTTP 409 e lascia invariate giacenza e testate.

## 3. Fase C — SaaS operabile

### Autenticazione e isolamento tenant

- [ ] Implementare reset password via email e policy password.
- [ ] Aggiungere rate limit al login, rotazione dei refresh token e logout/revoca.
- [ ] Verificare la protezione dal secret JWT predefinito in produzione e mantenerla coperta da test.
- [ ] Registrare almeno le operazioni di cancellazione e rettifica in un audit log.
- [ ] Garantire che ogni query usi il `tenant_id` ricavato dal JWT e che non sia accettato dal body come autorità.
- [ ] Portare `tenant_id` a `NOT NULL` sulle tabelle interessate e completare i vincoli di integrità.
- [ ] Aggiungere test IDOR tra tenant per lotti, soggetti, vendite, job di stampa e dispositivi; le richieste cross-tenant non devono restituire dati.

### Onboarding, produzione e privacy

- [ ] Predisporre onboarding interno ripetibile: tenant, dati OSA, primo admin e catalogo vuoto o template macelleria.
- [ ] Allineare il processo a `CREAZIONE_NUOVO_TENANT.md`; verificare che un nuovo laboratorio sia pronto per login e ingresso senza SQL manuale e in meno di 30 minuti.
- [ ] Configurare HTTPS, database gestito con backup automatici e point-in-time recovery, Secret Manager e ambiente staging separato dalla produzione.
- [ ] Monitorare `/health` e aggiungere error tracking e logging operativo.
- [ ] Eseguire e documentare una prova di ripristino del backup.
- [ ] Documentare installazione, token e riavvio del Local Print Agent come servizio Windows; verificare che riparta al riavvio del PC di banco.
- [ ] Preparare informativa privacy, DPA con cliente e cloud provider e checklist legale da completare con il professionista competente.
- [ ] Implementare export dei dati tenant (JSON/CSV) eseguibile da admin.
- [ ] Verificare che l'eliminazione non rimuova fisicamente lotti e documenti e che il contratto escluda validità fiscale RT/FE e certificazioni legali di etichette/HACCP.
- [ ] Mantenere per i primi 1–2 piloti il contratto e il pagamento manuali; non bloccare il rilascio sul billing self-service.

### UX, documentazione e collaudo

- [ ] Correggere il lookup EAN affinché mostri il nome dell'articolo e non JSON grezzo.
- [ ] Verificare che gli errori API mostrati all'operatore siano comprensibili e in italiano.
- [ ] Collaudare su tablet reale viewport, tastiera virtuale e scanner HID per i flussi di laboratorio e banco.
- [ ] Chiudere o proteggere `/docs` in produzione.
- [ ] Scrivere un manuale utente per ingresso → lavorazione → etichetta → vendita, distinto dalle istruzioni per sviluppatori.
- [ ] Preparare video o sequenza di screenshot per il pilota.
- [ ] Aggiungere e superare test per vendite, scadenze e isolamento tenant.
- [ ] Eseguire i test end-to-end solo su database sacrificabili: `tests/test_saas_e2e.py` ricrea tabelle.
- [ ] Verificare che un nuovo operatore completi il flusso pilota seguendo il solo manuale.

## 4. Gate di prodotto vendibile

Non avviare il pilota pagante finché tutti i punti seguenti non sono verificati:

- [ ] Un mese di ingressi e lavorazioni è registrato senza fogli Excel di appoggio.
- [ ] Da un lotto preparato si risale al DDT fornitore in meno di un minuto, via UI e scheda PDF.
- [ ] L'etichetta del preparato riporta ingredienti, allergeni, lotto interno e scadenza ed è stampata tramite Local Print Agent.
- [ ] Una vendita a cliente anagrafico con DDT scarica i lotti e mantiene coerenti le giacenze con `movimenti_lotto`.
- [ ] La ricevuta riporta chiaramente che il documento è non fiscale.
- [ ] I test dimostrano che il tenant B non può leggere i dati del tenant A.
- [ ] Il backup è ripristinabile e i segreti di produzione non sono quelli predefiniti di sviluppo.
- [ ] Il contratto esclude RT, FatturaPA e certificazione legale di etichette/HACCP.
- [ ] Ingresso, lavorazione da ricetta, etichetta e vendita DDT sono stati collaudati sul tablet del pilota.

**Esito:** se manca anche un solo requisito del gate, il rilascio resta un pilota tecnico e non va presentato come prodotto pronto alla vendita.

## 5. Fuori perimetro v1

Non inserire questi elementi nel gate di rilascio v1, salvo nuova decisione di prodotto:

- Registratore telematico, corrispettivi fiscali, POS e pagamenti elettronici.
- Fatturazione elettronica, SDI e FatturaPA.
- Uso offline della console o client desktop Kivy/Tkinter.
- Software HACCP completo o dichiarazioni di conformità/certificazione.
- Billing self-service/Stripe.
- 2FA.
- Export Bizerba combinato, da pianificare separatamente se richiesto.
