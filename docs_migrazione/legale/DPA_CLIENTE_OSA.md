# Accordo sul trattamento — bozza art. 28

Bozza di Data Processing Agreement tra il laboratorio (titolare) e il
fornitore di GestLab (responsabile). Non è firmabile finché i campi
`[DA COMPLETARE]` non sono chiusi e la [CHECKLIST_LEGALE.md](CHECKLIST_LEGALE.md)
non è firmata. Va allegato al contratto SaaS dei primi piloti, che resta
manuale.

## Parti

**Titolare:** il laboratorio OSA cliente.

- [DA COMPLETARE: ragione sociale, sede, partita IVA, email]

**Responsabile:** il fornitore del servizio GestLab.

- [DA COMPLETARE: ragione sociale, sede, partita IVA, email privacy]

## 1. Oggetto

Il responsabile ospita e fa funzionare GestLab perché il titolare registri
ingressi, lotti, lavorazioni, etichette, anagrafiche e vendite interne non
fiscali. Il trattamento dura quanto il contratto e riguarda i soli dati del
tenant di quel laboratorio.

## 2. Natura, finalità e categorie

Natura: hosting, conservazione, backup, supporto e stampa tramite coda
`print_jobs` e Local Print Agent sul PC del titolare.

Finalità: eseguire le istruzioni del titolare nella console (inserimento,
lettura, rettifica, disattivazione). Nessun uso proprio per marketing o per
addestrare modelli.

Interessati: utenti della console, clienti e fornitori del laboratorio anche
se persone fisiche, dipendenti inseriti in anagrafica.

Categorie, come da schema attuale:

- anagrafiche `soggetti` (denominazione, nome, cognome, codici fiscali e
  partita IVA, indirizzo, email, telefono, PEC, codice destinatario);
- `dipendenti` (nome, cognome, email, reparto);
- documenti di ingresso, lotti, movimenti, lavorazioni, vendite e righe, che
  possono nominare il soggetto;
- payload di stampa (etichetta, DDT, ricevuta non fiscale);
- audit del tenant (email dell’utente della console, azione, entità).

Non sono previsti dati particolari dell’art. 9.

## 3. Istruzioni

Il responsabile tratta i dati del tenant solo per erogare il servizio, i
backup, la sicurezza e il supporto chiesto dal titolare. Un’istruzione
diversa va data per iscritto (email all’indirizzo del contratto). Se
un’istruzione pare illecita, il responsabile lo segnala e sospende quella
sola operazione.

Istruzioni già incorporate nel prodotto, che il titolare accetta usando il
servizio:

- ogni query di business usa il `tenant_id` del token, non un valore inviato
  dal client;
- la disattivazione di un’anagrafica non cancella i lotti e i documenti;
- lotti e documenti di tracciabilità non hanno un comando di cancellazione
  fisica;
- etichette, DDT e ricevute non sono certificazioni né documenti fiscali.

## 4. Persone autorizzate

Accedono ai dati solo chi amministra l’infrastruttura o l’assistenza, per il
tempo necessario, con obbligo di riservatezza. [DA COMPLETARE: come si
documenta l’autorizzazione interna.]

## 5. Misure

Misure già presenti nel prodotto, da non presentare come certificazione:

- password con almeno 10 caratteri, una lettera e un numero; si salva solo
  l’hash;
- segreto JWT di produzione diverso dai valori di sviluppo;
- HTTPS obbligatorio sul profilo `GESTLAB_HOSTING=managed`;
- connessione al database remoto con verifica del certificato (`DB_SSL_CA`);
- segreti da Secret Manager in produzione, non da `config.ini`;
- refresh token salvati come hash, ruotati e revocati al logout e al cambio
  password;
- limite ai tentativi di login;
- database di produzione distinto dallo staging, con backup e point-in-time
  recovery;
- log di errore verso Sentry senza dati personali di default, e solo se il
  DSN è configurato;
- token del Print Agent fuori dal repository, sul PC del titolare.

[DA COMPLETARE: misure organizzative del fornitore (accessi agli ambienti,
cifratura a riposo del database gestito, tempi di risposta a un incidente).]

## 6. Sub-responsabili

L’elenco vivo è [DPA_FORNITORI_CLOUD.md](DPA_FORNITORI_CLOUD.md). Il titolare
autorizza in generale i sub-responsabili di quell’elenco. Un nuovo
sub-responsabile si comunica prima dell’uso, con almeno [DA COMPLETARE: giorni]
di preavviso. Il titolare può opporsi per motivi di protezione dati; se
l’opposizione impedisce il servizio, ciascuna parte può recedere dal contratto
senza penali di quel solo motivo.

Il responsabile resta responsabile verso il titolare dell’operato del
sub-responsabile.

## 7. Assistenza sui diritti

Il responsabile mette a disposizione del titolare, per il suo tenant:

- lettura e rettifica già disponibili in console per anagrafiche e utenti;
- export JSON o CSV del solo tenant, eseguibile dall’admin in console, senza
  hash delle password, token di sessione o di reimpostazione e senza il token
  del Print Agent;
- disattivazione degli utenti e delle anagrafiche.

Non esegue la cancellazione fisica di lotti, movimenti e documenti. Se
l’interessato chiede la cancellazione di un dato contenuto in quei documenti,
il titolare dà un’istruzione scritta e il responsabile indica il limite
tecnico e di rintracciabilità; la risposta all’interessato resta del titolare.

## 8. Violazioni

Il responsabile avvisa il titolare senza ingiustificato ritardo, e comunque
entro [DA COMPLETARE: ore, proposta 48] da quando ne ha conferma, con la
natura della violazione, le categorie, il numero approssimativo di interessati,
le conseguenze probabili e i rimedi. La notifica al Garante e agli interessati,
quando dovuta, è del titolare.

## 9. Fine del servizio

A scelta scritta del titolare, entro [DA COMPLETARE: giorni] dalla cessazione:
restituzione in JSON o CSV dei dati del solo tenant, oppure cancellazione
degli ambienti che li contengono. I backup del database gestito scadono secondo
la retention del provider [DA COMPLETARE: giorni]. Restano le copie che la
legge obbliga a conservare, e i lotti solo se il titolare chiede di mantenerli
per la rintracciabilità.

## 10. Audit

Il titolare può chiedere, non più di una volta l’anno salvo incidente, le
informazioni necessarie a dimostrare gli obblighi dell’art. 28. [DA COMPLETARE:
se si accettano solo questionari o anche un audit in loco, e con quale preavviso.]
I rapporti dei sub-responsabili (per esempio i report AWS) si considerano
parte di questa evidenza.

## 11. Clausole di perimetro da riportare anche nel contratto SaaS

Il servizio non è un registratore telematico, non emette corrispettivi fiscali
e non invia fatture al Sistema di Interscambio. DDT e ricevuta sono documenti
interni di scarico e di consegna. L’etichetta è un riepilogo dei dati inseriti
dal titolare: non è una certificazione di conformità al Reg. (UE) 1169/2011 né
un manuale HACCP. Il titolare resta l’OSA e verifica gli obblighi alimentari
e fiscali con i propri consulenti.

## 12. Legge

[DA COMPLETARE: legge italiana e foro, allineati al contratto principale.]

Versione bozza: 21 novembre 2026.
