# Checklist catalogo cliccabile da disegno

Checklist per completare il catalogo `macelleria` e scegliere il taglio sul profilo dell'animale, in Ingresso merce. Le decisioni sotto sono chiuse: non vanno riaperte durante la realizzazione.

## Come usarla

- Seguire le fasi nell'ordine: prima l'anagrafica, poi i disegni, poi la schermata, infine la verifica.
- Spuntare una voce solo dopo aver verificato il criterio indicato sulla voce stessa.
- Il documento descrive il lavoro. Non sostituisce `TEMPLATE_MACELLERIA` né la pagina di ingresso finché le voci non sono spuntate.

## Decisioni chiuse

- La mappa sostituisce l'elenco pulsanti in Ingresso merce (`web/js/features/ingresso-merce.js`, contenitore `#ingress-articoli`), dopo i pulsanti di categoria già generati dal campo `categoria`.
- Il clic risolve un codice articolo stabile sull'anagrafica del tenant e seleziona lo stesso `articolo_id` di oggi. Quantità, lotto fornitore, origine, scadenza o TMC, temperatura e conferma ingresso restano quelli attuali.
- Lo scanner continua a selezionare l'articolo dal codice a barre, anche quando a video c'è il disegno.
- Specie in mappa: Bovino, Vitello, Suino. Condimento e Preparato restano pulsanti di testo.
- Suino e vitello: un profilo. Bovino: due profili, quarto anteriore e quarto posteriore.
- Fuori dalle zone, come pulsanti accanto al disegno: mezzena intera, filetto, lardo. Ossobuco e braciole non sono articoli distinti: sono geretto e carrè o lonza affettati.
- Una zona il cui codice non ha un articolo attivo nel tenant è disattivata e non si clicca.
- Il catalogo `macelleria` si completa in `saas/services/onboarding.py` (`TEMPLATE_MACELLERIA`). I tenant già creati non ricevono gli articoli in automatico: le voci mancanti si aggiungono da Configurazioni, Articoli.
- I tagli sono in kg e utilizzabili come input di lavorazione. Sale e i tre preparati già presenti non cambiano ruolo.

## 1. Catalogo

Anagrafica di partenza, senza prezzi, EAN, lotti né giacenze. Il template passa da 9 a 61 articoli: 28 bovini, 13 suini, 16 di vitello, più sale, salsicce fresche, hamburger di bovino e arrosto di vitello.

- [x] Sostituire in `TEMPLATE_MACELLERIA` la voce `BOV-MUSCOLO` / «Muscolo bovino» con `BOV-GER-ANT` / «Geretto anteriore bovino», categoria `Bovino`, unità `kg`, utilizzabile come input. Non lasciare entrambi i codici.
- [x] Tenere `SUI-PANCIA` e rinominare l'articolo in «Pancetta di suino». Stessa regola per `SUI-SPALLA` («Spalla di suino») e `SUI-COSCIA` («Coscia di suino»).
- [x] Inserire i tagli di bovino della tabella sotto, tutti categoria `Bovino`, unità `kg`, utilizzabili come input.
- [x] Inserire i tagli di suino della tabella sotto, tutti categoria `Suino`, unità `kg`, utilizzabili come input.
- [x] Inserire i tagli di vitello della tabella sotto, tutti categoria `Vitello`, unità `kg`, utilizzabili come input.
- [x] Lasciare invariati `COND-SALE` (Sale, Condimento), `PREP-SALSICCIA`, `PREP-HAMBURGER` e `PREP-ARROSTO`.
- [x] Non inserire ossobuco, braciole, filetto di vitello, fesa di spalla suina né muscolo di spalla suina: sono lo stesso pezzo di un articolo già in elenco, oppure un taglio che il banco aggiunge dopo da Configurazioni.
- [x] Verificare che `tests/test_onboarding.py` passi con il template nuovo. Il test del catalogo macelleria confronta la tupla intera e il conteggio con `len(TEMPLATE_MACELLERIA)`, non con il numero 9.
- [x] Aggiornare `docs_migrazione/CREAZIONE_NUOVO_TENANT.md`: elenco delle voci, esempio di output `Catalogo: macelleria (61 articoli)` e il passo di ingresso, che cita ancora solo la pancia di suino. Il catalogo `vuoto` resta senza articoli.

### Bovino

