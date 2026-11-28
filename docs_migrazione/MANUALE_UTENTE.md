# Manuale utente — GestLab

Guida per chi usa la console in laboratorio e al banco: ingresso merce,
lavorazione, etichetta e vendita. Non spiega come installare il server, il
database o il programma di stampa. Quelle istruzioni restano in
[ISTRUZIONI_USO.md](ISTRUZIONI_USO.md) e in
[PRINT_AGENT_WINDOWS.md](PRINT_AGENT_WINDOWS.md). Le schermate dello
stesso percorso sono in [sequenza_pilota/README.md](sequenza_pilota/README.md). Per il collaudo
formale con un operatore nuovo usa
[COLLAUDO_FLUSSO_MANUALE.md](COLLAUDO_FLUSSO_MANUALE.md).

GestLab registra la merce che entra, i preparati che escono dalla lavorazione
e le vendite interne del laboratorio. Non è una cassa fiscale, non invia
fatture elettroniche e non certifica etichette né procedure HACCP.

## 1. Accedere

1. Apri nel browser l’indirizzo della console che ti ha dato chi gestisce
   il laboratorio.
2. Inserisci email e password, poi premi **Accedi**.
3. In alto a destra compare la tua email e il ruolo (`admin` o `operatore`).
4. Per uscire premi **Esci**.

Se non ricordi la password, premi **Password dimenticata**, inserisci l’email
e poi **Invia collegamento**. Se l’indirizzo è registrato, arriva un
collegamento valido 60 minuti. La nuova password deve avere almeno 10
caratteri, con una lettera e un numero.

Dopo l’accesso la Home propone tre azioni: **Ingresso merce**,
**Configurazioni** e **Tracciabilità**. Il menu laterale (in alto sul tablet)
apre anche Dashboard, Vendite, Report, Listino, Stampa e Coda stampa.

La console ha bisogno di rete. Senza connessione non lavora in locale.

## 2. Prima del primo ingresso

Questi dati si preparano una volta, da **Home** → **Configurazioni**.

| Cosa serve | Dove | Cosa controllare |
|---|---|---|
| Articoli da ricevere e da produrre | Articoli | Nome, categoria, unità (`kg`, `pz` o `lt`), prezzo unitario, articolo attivo. Spunta **Utilizzabile come input di lavorazione** solo sulla merce che può entrare in una lavorazione. |
| Fornitore del DDT | Clienti e fornitori | Ruolo **Fornitore**, anagrafica attiva e **Abilitato per ingresso merce**. Senza questa spunta il fornitore non compare nell’ingresso. |
| Cliente del DDT | Clienti e fornitori | Ruolo **Cliente** e anagrafica attiva. |
| Chi ha lavorato | Dipendenti | Nome e cognome dell’operatore da scegliere in lavorazione. |
| Ricetta del preparato | Tracciabilità → Ricette | Vedi sotto. |
| Dati sull’etichetta | Configurazioni → Admin | Solo l’admin: ragione sociale, sede, laboratorio e partita IVA. |

Il prezzo di vendita e dell’etichetta è il **prezzo unitario** dell’articolo.
Se manca, la vendita di quell’articolo non si registra.

### Ricetta

Da **Tracciabilità** apri **Ricette** e premi **Nuova ricetta**.

1. Dai un nome e scegli il **prodotto ottenuto**.
2. Indica **resa attesa** e **scarto atteso** nell’unità del prodotto.
3. Aggiungi gli ingredienti. Per ciascuno scegli l’articolo, poi una quantità
   per kg di prodotto oppure una percentuale, e se è obbligatorio.
4. Spunta gli allergeni tra i 14 gruppi in elenco.
5. Se l’OSA li ha definiti, compila i **giorni di vita** e le istruzioni di
   conservazione e cottura. I giorni di vita non calcolano da soli la scadenza
   del lotto: in lavorazione la data va sempre dichiarata.
6. Lascia spuntata **Ricetta attiva** e premi **Salva ricetta**.

Una ricetta disattivata resta nello storico e non compare più tra le
lavorazioni nuove. Non si cancella.

Ingredienti, allergeni e istruzioni sono i dati dichiarati dall’OSA. GestLab
li riporta sull’etichetta, ma non li certifica.

## 3. Ingresso merce

Da Home premi **Ingresso merce**. I passaggi sono tre.

### 3.1 Intestazione

La data è quella di oggi e non si modifica. Scegli il fornitore e scrivi il
**numero documento / DDT** stampato sul documento del fornitore. Premi
**Continua agli articoli**.

**Azzera movimento** svuota il documento non ancora confermato.

