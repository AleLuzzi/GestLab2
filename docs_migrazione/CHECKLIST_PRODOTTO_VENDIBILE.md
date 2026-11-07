# Checklist per completare GestLab vendibile

Checklist operativa basata su [PIANO_PRODOTTO_VENDIBILE.md](PIANO_PRODOTTO_VENDIBILE.md), aggiornato il 2026-11-07.

## Come usarla

- Seguire le fasi nell'ordine indicato: il debito tecnico e la Fase A precedono le vendite.
- Spuntare una voce solo dopo aver verificato il criterio indicato; registrare eventuali decisioni di prodotto nel piano.
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

- [x] Aggiornare il wizard d'ingresso per raccogliere lotto fornitore, origine e scadenza; raccogliere la temperatura d'ingresso quando applicabile. Campi facoltativi per gli articoli selezionati, mostrati nel riepilogo e inviati per ciascuna riga; temperatura limitata a -100..100 °C con due decimali.
- [x] Definire la distinzione tra scadenza e TMC, i campi da salvare e le regole da applicare agli articoli interessati. Decisione di prodotto e regole operative registrate in `PIANO_PRODOTTO_VENDIBILE.md` § 5.1; l'implementazione resta da realizzare e collaudare.
- [x] Decidere se e come registrare note di lotto (per esempio “bio” o razza) e, se incluse, aggiungerle al flusso. Scelta: nota descrittiva facoltativa fino a 500 caratteri, raccolta in ingresso, salvata sul lotto e visibile nel riepilogo e dettaglio; non è una certificazione e non si propaga automaticamente ai lotti `V`. Coperta da `tests/test_tracciabilita.py` e dalla migrazione `20261107_note_lotto.sql`.
- [x] Mostrare nel dettaglio lotto i metadati, il fornitore e il DDT d'ingresso; la scheda mostra lotto fornitore, origine, scadenza e temperatura, oltre a data, numero DDT e fornitore d'ingresso.
- [x] Definire come i lotti `V` ereditano o dichiarano origine e scadenza, anche in relazione alla ricetta e alla data di produzione. Decisione in `PIANO_PRODOTTO_VENDIBILE.md` § 5.1: origine dichiarata dall'operatore per ogni output, senza copia o aggregazione automatica; data riferita alla lavorazione, senza ereditarla dagli input. Una durata di ricetta approvata dall'OSA può solo proporre una data da confermare dall'operatore.
- [x] Applicare la selezione FEFO predefinita in lavorazione: il lotto con scadenza più vicina è preselezionato, i lotti senza scadenza sono in coda e quelli scaduti non sono selezionabili; l'operatore può scegliere un altro lotto disponibile.
- [ ] Applicare la selezione FEFO predefinita in vendita in Fase B; consentire la scelta di un altro lotto disponibile.
- [ ] Mostrare in dashboard lotti in scadenza (ad esempio entro 48 ore e 7 giorni), giacenze a zero e job di stampa in errore.
- [ ] Verificare che i metadati e le regole siano coperti da test e funzionino anche sui database migrati.

**Verifica di fase:** un operatore registra un ingresso con lotto fornitore, origine e scadenza, ritrova i dati insieme a fornitore e DDT e vede in dashboard i lotti in scadenza. I lotti prodotti dichiarano origine e scadenza.

### Genealogia ed export

- [ ] Realizzare in UI la genealogia all'indietro: lotto `V` → lavorazione → lotti input → ingresso → fornitore.
- [ ] Realizzare in UI la genealogia in avanti: lotto `A` → lavorazioni → lotti `V` (e, in Fase B, vendite).
- [ ] Generare una scheda lotto PDF per controlli, presentandola come riepilogo e non come certificazione legale.
- [ ] Verificare con un caso reale che dalla UI e dal PDF si risalga dal preparato al DDT fornitore in meno di un minuto.

### Ricette, ingredienti ed etichette