| Codice | Nome | Sul disegno |
| --- | --- | --- |
| BOV-MEZZENA | Mezzena bovina | Pulsante, non una zona |
| BOV-COLLO | Collo bovino | Quarto anteriore |
| BOV-REALE | Reale bovino | Quarto anteriore |
| BOV-SOTTOSPAL | Sottospalla bovina | Quarto anteriore |
| BOV-FESONE | Fesone di spalla bovino | Quarto anteriore |
| BOV-CAPPELLO | Cappello del prete bovino | Quarto anteriore |
| BOV-FUSELLO | Girello di spalla bovino | Quarto anteriore |
| BOV-TRAVERSIN | Copertina di sotto bovina | Quarto anteriore |
| BOV-BRIONE | Brione bovino | Quarto anteriore |
| BOV-PETTO | Petto bovino | Quarto anteriore |
| BOV-FIOCCO | Fiocco bovino | Quarto anteriore |
| BOV-BIANCO | Biancostato bovino | Quarto anteriore |
| BOV-PANCIA | Pancia bovina | Quarto anteriore |
| BOV-SCALFO | Scalfo bovino | Quarto anteriore |
| BOV-GER-ANT | Geretto anteriore bovino | Quarto anteriore |
| BOV-COSTATA | Costata bovina | Quarto posteriore |
| BOV-CONTROF | Controfiletto bovino | Quarto posteriore |
| BOV-FILETTO | Filetto bovino | Pulsante, non una zona |
| BOV-SCAMONE | Scamone bovino | Quarto posteriore |
| BOV-FIANCH | Fianchetto bovino | Quarto posteriore |
| BOV-NOCE | Noce bovina | Quarto posteriore |
| BOV-FESA | Fesa bovina | Quarto posteriore |
| BOV-SOTTOF | Sottofesa bovina | Quarto posteriore |
| BOV-CODONE | Codone bovino | Quarto posteriore |
| BOV-GIRELLO | Girello bovino | Quarto posteriore |
| BOV-PESCE | Pesce bovino | Quarto posteriore |
| BOV-GER-POST | Geretto posteriore bovino | Quarto posteriore |
| BOV-CODA | Coda bovina | Quarto posteriore |

### Suino

| Codice | Nome | Sul disegno |
| --- | --- | --- |
| SUI-MEZZENA | Mezzena di suino | Pulsante, non una zona |
| SUI-COPPA | Coppa di suino | Zona |
| SUI-LONZA | Lonza di suino | Zona |
| SUI-FILETTO | Filetto di suino | Pulsante, non una zona |
| SUI-COSTINE | Costine di suino | Zona |
| SUI-SPALLA | Spalla di suino | Zona |
| SUI-PANCIA | Pancetta di suino | Zona |
| SUI-GUANCIA | Guanciale di suino | Zona |
| SUI-LARDO | Lardo di suino | Pulsante, non una zona |
| SUI-COSCIA | Coscia di suino | Zona |
| SUI-STINCO | Stinco di suino | Zona |
| SUI-PIEDE | Piedino di suino | Zona |
| SUI-CODA | Coda di suino | Zona |

### Vitello

| Codice | Nome | Sul disegno |
| --- | --- | --- |
| VIT-MEZZENA | Mezzena di vitello | Pulsante, non una zona |
| VIT-GER-POST | Garretto posteriore di vitello | Zona |
| VIT-PESCE | Pesce di vitello | Zona |
| VIT-FESA | Fesa di vitello | Zona |
| VIT-SCAMONE | Scamone di vitello | Zona |
| VIT-NOCE | Noce di vitello | Zona |
| VIT-SOTTOF | Sottofesa di vitello | Zona |
| VIT-GIRELLO | Girello di vitello | Zona |
| VIT-LOMBO | Lombo di vitello | Zona |
| VIT-CARRE | Carrè di vitello | Zona |
| VIT-COPPA | Coppa di vitello | Zona |
| VIT-PANCIA | Pancia di vitello | Zona |
| VIT-PETTO | Petto di vitello | Zona |
| VIT-COLLO | Collo di vitello | Zona |
| VIT-SPALLA | Spalla di vitello | Zona |
| VIT-GER-ANT | Garretto anteriore di vitello | Zona |

## 2. Disegni

SVG di profilo, nel frontend, senza librerie. Le zone sono forme del disegno, non un'immagine con coordinate fisse. Ogni zona porta `data-codice` uguale al codice della tabella.

