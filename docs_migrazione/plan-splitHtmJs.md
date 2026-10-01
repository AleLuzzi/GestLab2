# Come separare HTML e JS in modo professionale

## Obiettivo
Separare il markup della UI in [web/index.html](web/index.html) dalla logica in [web/js/](web/js/), mantenendo la stessa UX ma migliorando manutenzione, testabilità e scalabilità.

## Passi consigliati

### 1) Fare un inventory delle responsabilità
- Elencare tutte le sezioni della pagina: login, landing, dashboard, configurazioni, CRUD, stampa, admin.
- Identificare quali parti sono statiche e quali sono dinamiche.
- Classificare le aree in base alla responsabilità:
  - struttura DOM
  - stato dell'app
  - chiamate HTTP
  - eventi utente
  - rendering della tabella/form

### 2) Tenere HTML come contenitore, non come script
- Lasciare in HTML solo:
  - container principali
  - moduli form
  - table/list placeholders
  - elementi con `id`, `class` e `data-*`
- Eliminare qualsiasi handler inline come `onclick`, `onchange` o `onsubmit`.
- Assicurarsi che la struttura sia semanticamente chiara e accessibile.

### 3) Centralizzare l'inizializzazione
- Creare una funzione unica come `initApp()` che viene eseguita a `DOMContentLoaded`.
- Dentro questa funzione:
  - inizializzare i form
  - collegare i listener agli elementi
  - impostare lo stato iniziale
  - mostrare la vista giusta

### 4) Separare le feature in blocchi funzionali
- Raggruppare il codice per feature, per esempio:
  - auth
  - dashboard
  - dipendenti
  - merceologie
  - reparti
  - tagli
  - fornitori
  - stampa
- Per ogni feature, mantenere uno schema coerente:
  - `loadX()`
  - `newX()`
  - `editX()`
  - `saveX()`
  - `deleteX()`

### 5) Estrarre le API e gli errori in un layer dedicato
- Mantenere un helper unico per le chiamate HTTP, ad esempio `api(path, options)`.
- Centralizzare:
  - header `Authorization`
  - refresh token
  - gestione 401
  - parsing JSON
  - errori standardizzati
- In questo modo si evita duplicazione del codice tra tutte le CRUD table.

### 6) Usare selettori stabili e un approccio data-driven
- Preferire `document.getElementById` per elementi univoci.
- Per liste e tabelle usare schema regolare:
  - `#dip-tbody`
  - `#merc-tbody`
  - `#tagli-tbody`
  - `#reparti-tbody`
- Usare `data-view` per navigazione e `data-tab` per le tab delle stampe.

### 7) Suddividere il JS in moduli logici
- Esempio di struttura ideale:
  - `web/js/app.js` -> bootstrap e inizializzazione
  - `web/js/api/client.js` -> richieste API, token e refresh
  - `web/js/core/` -> autenticazione, navigazione e helper DOM
  - `web/js/features/` -> dashboard, anagrafiche, ingresso merce, lotti, menu, stampa e admin
- Se si vuole restare su un file solo, almeno creare sezioni chiari con commenti e funzioni ben separate.

### 8) Condividere i dati tra view e form
- I CRUD devono seguire un modello uniforme:
  - `loadList()` per leggere la tabella
  - `populateSelectOptions()` per dropdown
  - `openForm()` per visualizzare il form
  - `saveForm()` per POST/PUT
  - `deleteRow()` per DELETE
- Ogni form deve usare campi coerenti con `name`, `id`, `value` e la validazione del payload del backend.

### 9) Migrare gradualmente, non in un colpo solo
- Prima separare solo il login e il menu.
- Poi i dashboard stats.
- Poi le CRUD di una tabella.
- Infine le funzioni di stampa e admin.
- Verificare dopo ogni blocco che non ci siano regressioni.

### 10) Verifica finale
Dopo il refactor, fare una checklist:
- [ ] HTML senza `onclick` inline
- [ ] JS senza logica di UI mescolata nel markup
- [ ] Login funziona
- [ ] Dashboard aggiorna i conteggi
- [ ] CRUD di Dipendenti, Merceologie, Reparti e Tagli funzionano
- [ ] Nessun errore in console
- [ ] Nessuna chiamata API duplicata

## Raccomandazione pratica per questo progetto
Per il repo attuale, il punto di partenza migliore è:
1. lasciare in [web/index.html](web/index.html) solo i container delle view e i form;
2. mantenere in [web/js/app.js](web/js/app.js) solo l'inizializzazione dei moduli;
3. creare una struttura per le CRUD via `load*` + `save*` + `delete*`;
4. mantenere `Tagli` allineato alle altre anagrafiche;
5. verificare con una sessione reale e i JSON restituiti da [saas/main.py](saas/main.py).

## Regola d'oro
Uno sviluppatore senior non separa file solo per ordine estetico: lo fa per ridurre il coupling, rendere ogni feature indipendente e semplificare i test. La separazione migliore è quella che lascia il markup a descrivere la UI e il JavaScript a descrivere il comportamento.