- [ ] Creare l'anagrafica ricette per tenant, collegando articolo prodotto, rese e scarti attesi.
- [ ] Gestire righe ricetta con articoli input, quantità o percentuali e indicazione di obbligatorietà.
- [ ] Strutturare ingredienti e allergeni nella ricetta; definire i giorni di vita e le istruzioni di conservazione/cottura.
- [ ] Guidare la lavorazione da ricetta: precompilare input e lotti FEFO, poi registrare i pesi reali confermati dall'operatore.
- [ ] Generare etichette dal lotto (o da articolo e lotto) con denominazione, ingredienti, allergeni evidenziati, lotto, scadenza, conservazione e dati OSA; includere peso/prezzo quando disponibili.
- [ ] Derivare ingredienti e allergeni dai dati della ricetta senza ricopiatura manuale; limitare eventuali override al ruolo admin.
- [ ] Completare il collaudo di stampa con coda `print_jobs`, Local Print Agent e stampante prevista (DYMO).
- [ ] Verificare con una ricetta reale che una lavorazione guidata produca un'etichetta completa e coerente.

**Verifica di fase:** è possibile produrre un preparato, ad esempio salsicce fresche, partendo da una ricetta; l'etichetta riporta ingredienti, allergeni, lotto interno e scadenza tramite il Local Print Agent.

### Inventario

- [ ] Realizzare la UI/API di rettifica per lotto, delta e motivo (inventario, calo, reso o errore).
- [ ] Aggiornare giacenza e movimento `RETTIFICA` in modo coerente e tracciabile; non consentire di correggere la giacenza modificando il lotto.
- [ ] Mostrare il confronto tra conteggio fisico per articolo e quantità teorica, sommando i lotti.
- [ ] Testare, tra gli altri casi, una rettifica di −0,250 kg su un lotto `V` e verificare giacenza e storico movimenti.

### HACCP lite (opzionale, solo su richiesta del pilota)

- [ ] Confermare con il cliente che il registro semplificato delle temperature è necessario.
- [ ] Se approvato, registrare temperatura all'ingresso e in cella con un registro giornaliero semplice.
- [ ] Mantenere esplicito che la funzione non fornisce un manuale HACCP né firme o certificazioni ASL.

## 2. Fase B — Vendite interne

### Documento e scarico di magazzino

- [ ] Definire l'aggregato persistente di vendita e le relative migrazioni.
- [ ] Registrare tenant, data, numero progressivo per tenant, cliente opzionale (o banco) e tipo documento `DDT`/`RICEVUTA`.
- [ ] Registrare per ogni riga lotto, articolo, quantità, unità di misura, prezzo unitario e IVA a solo scopo informativo.
- [ ] Implementare lo scarico parziale, il movimento `VENDITA` e la chiusura del lotto a giacenza zero, in un'unica transazione.
- [ ] Rifiutare con HTTP 409 una vendita che eccede la giacenza disponibile; verificare concorrenza e rollback in caso di errore.
- [ ] Estendere il servizio vendite e il repository di tracciabilità senza usare il modello legacy.
- [ ] Collegare le vendite alla genealogia in avanti dei lotti.
- [ ] Aggiungere test per scarico parziale, lotto esaurito, quantità insufficiente, numerazione e isolamento tenant.

### Banco, listini e documenti

- [ ] Realizzare una UI vendita adatta al tablet: ricerca articolo, lotto FEFO modificabile, quantità/peso, totale e stampa, senza passaggi tecnici.
- [ ] Usare il prezzo commerciale canonico dell'articolo per vendita ed etichetta; non usare `articoli_bilancia.prezzo1` come fonte del prezzo commerciale.
- [ ] Decidere se il listino HORECA distinto dal banco serve al pilota; in assenza di necessità, rinviarlo a v1.1.
- [ ] Generare il DDT dal documento persistito, con mittente OSA, destinatario cliente, righe e lotto, numero progressivo e possibilità di ristampa dallo storico.
- [ ] Verificare che ristampare lo stesso DDT mantenga numero e righe e non generi un documento orfano.
- [ ] Generare la ricevuta non fiscale dallo stesso documento di vendita tramite Local Print Agent.
- [ ] Inserire in modo visibile la dicitura: “Documento non fiscale — non sostituisce lo scontrino del registratore telematico”.
- [ ] Mostrare nel menu/listino operativo solo articoli attivi con almeno un lotto disponibile, con possibilità di disattivare il filtro.
- [ ] Verificare il flusso completo: vendita a cliente anagrafico, scarico corretto dei lotti e stampa del DDT.

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
