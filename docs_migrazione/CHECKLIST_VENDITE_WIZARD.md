# Checklist wizard Vendite

Checklist per portare Vendite allo stesso wizard a tre passi di Ingresso merce e per spostare storico DDT e storico ricevute in una voce di menu Report. Le decisioni sotto sono chiuse: non vanno riaperte durante la realizzazione.

## Come usarla

- Seguire le fasi nell'ordine: prima il wizard di Vendite, poi Report, poi gli stili, infine manuale e verifica.
- Spuntare una voce solo dopo aver verificato il criterio indicato sulla voce stessa.
- Il documento descrive il lavoro. Non sostituisce la pagina Vendite né il menu finché le voci non sono spuntate.

## Decisioni chiuse

- Vendite usa gli stessi tre passi di Ingresso merce: Intestazione, Articoli, Riepilogo. Un solo passo è visibile. Indietro è libero. Il passo 3 si apre solo con almeno una riga. La conferma sta solo sul passo 3.
- I selettori del wizard interrogano solo il proprio pannello. `mostraStep` in `web/js/features/ingresso-merce.js` oggi usa `document.querySelectorAll` su `.ingresso-step`, `[data-step-indicator]` e `[data-step-back]`. Con due wizard nella stessa pagina quei selettori vanno limitati a `#view-ingresso-merce`, e quelli di Vendite a `#view-vendite`.
- Passo 1, Intestazione: data di oggi in sola lettura, cliente, tipo documento. Per il DDT il cliente è obbligatorio prima di continuare. Per la ricevuta non fiscale si può lasciare «Banco / cliente non indicato».
- Passo 2, Articoli: restano ricerca, filtro «Solo articoli con lotto disponibile», select articolo, select lotto FEFO, quantità, prezzo in sola lettura, riepilogo del lotto e «Aggiungi al riepilogo». Non si copiano i pulsanti di categoria né il disegno dell'animale.
- Passo 3, Riepilogo: data, cliente, tipo documento, numero di righe e totale. Ogni riga mostra articolo, lotto, quantità, prezzo, importo e Rimuovi. Il pulsante è «Registra vendita».
- Lo scanner consuma il codice solo se `#view-vendite` è attiva e il passo Articoli è visibile. Seleziona l'articolo e mette il focus sulla quantità. Sugli altri passi non consuma la scansione.
- «Aggiorna lotti» resta nell'intestazione del pannello Vendite. Ricarica listino, lotti e clienti e non svuota il carrello né cambia passo.
- Aprire Vendite dal menu non azzera una vendita in corso. Il ritorno al passo 1 con carrello vuoto avviene dopo una registrazione riuscita.
- Storico DDT e storico ricevute escono da `#view-vendite`. Nel menu laterale, subito dopo Vendite, compare **Report** (`data-view="report"`) e il pannello `#view-report`. Le due tabelle, «Scarica / ristampa» e «Ristampa» restano quelli di oggi: rileggono il documento già registrato e non ne creano uno nuovo.
- Il caricamento degli storici esce da `loadVendite` e va in `loadReport`, chiamato da `web/js/core/navigation.js` all'apertura di Report. La logica sta in `web/js/features/report.js`.
- Dopo la registrazione il messaggio di esito resta sul wizard e, se il DDT o la ricevuta non sono stati generati, invita a riprovare da Report. Gli storici non si ricaricano finché non si apre Report.
- Payload, IVA a zero, conferma del TMC superato e rifiuto se la quantità supera la giacenza restano quelli di `registraVendita` e `aggiungiRiga`. Nessun cambiamento a `saas/services/vendite.py`, ai repository, allo schema o agli endpoint `POST /api/v1/vendite/complete`, `GET /api/v1/vendite/ddt`, `GET /api/v1/vendite/ricevute`, `GET /api/v1/vendite/{id}/ddt.pdf` e `POST /api/v1/vendite/{id}/ricevuta`.
- Report non entra nella landing. Lo vedono gli stessi utenti che vedono le altre voci del menu laterale.

## 1. Wizard Vendite

Punto di innesto: `#view-vendite` in `web/index.html` e `web/js/features/vendite.js`. Il modello è `#view-ingresso-merce` e `mostraStep` in `web/js/features/ingresso-merce.js`.

