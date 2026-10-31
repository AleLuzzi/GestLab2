# Piano: anagrafica condivisa di clienti e fornitori

## Obiettivo e decisione architetturale

Realizzare un'anagrafica riutilizzabile per clienti e fornitori, con indirizzi e
dati utili alla fatturazione, integrandola con l'ingresso merce esistente.

La raccomandazione è **non rinominare la tabella `fornitori` in `anagrafica` e
non duplicare tutti i dati in due tabelle indipendenti**. Introdurre una tabella
comune `soggetti` con i dati condivisi e mantenere i dati operativi specifici
del fornitore separati. Un soggetto potrà avere entrambi i ruoli.

La fatturazione elettronica completa non è compresa in questo piano: si
preparano i dati anagrafici e i riferimenti necessari, ma la generazione,
trasmissione e conservazione delle fatture richiedono un progetto successivo.
Le regole fiscali e i campi obbligatori dovranno essere verificati in base al
regime e al formato di fatturazione effettivamente adottati.

## Situazione attuale nel progetto

- Lo schema iniziale è definito in `saas/init_database.sql`; il bootstrap crea
  le tabelle da questo file.
- `fornitori` contiene `azienda`, le abilitazioni all'ingresso merce e
  all'inventario e `tenant_id`.
- Modello, repository, servizio, schemi API e CRUD web gestiscono i fornitori
  come risorsa autonoma.
- La maschera d'ingresso carica `/api/v1/fornitori` e seleziona il fornitore.
- Il percorso d'ingresso operativo salva il nome testuale del fornitore in
  `ingresso_merce.fornitore`.
- Il percorso tracciato salva il nome testuale in
  `documenti_ingresso.fornitore`; lotti e tracciabilità leggono poi quel
  documento.

## Modello dati proposto

Le definizioni seguenti sono logiche: tipi, lunghezze e nomi finali vanno
allineati alle convenzioni dello schema esistente prima dell'implementazione.

### `soggetti`: dati comuni

Contiene una sola volta i dati condivisi da clienti e fornitori:

- chiave primaria e `tenant_id`;
- denominazione/ragione sociale;
- tipo di soggetto, almeno azienda o persona fisica;
- nome e cognome, utilizzati quando il soggetto è una persona;
- partita IVA e codice fiscale;
- indirizzo, numero civico, CAP, città/comune, provincia e Paese;
- email, telefono e contatto di riferimento, se utili al flusso operativo;
- indirizzo di fatturazione distinto da quello principale solo se serve davvero;
- stato attivo/disattivo e date di creazione/aggiornamento.

Il CAP va memorizzato come testo per conservare zeri iniziali e formati esteri.
I dati non disponibili restano nullable. Non usare il nome della città o la
ragione sociale come chiave univoca: uno stesso nome può appartenere a soggetti
diversi. Se si introduce un controllo duplicati, deve essere esplicito e
tenant-scoped, non un vincolo rigido basato soltanto sul nome.

Usare una chiave composta/un vincolo univoco su `(tenant_id, id)` per rendere
possibili riferimenti che impediscano associazioni tra tenant diversi.

### Ruoli e dati specifici

Il modello deve permettere che un soggetto sia cliente, fornitore o entrambi.
Per esplicitare i ruoli si raccomanda una tabella `soggetti_ruoli` con
`tenant_id`, `soggetto_id` e ruolo (`cliente` o `fornitore`), con vincolo
univoco per coppia soggetto/ruolo e vincolo di appartenenza allo stesso
tenant. In alternativa, due flag sulla tabella comune sono accettabili solo
se si vuole mantenere intenzionalmente il modello minimale e non si prevedono
nuovi ruoli.

Mantenere le opzioni operative esclusivamente sui fornitori: creare una tabella
`fornitori` legata al soggetto (ad esempio `soggetto_id` come PK/FK) che
conservi `flag1_ing_merce` e `flag2_inventario`. In questo modo le funzionalità
esistenti non dipendono da campi non pertinenti ai clienti. La tabella
`clienti` può essere introdotta solo quando emergono attributi esclusivi dei
clienti; non crearla vuota per simmetria.