### 3.2 Articoli

1. Scegli la **categoria**, poi il taglio:
   - **Bovino**, **Vitello** e **Suino**: sul profilo dell’animale tocca la zona
     del taglio che stai ricevendo. Un secondo tocco sulla stessa zona la
     deseleziona.
   - **Bovino**: con **Quarto anteriore** e **Quarto posteriore** vedi un solo
     profilo alla volta.
   - Accanto al profilo trovi i pulsanti per tagli fuori dal disegno: mezzena
     (bovino, vitello e suino), filetto (bovino e suino), lardo (solo suino).
     Sul vitello resta solo la mezzena.
   - **Condimento** e **Preparato**: elenco a pulsanti con il nome dell’articolo,
     senza disegno (per esempio Sale, Salsicce fresche).
   - Un articolo disattivato in Configurazioni non si seleziona: la zona o il
     pulsante resta spento.
2. Con lo scanner sul campo, il codice a barre seleziona l’articolo, anche con
   il profilo a video: apre la categoria giusta e evidenzia la zona o il pulsante.
3. Compila i dati del lotto, se il fornitore li indica. Valgono per gli
   articoli che aggiungi subito dopo:
   - **Lotto fornitore**
   - **Origine**
   - **Tipo di data**: nessuna, **Data di scadenza** oppure **Termine minimo
     di conservazione (TMC)**. Una riga ha un solo tipo.
   - **Data riportata dal fornitore**
   - **Temperatura all’ingresso**, se la misuri: da −100 a 100 °C, con due
     decimali
   - **Note del lotto**, facoltative, fino a 500 caratteri (per esempio «bio»
     o la razza). La nota resta su questo lotto e non passa da sola ai
     preparati.
4. Inserisci la **quantità ricevuta** con fino a tre decimali, per esempio
   `12,500`, nell’unità dell’articolo.
5. Premi **Aggiungi al riepilogo**. Ripeti per ogni articolo del DDT.
6. Premi **Vai al riepilogo**.

### 3.3 Riepilogo

Controlla data, fornitore, numero DDT e ogni riga. Se manca qualcosa, torna
agli articoli. Quando è corretto, premi **Conferma ingresso**.

Ogni riga diventa un lotto di ingresso (tipo acquisto). La quantità confermata
è la giacenza iniziale. Il lotto, il fornitore e il numero DDT restano
collegati e si ritrovano nel dettaglio del lotto.

## 4. Lavorazione

Apri **Tracciabilità** → **Lavorazione**.

1. La data proposta è oggi. Scegli l’**operatore** e, se serve, una
   descrizione breve.
2. Scegli la **ricetta** e la **quantità prodotto prevista (kg)**. La
   precompilazione vale per i prodotti in kg. Premi **Precompila input FEFO**.
3. Controlla gli **input**. Per ogni ingrediente il lotto proposto è quello
   con la data applicabile più vicina (FEFO). I lotti senza data stanno in
   coda. Puoi scegliere un altro lotto disponibile. Correggi la quantità con
   il peso reale. Se un ingrediente facoltativo non lo usi, premi **Rimuovi**.
   Se la disponibilità non basta, il messaggio lo indica: non confermare una
   quantità che non hai.
4. Controlla l’**output**. Il prodotto della ricetta è già proposto: inserisci
   il peso reale. Per ogni prodotto dichiari tu:
   - **Tipo di data** (scadenza o TMC) e la **data**
   - **Origine dichiarata**

   Questi dati non vengono copiati né calcolati dai lotti in ingresso. I
   giorni di vita della ricetta non impostano la data: sono solo un
   riferimento dell’OSA.
5. Se c’è scarto pesato, aggiungilo con descrizione, quantità e unità (`kg` o
   `pz`).
6. Spunta **Confermo che le quantità di input e output sono i pesi reali
   rilevati e verificati dall’operatore.** Se cambi input o output dopo la
   spunta, la conferma non vale più: va rimessa.
7. Premi **Registra lavorazione**.

A registrazione riuscita compare il codice del lotto prodotto (tipo
produzione). Gli input vengono scaricati e il nuovo lotto entra in giacenza
nella stessa operazione.

Regole da rispettare:

- Un lotto con **scadenza già passata** non si può selezionare.
- Un lotto con **TMC già passato** si può usare solo se confermi il messaggio
  «Uno o più lotti hanno il TMC superato».
- Gli ingredienti obbligatori della ricetta e il prodotto previsto devono
  essere presenti.