- [x] Disegnare il profilo del suino con le dieci zone della tabella (coppa, lonza, costine, spalla, pancetta, coscia, guanciale, stinco, piedino, coda). Modulo `web/js/catalogo-disegno/profilo-suino.js`, stili base in `web/app.css`; verifica in `tests/test_catalogo_disegno.py`.
- [x] Disegnare il profilo del vitello con le quindici zone della tabella, mezzena esclusa. Modulo `web/js/catalogo-disegno/profilo-vitello.js`; verifica in `tests/test_catalogo_disegno.py`.
- [x] Disegnare due profili di bovino: quarto anteriore (quattordici zone) e quarto posteriore (dodici zone). Filetto e mezzena restano fuori da entrambi. Modulo `web/js/catalogo-disegno/profilo-bovino.js` (`creaProfiloBovinoAnteriore`, `creaProfiloBovinoPosteriore`); verifica in `tests/test_catalogo_disegno.py`.
- [x] Rendere ogni zona abbastanza larga per un dito sul banco. Se due zone si sovrappongono, si allarga l'area cliccabile senza fondere i codici.
- [x] Mostrare il nome dell'articolo al passaggio del puntatore, al focus da tastiera e nel testo di conferma dopo il clic.
- [x] Dare a ogni zona un nome accessibile (il nome articolo) e permettere di raggiungerla e attivarla da tastiera, come i pulsanti articolo attuali.

## 3. Ingresso merce

Punto di innesto: `renderArticoli` in `web/js/features/ingresso-merce.js` e il passo 2 in `web/index.html`. Gli stili stanno in `web/app.css`, accanto a `.categoria-buttons` e `.articoli-list`.

- [x] Per Bovino, Vitello e Suino, al posto della griglia `.articoli-list` mostrare il disegno della specie e la riga di pulsanti dei pezzi fuori profilo.
- [x] Per il bovino mostrare due comandi, «Quarto anteriore» e «Quarto posteriore», e un solo profilo alla volta.
- [x] Al clic su una zona attiva selezionare l'articolo del tenant con quel `codice`, con lo stesso comportamento di oggi: una sola selezione, un secondo clic sulla stessa zona la toglie, `aria-pressed` aggiornato.
- [x] Evidenziare la zona scelta e scrivere nel feedback il nome articolo, come fa oggi «Selezionato: …».
- [x] Accanto al disegno, pulsanti per gli articoli marcati «Pulsante» nella tabella della specie corrente: mezzena; filetto per bovino e suino; lardo solo per il suino. Il vitello ha solo la mezzena.
- [x] Se il codice della zona non corrisponde a un articolo attivo, disegnare la zona disattivata: niente selezione, niente `articolo_id`.
- [x] Per Condimento, Preparato e qualunque altra categoria lasciare l'elenco di pulsanti testuali.
- [x] Tenere lo scanner su `#ingress-articoli`: la lettura del codice a barre seleziona l'articolo, porta la categoria giusta e, se la specie ha il disegno, evidenzia la zona o il pulsante con quel codice.
- [x] Non cambiare il payload di conferma: la riga invia ancora `articolo_id`, quantità e metadati lotto.

## 4. Verifica

- [ ] Con un tenant `macelleria` nuovo, in Ingresso merce scegliere Suino, cliccare la lonza, inserire una quantità e aggiungere la riga: il riepilogo mostra «Lonza di suino» e la conferma crea il lotto su quell'articolo.
- [ ] Ripetere con Vitello (un taglio di zona, per esempio il carrè) e con Bovino su entrambi i quarti (un taglio anteriore e uno posteriore).
- [ ] Verificare i pulsanti fuori profilo: mezzena bovina, filetto bovino, filetto di suino e lardo di suino finiscono nel riepilogo con il nome dell'articolo.
- [ ] Disattivare da Configurazioni un taglio presente sul disegno, ricaricare l'ingresso e verificare che la zona sia spenta e che il clic non aggiunga righe.
- [ ] Verificare che Condimento e Preparato mostrino ancora i pulsanti Sale, Salsicce fresche, Hamburger di bovino e Arrosto di vitello, senza disegno.
- [ ] Verificare la regressione del passo 1 e del passo 3: fornitore obbligatorio, quantità, azzera movimento e conferma. Un ingresso completo continua a creare documento e lotto come prima del disegno.
- [ ] Aggiornare in `docs_migrazione/MANUALE_UTENTE.md` solo il passo articoli dell'ingresso (§ 3): categoria, poi taglio sul disegno per bovino, vitello e suino, pulsanti per mezzena, filetto e lardo, elenco testuale per le altre categorie, scanner invariato.

## Fuori da questa checklist

- Quinto quarto (fegato, lingua, guancia bovina, cuore, rognone, trippa, animelle): non fa parte della mezzena e non ha zone sul profilo.
- Salumi stagionati (prosciutto, coppa stagionata, pancetta tesa): restano preparati, da aggiungere in anagrafica se il laboratorio li vende.
- La stessa mappa in lavorazione e in vendita: si riusa dopo che l'ingresso è verificato, non in questo giro.
- Nessun aggiornamento automatico dei tenant già creati con il template da 9 articoli.