Durante la transizione, la colonna legacy `fornitori.azienda` viene mantenuta
come copia compatibile della denominazione, sincronizzata dalle API e non
usata come fonte canonica; i nuovi percorsi leggono `soggetti.denominazione`.

La cancellazione di un soggetto referenziato da documenti deve essere impedita
o sostituita dalla disattivazione. I documenti e la tracciabilità non devono
perdere i propri riferimenti a seguito della cancellazione di un'anagrafica.

### Dati per la fatturazione

Prevedere nell'anagrafica i recapiti fiscali del destinatario, mantenendoli
distinti dai dati della fattura:

- ragione sociale o nome e cognome;
- partita IVA e codice fiscale;
- indirizzo di fatturazione completo, CAP, città, provincia e Paese;
- codice destinatario SDI e PEC, se applicabili;
- eventuale contatto amministrativo e condizioni/termini di pagamento solo
  quando richiesti dal flusso.

Il codice destinatario e la PEC sono alternativi/condizionati dalle regole
applicabili e non vanno validati con assunzioni universali nel frontend.
Specificare i formati e i campi obbligatori dopo aver scelto il processo di
fatturazione.

Non mettere nell'anagrafica valori che appartengono alla singola fattura:
numero e data, righe, imponibile, aliquote e importi IVA, totali, valuta,
causali o stato di emissione. Questi andranno in future tabelle di documenti
fiscali e righe fattura. La fattura dovrà conservare una copia/snapshot dei
dati del cliente usati al momento dell'emissione, così una modifica successiva
all'anagrafica non altererà i documenti già emessi.

## Modifiche alle tabelle di ingresso merce

### `ingresso_merce`

La colonna testuale `fornitore` non identifica stabilmente il soggetto. Il
piano è:

1. Aggiungere una colonna nullable `fornitore_id` collegata al soggetto con
   ruolo fornitore e con garanzia di `tenant_id` coerente.
2. Aggiornare insert, update, letture, filtri ed export per utilizzare l'ID e
   recuperare la denominazione con join quando serve visualizzarla.
3. Decidere se conservare `fornitore` come snapshot del nome al momento
   dell'ingresso. È raccomandato conservarlo o sostituirlo con una colonna
   esplicitamente denominata `fornitore_nome_snapshot`, perché le stampe e lo
   storico devono restare comprensibili anche se la denominazione cambia.
4. Dopo aver verificato che tutti i flussi scrivono e leggono l'ID, rimuovere
   la colonna testuale originaria oppure rinominarla come snapshot, evitando
   due fonti correnti di verità.

### `documenti_ingresso`

La tabella tracciata è il riferimento del lotto e oggi salva il nome del
fornitore:

1. Aggiungere `fornitore_id` come riferimento al soggetto/ruolo fornitore,
   mantenendo `tenant_id` nel vincolo relazionale.
2. Conservare una denominazione snapshot (per esempio
   `fornitore_nome_snapshot`) nel documento, così il dettaglio del lotto,
   le stampe e i report non cambiano retroattivamente.
3. Aggiornare `registra_ingresso`, la lettura del dettaglio lotto e ogni
   selezione/report che legge `documenti_ingresso.fornitore`.
4. Impedire la cancellazione fisica di soggetti referenziati; l'eventuale
   disattivazione non deve modificare il documento.

L'API non deve accettare un ID appartenente a un altro tenant, né un soggetto
senza il ruolo fornitore o non abilitato all'ingresso merce. La verifica va
eseguita lato server nella stessa transazione dell'inserimento del documento.

### Ingresso operativo e ingresso tracciato

Nel repository esistono due percorsi distinti. Implementare la modifica su
entrambi, senza lasciarli con semantiche discordanti:

- percorso operativo: `IngressoMerceCreate`, endpoint
  `/api/v1/ingresso-merce`, servizio ingresso merce e repository
  `core/repositories/ingresso_merce_repo.py`;
- percorso tracciato: `IngressoTracciatoCreate`, endpoint
  `/api/v1/tracciabilita/ingressi` e
  `saas/repositories/tracciabilita_repo.py`.