- Senza almeno un input e un output la lavorazione non si registra.
- Puoi lavorare anche senza ricetta, con **Lavorazione manuale** e i pulsanti
  **+ Aggiungi lotto**, **+ Aggiungi prodotto** e **+ Aggiungi scarto**. Per
  il preparato da vendere ed etichettare usa la ricetta: è lei che porta
  ingredienti e allergeni in etichetta.

## 5. Etichetta

Apri **Stampa** → scheda **Etichetta**.

1. Nel campo **Lotto** scegli il lotto prodotto (codice e nome articolo). Non
   usare «Etichetta manuale» per il preparato tracciato.
2. Sotto compare il riepilogo della ricetta collegata alla lavorazione:
   ingredienti, allergeni e conservazione. Denominazione, lotto, scadenza o
   TMC, origine e prezzo arrivano dal lotto e dall’articolo. Il prezzo non si
   modifica da qui.
3. Inserisci il **peso confezione** se va stampato.
4. Solo l’admin può modificare ingredienti e allergeni. L’operatore li vede
   già compilati dalla ricetta e non li riscrive.
5. Leggi l’avviso: l’etichetta non è una certificazione legale. Ingredienti e
   allergeni vanno verificati con l’OSA prima della stampa.
6. **Genera etichetta (PDF)** scarica il PDF. **Stampa su DYMO** mette
   l’etichetta in coda per la stampante del banco.

Se la stampa fisica non esce, apri **Coda stampa** e controlla lo stato del
job. Un job in errore compare anche in Dashboard. La stampante e il programma
sul PC di banco li segue chi amministra il laboratorio.

## 6. Vendita

Apri **Vendite**. I passaggi sono tre, come in **Ingresso merce**. In alto,
**Aggiorna lotti** ricarica listino, lotti e clienti senza svuotare il
carrello né cambiare passo.

### 6.1 Intestazione

1. La **data** è quella di oggi e non si modifica.
2. Scegli il **cliente**. Per un **DDT** il cliente è obbligatorio prima di
   andare avanti. Con **Ricevuta non fiscale** puoi lasciare **Banco / cliente
   non indicato** oppure indicare un cliente.
3. Scegli il **documento**: **DDT** oppure **Ricevuta non fiscale**.
4. Premi **Continua agli articoli**.

### 6.2 Articoli

1. Cerca l’articolo per nome oppure scansionalo. Lo scanner funziona solo in
   questo passo: seleziona l’articolo e porta il focus sulla quantità.
2. Con **Solo articoli con lotto disponibile** restano gli articoli attivi che
   hanno almeno un lotto vendibile: attivo, con giacenza e non scaduto. Togli
   la spunta per vedere anche gli articoli attivi senza giacenza. Gli articoli
   disattivati non compaiono.
3. Il **lotto disponibile** preselezionato è il primo in ordine FEFO. Puoi
   sceglierne un altro. Sotto il lotto leggi la quantità disponibile e la data.
4. Inserisci **quantità / peso** con fino a tre decimali. Il **prezzo
   unitario** è quello dell’articolo e non si cambia in vendita.
5. Premi **Aggiungi al riepilogo**. Puoi aggiungere più righe; il passo non
   cambia da solo.
6. **Indietro** torna all’intestazione. **Vai al riepilogo** si attiva solo
   con almeno una riga nel carrello.

Un lotto scaduto non è vendibile. Se il TMC è superato, prima di aggiungerlo
compare la domanda «Il TMC del lotto è superato. Vuoi confermare la vendita?».

### 6.3 Riepilogo

Controlla **data**, **cliente** (o banco), **tipo documento**, **righe** e
**totale**. Ogni riga mostra articolo, lotto, quantità, prezzo e importo; con
**Rimuovi** togli una riga. Senza righe **Registra vendita** resta disattivo.

Nel riepilogo compare la dicitura: il documento **non è fiscale** e non
sostituisce lo scontrino del registratore telematico.

Premi **Registra vendita** solo quando intestazione e righe sono corrette.
La registrazione scarica i lotti e crea il documento insieme. Se la quantità
supera la giacenza, la vendita è rifiutata e le giacenze restano com’erano:
riduci la quantità o aggiorna i lotti con **Aggiorna lotti**.

Dopo una registrazione riuscita torni all’intestazione con carrello vuoto. Se
la ricevuta è stata inviata, il messaggio lo conferma. Il DDT si scarica in
PDF al momento della registrazione. Numero e righe sono quelli appena
registrati. Se il DDT o la ricevuta non sono stati generati, il messaggio
invita a riprovare da **Report**, non dallo storico in questa schermata.

## 7. Report

Dal menu laterale apri **Report**, subito dopo **Vendite**.

### 7.1 Storico DDT