- [x] In `#view-vendite` aggiungere l'indicatore `ol` con classe `ingresso-steps` e i tre testi «1. Intestazione», «2. Articoli», «3. Riepilogo». Gli attributi di passo sono letti solo dentro `#view-vendite`.
- [x] Spezzare il pannello in tre `section` con classe `ingresso-step`. All'apertura è visibile solo l'intestazione; le altre hanno `hidden`.
- [x] Spostare nel passo 1 la data (`input type="date"` in sola lettura, valore `dataLocaleISO()`), `#sales-customer` e `#sales-document-type`. Il pulsante primario è «Continua agli articoli».
- [x] Bloccare «Continua agli articoli» se il documento è DDT e `#sales-customer` è vuoto. Messaggio: «Per un DDT seleziona un cliente.» e focus sul cliente. Con ricevuta non fiscale il passo 2 si apre anche senza cliente.
- [x] Spostare nel passo 2 `#sales-search`, `#sales-only-available`, `#sales-article`, `#sales-lot`, `#sales-quantity`, `#sales-price`, `#sales-lot-summary`, `#sales-selection-error` e `#btn-add-sales-line`. Il pulsante di aggiunta dice «Aggiungi al riepilogo» e non cambia passo.
- [x] Nel passo 2 lasciare «Indietro» verso l'intestazione e «Vai al riepilogo». Senza righe, «Vai al riepilogo» resta sul passo 2 e scrive «Aggiungi almeno un articolo prima di continuare.»
- [x] Nel passo 3 mostrare data, cliente (oppure «Banco»), tipo documento, conteggio righe e totale. L'elenco righe usa i dati già in `righeVendita`: articolo, codice lotto, quantità, prezzo, importo e Rimuovi.
- [x] Spostare `#btn-register-sales`, `#sales-checkout-error`, `#sales-checkout-status` e la dicitura «Documento non fiscale — non sostituisce lo scontrino del registratore telematico» nel passo 3. Togliere da `#view-vendite` le tabelle `#sales-history-body` e `#sales-receipt-history-body`.
- [x] In `vendite.js` aggiungere `mostraStep` limitato a `#view-vendite`: un solo passo visibile, indicatore con `aria-current="step"`, errori di conferma azzerati al cambio passo.
- [x] All'ingresso nel passo 3 rileggere data, cliente, tipo documento, righe e totale dai campi e da `righeVendita`. Rimuovere una riga aggiorna elenco e totale e, se non restano righe, lascia il passo 3 con l'elenco vuoto e «Registra vendita» disabilitato.
- [x] Prima di `POST /api/v1/vendite/complete` ricontrollare il DDT senza cliente, anche se l'utente è tornato all'intestazione e ha tolto il cliente. Il corpo della richiesta resta `data`, `cliente_id`, `tipo_documento` e `righe` con `lotto_id`, `articolo_id`, `quantita`, `unita_misura`, `prezzo_unitario` e `iva_percentuale` a `0.00`.
- [x] Dopo una registrazione riuscita svuotare `righeVendita`, tornare al passo 1, reimpostare la data a oggi e mostrare l'esito sul passo 1. Se il DDT o la ricevuta non vengono generati, il testo dice di riprovare da Report, non dallo storico.
- [x] Lo scanner in `initVendite` restituisce `false` se `#view-vendite` non è attiva o se il passo visibile non è Articoli. Sul passo Articoli seleziona l'articolo come `selezionaArticoloDaScanner` e mette il focus su `#sales-quantity`.
- [x] `loadVendite` continua a caricare `GET /api/v1/vendite/lotti-disponibili`, `GET /api/v1/menu?solo_disponibili=false` e `GET /api/v1/soggetti`, e non chiama più gli storici. Non svuota `righeVendita` e non cambia il passo corrente.
- [x] In `mostraStep` di `ingresso-merce.js` e nei listener `[data-step-back]` limitare le query a `#view-ingresso-merce`, così il wizard Vendite non viene nascosto da un cambio passo dell'ingresso.
- [x] Aggiornare il query string `?v=` di `vendite.js` in `web/js/app.js` e in `web/js/core/navigation.js` quando il modulo cambia.

## 2. Report

Punto di innesto: la sidebar e `switchView` in `web/js/core/navigation.js`, il nuovo pannello in `web/index.html`, il modulo `web/js/features/report.js`.