Usare un nome esplicito e coerente nel payload, ad esempio `fornitore_id`.
Non accettare il nome libero come sostituto dell'identificativo nei nuovi
flussi. Se in una fase intermedia si mantiene la stringa per compatibilità,
il backend deve risolverla in modo non ambiguo e segnalare un errore chiaro
quando non trova un unico fornitore valido.

## Modifiche backend e API

1. Definire i modelli Python per il soggetto e gli eventuali dati di ruolo,
   mantenendo compatibilità con il modello multi-tenant e con le convenzioni
   esistenti.
2. Introdurre repository/service per ricerca, elenco, creazione, aggiornamento
   e disattivazione; tutte le query devono essere filtrate per tenant.
3. Esportare API per elenco/CRUD dei soggetti. Supportare filtro per ruolo,
   stato e ricerca per denominazione; le risposte devono includere i dati
   comuni e i campi operativi del fornitore quando applicabili.
4. Mantenere gli endpoint `/api/v1/fornitori` come superficie compatibile per
   la UI esistente durante la transizione, implementandoli sopra il modello
   condiviso oppure aggiornando insieme tutti i client interni.
5. Validare lunghezze, stringhe vuote, formati basilari e coerenza del tipo
   persona/azienda negli schemi Pydantic. Non imporre regole fiscali non ancora
   decise.
6. Aggiornare gli endpoint di ingresso affinché validino ruolo, abilitazioni e
   tenant del soggetto selezionato prima di scrivere.
7. Restituire errori espliciti e coerenti per identificativi inesistenti,
   non autorizzati, disattivati o privi del ruolo richiesto.

## Aggiornamento frontend

### Navigazione e pagina anagrafica

- Sostituire la sola voce “Fornitori” con una sezione “Clienti e fornitori”
  (o “Anagrafiche”), accessibile dalle configurazioni.
- Creare un elenco filtrabile per ruolo e stato, con ricerca per
  denominazione, codice fiscale o partita IVA.
- Riutilizzare un solo form per i dati comuni, mostrando i ruoli selezionati.
- Mostrare le abilitazioni “ingresso merce” e “inventario” solo quando è
  selezionato il ruolo fornitore.
- Organizzare i campi in gruppi leggibili: soggetto, indirizzi, contatti e
  fatturazione. Etichettare con chiarezza i campi opzionali e quelli
  condizionatamente richiesti.
- Supportare creazione, modifica e disattivazione; evitare eliminazioni
  distruttive quando l'anagrafica è già usata.
- Aggiornare `web/js/features/anagrafiche.js`, `web/js/core/navigation.js`,
  le viste in `web/index.html` e il riepilogo/configurazioni che oggi cita
  soltanto i fornitori.

### Selettore dell'ingresso merce

- Caricare solo soggetti con ruolo fornitore, attivi e abilitati all'ingresso
  merce.
- Usare l'ID del soggetto come `value` dell'opzione e la denominazione come
  etichetta.
- Inviare `fornitore_id` all'API; non affidarsi al testo visualizzato come
  identità del fornitore.
- Aggiornare il riepilogo e gli eventuali dettagli per visualizzare il nome
  snapshot o quello restituito dal server.
- Gestire esplicitamente il caso in cui non esistano fornitori selezionabili
  e gli errori di caricamento/salvataggio.

## Schema iniziale e database attualmente in uso

Non è richiesta una procedura generale di conversione per database storici.
Rimane però necessario applicare il nuovo schema al database attualmente in
uso: `CREATE TABLE IF NOT EXISTS` non modifica tabelle già create.

Prima dell'implementazione, chiarire se i dati presenti nel database corrente
sono sacrificabili:

- **Se sono sacrificabili:** ricreare il database di sviluppo dal nuovo
  `saas/init_database.sql` e verificare il bootstrap end-to-end.
- **Se vanno conservati:** preparare una modifica mirata per il solo database
  corrente. Creare i soggetti dai fornitori esistenti, preservare ID/nome e
  abilitazioni, collegare gli ingressi che si possono associare senza
  ambiguità e lasciare gli altri non collegati con un esito esplicito da
  risolvere. Non eliminare dati o disabilitare vincoli in modo generico.

In entrambi i casi:

1. Aggiornare `saas/init_database.sql` come schema canonico per i nuovi
   ambienti.