La tabella elenca i DDT già registrati (documento, data, cliente, righe).
**Scarica / ristampa** rilegge lo stesso DDT: stesso numero, stesse righe,
nessun documento nuovo. Il file è un PDF `ddt_{numero}.pdf`.

### 7.2 Storico ricevute non fiscali

La tabella elenca le ricevute già registrate. Resta visibile la dicitura: il
documento non è fiscale e non sostituisce lo scontrino del registratore
telematico.

**Ristampa** rimanda la stessa ricevuta al Local Print Agent e non crea
un’altra vendita.

## 8. Risalire dal preparato al fornitore

Apri **Tracciabilità** → **Lotti**. Cerca il codice del lotto prodotto e premi
**Traccia**.

Nel dettaglio leggi quantità, lotto fornitore, origine, scadenza o TMC e,
per il lotto di ingresso, la temperatura. Poi:

1. Nella lavorazione, sotto **Lotti input consumati**, premi **Apri lotto**
   sull’ingrediente.
2. Sul lotto di ingresso, **Documento di ingresso** mostra data, numero DDT e
   fornitore.
3. **Indietro** torna al lotto da cui sei partito. **Chiudi** esce dal
   dettaglio.

**Scarica scheda PDF** produce un riepilogo con gli stessi collegamenti. Il
PDF dichiara che non è una certificazione legale. **Genealogia in avanti**
elenca le lavorazioni che hanno consumato il lotto, i preparati ottenuti e le
vendite (DDT o ricevuta, numero, data, cliente o banco, quantità).

In **Movimenti** restano ingresso, lavorazione, vendita e rettifiche, con data
e quantità.

## 9. Controlli di magazzino

**Dashboard** mostra i lotti scaduti ancora disponibili, quelli in scadenza
entro 48 ore, quelli in scadenza da 3 a 7 giorni, le giacenze a zero e i job
di stampa in errore. Il riquadro **Lookup barcode (EAN)** mostra nome,
codice, EAN e prezzo. Su tablet premi **Tastiera** solo se devi digitare il
codice a mano: lo scanner invia il codice e Invio da solo.

In **Tracciabilità** → **Lotti**, il confronto inventario somma la giacenza
teorica dei lotti dell’articolo. Il conteggio fisico mostra solo lo
scostamento e non modifica il magazzino.

Per correggere una giacenza apri il lotto e usa **Rettifica giacenza**: un
delta positivo o negativo (per esempio `-0,250`) e un motivo tra inventario,
calo, reso ed errore. La giacenza non può andare sotto zero. Non si corregge
riscrivendo la quantità del lotto.

## 10. Sul tablet

Fino allo schermo di un tablet il menu sta in alto e ingresso e vendita usano
tutta la larghezza. I campi sono abbastanza grandi da non far ingrandire la
pagina alla tastiera.

Lo scanner, collegato come tastiera, funziona in Dashboard, in ingresso e in
vendita: legge almeno 6 caratteri in rapida successione e chiude con Invio.
Una digitazione lenta seguita da Invio non è una scansione. Sul campo EAN la
tastiera resta chiusa finché non premi **Tastiera**.

## 11. Se compare un messaggio

I messaggi della console sono in italiano. I casi più frequenti:

| Messaggio o situazione | Cosa fare |
|---|---|
| Nessun fornitore abilitato | In Clienti e fornitori spunta ruolo Fornitore e **Abilitato per ingresso merce**. |
| Nessun articolo attivo in questa categoria | Controlla che l’articolo sia attivo e che la categoria sia quella selezionata. |
| Il lotto scaduto non compare | Non si lavora né si vende. Il TMC superato compare ancora, ma va confermato. |
| Disponibilità FEFO insufficiente | Riduci la quantità prevista oppure registra prima un ingresso. |
| Manca il prodotto della ricetta o un ingrediente obbligatorio | Rimetti la riga prima di registrare. |
| La vendita supera la giacenza | Riduci la quantità. La vendita non è stata registrata. |
| Prezzo non configurato | In Articoli imposta il prezzo unitario. |
| DDT senza cliente | Scegli un cliente attivo, oppure passa a ricevuta non fiscale. |
| La stampante non stampa | Controlla Coda stampa e avvisa chi gestisce il PC di banco. |
| Accesso bloccato dopo molti tentativi | Aspetta e riprova, oppure usa **Password dimenticata**. |

Lotti, DDT, ricevute e documenti di ingresso non si cancellano dalla console.
Un articolo o un’anagrafica si disattivano: non compaiono più nelle scelte
nuove, ma i documenti già registrati restano.
