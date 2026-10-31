# Articoli e tracciabilità dei lotti

## Modello dati

Il modello SaaS usa `articoli` al posto di `tagli`; i flussi della UI desktop
legacy e le altre tabelle non sono migrati da questa modifica. Il CRUD dei
tagli legacy è fuori dal perimetro SaaS concordato.

- `articoli` è l'anagrafica degli articoli di magazzino (materie prime, tagli e
  prodotti finiti). Ogni articolo ha un'unità di misura e appartiene a un
  tenant.
- `documenti_ingresso` conserva i dati del documento del fornitore.
- `lotti` registra una quantità concreta. Un lotto in ingresso ha codice
  `numeroA`; ciascun prodotto creato da una lavorazione ha un lotto distinto
  `numeroV`.
- `righe_ingresso_tracciato` collega ogni lotto `A` al documento e alla
  quantità ricevuta.
- `lavorazioni`, `lavorazione_input` e `lavorazione_output` registrano
  rispettivamente la trasformazione, i lotti consumati e gli articoli
  prodotti. È possibile avere più input e più output per lavorazione.
- `movimenti_lotto` mantiene lo storico delle variazioni positive e negative di
  giacenza; `lavorazione_scarto` registra cali/scarti dichiarati senza
  confonderli con un articolo commercializzabile.

Le quantità sono memorizzate come `DECIMAL(12,3)`. Il consumo aggiorna la
giacenza del lotto nella stessa transazione che crea la lavorazione e i lotti
di output; ciascuna variazione è registrata anche in `movimenti_lotto`.
Progressivo e lotto sono anch'essi creati nella transazione; i
contatori `prog_acq` e `prog_ven` di `progressivi` sono bloccati durante
l'assegnazione. Le chiavi e le query del nuovo modello sono filtrate per
`tenant_id`.

Ogni riga di ingresso crea un lotto `A` indipendente, anche quando più righe
sono sullo stesso DDT. Ogni riga di output crea un lotto `V` indipendente.
Per esempio, il sezionamento di un lotto di Mezzena in Lombo, Spalla e Pancia
crea tre lotti `V`; una lavorazione successiva può consumare il lotto della
Pancia e creare il lotto `V` delle Salsicce Fresche.

## Aggiornamento del database

- Nuova installazione: usare lo schema aggiornato in
  [`saas/init_database.sql`](../saas/init_database.sql).
- Installazione esistente: applicare una sola volta
  [`saas/migrations/20261003_stock_traceability.sql`](../saas/migrations/20261003_stock_traceability.sql)
  e
  [`saas/migrations/20261031_work_operator_id.sql`](../saas/migrations/20261031_work_operator_id.sql).
  La seconda migrazione aggiunge l'identificativo dell'operatore alle lavorazioni
  già esistenti.

La migrazione non converte i record storici: le tabelle legacy non contengono
sempre l'identificativo dell'articolo e le relazioni necessarie per ricostruire
una genealogia certa. La migrazione dei dati va quindi eseguita solo dopo una
riconciliazione esplicita degli articoli, delle quantità e dei lotti.
In un database esistente, `20261003_stock_traceability.sql` non copia
automaticamente i record da `tagli` ad `articoli`; riconciliare il catalogo
prima di dismettere i dati legacy.

## API SaaS

Le nuove rotte usano il tenant del token autenticato; il client non deve
inviare `tenant_id`.

- La gestione CRUD del catalogo articoli è disponibile in Configurazioni.
- Ogni articolo può essere escluso dagli input delle lavorazioni lasciandolo
  attivo per ingressi, tracciabilità e vendita. La proprietà
  `utilizzabile_come_input` è attiva per default; disattivandola, i lotti
  disponibili dell'articolo non compaiono tra gli input e il backend rifiuta
  comunque la registrazione di una lavorazione che li utilizzi.
  Per database già esistenti, applicare prima
  `saas/migrations/20261031_articoli_input_lavorazione.sql`.
- I documenti e i lotti in ingresso si registrano solo da Ingresso merce; la
  conferma usa `POST /api/v1/tracciabilita/ingressi`.
- La schermata Tracciabilità consente di consultare i lotti e registrare le
  lavorazioni. Gli articoli di output sono selezionati dal catalogo esistente.
- `GET /api/v1/articoli`: elenca il catalogo.
- `POST /api/v1/articoli`: crea un articolo, per esempio
  `{"nome":"Mezzena Suino","categoria":"Suino","unita_misura":"kg"}`.
- `POST /api/v1/tracciabilita/ingressi`: registra data, fornitore, DDT e righe
  con `articolo_id` e quantità; risponde con i lotti `A` creati.
- `GET /api/v1/tracciabilita/lotti?solo_disponibili=true`: elenca le giacenze.
- `GET /api/v1/tracciabilita/lotti/{lotto_id}`: restituisce il documento
  d'ingresso oppure la lavorazione con i suoi lotti input/output.
- `POST /api/v1/tracciabilita/lavorazioni`: riceve data, descrizione, lotti
  input e articoli/quantità output; risponde con i lotti `V` creati.

Esempio di lavorazione:

```json
{
  "data": "2026-10-03",
  "descrizione": "Sezionamento mezzena",
  "input": [{"lotto_id": 12, "quantita": "85.000"}],
  "output": [
    {"articolo_id": 2, "quantita": "24.000"},
    {"articolo_id": 3, "quantita": "20.000"},
    {"articolo_id": 4, "quantita": "18.000"}
  ],
  "scarti": [{"descrizione": "Rifilatura", "quantita": "3.000", "unita_misura": "kg"}]
}
```

L'ingresso SaaS usa `POST /api/v1/tracciabilita/ingressi` e crea documenti,
lotti e movimenti nel nuovo modello; il vecchio endpoint resta disponibile ai
client non migrati.