2. Non fare affidamento sul bootstrap per applicare `ALTER TABLE` impliciti:
   il file di inizializzazione usa `CREATE TABLE IF NOT EXISTS`.
3. Applicare le modifiche allo schema esistente con uno script esplicito e
   verificabile, oppure ricreare il database soltanto dopo aver confermato
   che i dati correnti sono sacrificabili.
4. Verificare chiavi, indici, foreign key e compatibilità MySQL con il charset
   e gli ID delle tabelle già presenti.
5. Documentare una procedura di ripristino prima di intervenire sul database
   in uso.

### Implementazione prevista per il database esistente

Per conservare i dati senza ricostruire il database, usare
`saas/migrations/20261031_soggetti_clienti_fornitori.sql` una sola volta sul
database preesistente, dopo averne fatto un backup. La migrazione conserva gli
ID dei fornitori creando i soggetti con lo stesso ID iniziale, mantiene le
colonne testuali `fornitore` come snapshot e collega gli ingressi solo quando
il nome corrisponde in modo esatto e univoco nel tenant. Gli ingressi non
associabili restano consultabili con `fornitore_id` nullo e snapshot
inalterato; non vengono assegnati automaticamente a un soggetto ambiguo.

La migrazione è intenzionalmente one-shot: non va eseguita dopo aver creato il
database dal nuovo `init_database.sql` e non viene eseguita automaticamente dal
bootstrap. Prima dell'esecuzione, verificare backup, ambiente e conteggi dei
record; in caso di errore, interrompere e ripristinare/analizzare il database
prima di riprovare, senza rilanciare alla cieca gli `ALTER TABLE`.

## Sequenza di implementazione

1. **Confermare le decisioni funzionali:** soggetti persona fisica/azienda,
   ruoli multipli, indirizzo di fatturazione separato, campi fiscali richiesti
   e sorte dei dati attualmente presenti.
2. **Definire lo schema:** `soggetti`, ruoli e dati specifici fornitore;
   vincoli multi-tenant e riferimenti per documenti.
3. **Implementare modello, repository e service:** CRUD tenant-scoped,
   disattivazione e ricerca.
4. **Esporre le API:** anagrafica comune, compatibilità dei fornitori ed
   endpoint di ingresso basati su ID.
5. **Aggiornare i due flussi di ingresso:** operativo e tracciato, compresi
   snapshot e dettaglio lotto.
6. **Aggiornare il frontend:** navigazione, elenco/form soggetti e selettore
   fornitore dell'ingresso.
7. **Aggiornare e verificare lo schema** sul database corrente secondo la
   decisione di conservazione dei dati.
8. **Eseguire test e prova manuale end-to-end** prima di aggiungere emissione
   fatture o altre funzioni fiscali.

## Test e criteri di accettazione

- Un soggetto può essere cliente, fornitore o entrambi, senza duplicare i
  dati comuni.
- Un tenant non può leggere, modificare o referenziare i soggetti di un altro
  tenant.
- Le abilitazioni operative esistono solo per i fornitori e filtrano
  correttamente il selettore d'ingresso.
- CRUD e ricerca preservano CAP come stringa e supportano dati facoltativi.
- Il flusso operativo e quello tracciato rifiutano un ID inesistente, di altro
  tenant, disattivato o non valido per l'ingresso.
- Un ingresso salva il riferimento al fornitore corretto e conserva una
  denominazione storica leggibile.
- Il dettaglio lotto e i report continuano a mostrare il fornitore dopo una
  modifica alla denominazione o una disattivazione.
- Una anagrafica referenziata non può essere eliminata causando perdita o
  corruzione dello storico.
- I test coprono repository, servizi, API, tenant isolation e i due flussi
  d'ingresso; la UI consente di creare/modificare un fornitore e registrare un
  ingresso completo.
- Un bootstrap su schema vuoto crea tutte le tabelle e i vincoli previsti.

## Fuori ambito immediato

- Emissione e numerazione delle fatture.
- Calcolo IVA, note di credito, pagamenti, scadenze e registri fiscali.
- Integrazione con SDI, firma, invio e conservazione a norma.
- Gestione di più sedi o indirizzi con tipologie/storico, salvo che diventi un
  requisito confermato.