- [x] Aggiungere in `.sidebar`, subito dopo il pulsante Vendite, `<button class="nav-item" data-view="report">Report</button>`. Non aggiungere Report alla griglia della landing.
- [x] Aggiungere `#view-report` con titolo «Report», la tabella storico DDT (`#sales-history-body`, colonne Documento, Data, Cliente, Righe, azione «Scarica / ristampa») e la tabella storico ricevute non fiscali (`#sales-receipt-history-body`, azione «Ristampa»), con la dicitura che il documento non è fiscale.
- [x] Spostare in `report.js` il caricamento di `GET /api/v1/vendite/ddt` e `GET /api/v1/vendite/ricevute`, lo scarico di `GET /api/v1/vendite/{id}/ddt.pdf` e l'accodamento di `POST /api/v1/vendite/{id}/ricevuta`. `vendite.js` può chiamare da Report le funzioni di scarico e accodamento usate subito dopo la registrazione, senza disegnare le tabelle.
- [x] Esportare `loadReport` e registrarlo in `switchView` alla chiave `report`. All'apertura della vista si ricaricano entrambi gli storici.
- [x] In `web/js/app.js` chiamare `initReport` insieme agli altri `init`, con il query string `?v=` allineato agli altri import toccati.
- [x] «Scarica / ristampa» scarica `ddt_{numero}.pdf` del documento già registrato. «Ristampa» rimanda la stessa ricevuta al Local Print Agent. Nessuno dei due crea una vendita nuova. Gli stati restano `#sales-history-status` e `#sales-receipt-history-status`.

## 3. Stili

Gli stili stanno in `web/app.css`, accanto a `.ingresso-steps` e a `.sales-selection-fields`.

- [x] Il passo Vendite visibile usa la stessa presentazione di `.ingresso-step`: un solo blocco, azioni in fondo, campi touch con altezza minima 52 px.
- [x] La griglia dei campi di intestazione e articoli resta leggibile sotto i 640 px, sulla regola già presente per `.sales-selection-fields`.
- [x] Le tabelle di Report riusano `.sales-cart`, `.sales-cart-table-wrap` e lo scorrimento orizzontale già usato dal carrello. Non introducono una seconda scala di padding.

## 4. Manuale

File `docs_migrazione/MANUALE_UTENTE.md`.

- [x] Nella riga del menu laterale aggiungere Report accanto a Vendite.
- [x] Riscrivere la sezione 6 in tre passi: intestazione (data, cliente, DDT o ricevuta), articoli (ricerca, filtro giacenza, lotto FEFO, quantità, prezzo non modificabile, aggiungi), riepilogo (righe, totale, registra). La dicitura non fiscale sta nel riepilogo, non in fondo alla pagina.
- [x] Togliere «6.3 Ristampare» da Vendite e aggiungere una sezione Report: storico DDT con scarica o ristampa, storico ricevute con ristampa, stesso numero e stesse righe, nessun documento nuovo.
- [x] Nel testo dopo la registrazione, il rimando per un DDT o una ricevuta non generati punta a Report.

## 5. Verifica

- [x] `tests/test_vendite.py` resta verde, senza modifiche allo schema né agli endpoint.
- [x] In Vendite, con ricevuta non fiscale, il passo 1 prosegue senza cliente. Con DDT, senza cliente, resta sul passo 1 e mostra «Per un DDT seleziona un cliente.»
- [x] Sul passo Articoli, aggiungere una riga non cambia passo. «Vai al riepilogo» senza righe resta sul passo 2. Con una riga, il passo 3 mostra articolo, lotto, quantità, prezzo, importo e totale.
- [x] Rimuovere l'unica riga dal riepilogo lascia «Registra vendita» disabilitato. Tornare agli articoli e aggiungere di nuovo una riga ripristina il totale.
- [x] Un lotto con TMC superato chiede ancora conferma prima dell'aggiunta. Una quantità sopra la disponibilità non entra nel riepilogo. Una vendita rifiutata dal server non svuota le righe e non cambia passo.
- [x] Dopo una registrazione riuscita si torna al passo 1, il carrello è vuoto e il messaggio cita Report se il PDF o la ricevuta non partono. In `#view-vendite` non ci sono le tabelle storico.
- [x] Lo scanner sul passo Articoli seleziona l'articolo e focalizza la quantità. Sul passo Intestazione e sul passo Riepilogo la scansione non cambia l'articolo.
- [x] Aprire Report mostra i DDT e le ricevute del tenant. «Scarica / ristampa» scarica il PDF dello stesso numero. «Ristampa» accoda la stessa ricevuta. Nessuna delle due azioni crea una vendita.
- [x] Cambiare passo in Ingresso merce non nasconde né mostra i passi di Vendite, e il contrario.

## Fuori da questa checklist

- Pulsanti di categoria e disegno dell'animale nel passo Articoli di Vendite.
- Modifiche a servizi, repository, schema, prezzi, IVA o regole FEFO.
- Una voce Report nella landing o un filtro per ruolo diverso dalle altre voci del menu laterale.
- Report diversi dallo storico DDT e dallo storico ricevute non fiscali.
