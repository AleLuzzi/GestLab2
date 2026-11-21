# Informativa privacy — bozza

Bozza art. 13 del Regolamento (UE) 2016/679. Non pubblicare finché il
professionista non ha compilato i campi `[DA COMPLETARE]` e firmato
[CHECKLIST_LEGALE.md](CHECKLIST_LEGALE.md).

## 1. Titolare del trattamento di questo testo

Per i dati dell’account del laboratorio (contratto SaaS, utenti della console,
log di sicurezza del servizio) il titolare è:

- [DA COMPLETARE: ragione sociale]
- [DA COMPLETARE: sede legale]
- [DA COMPLETARE: partita IVA]
- [DA COMPLETARE: email per le richieste privacy]

[DA COMPLETARE: se è stato designato un DPO, indicarne i contatti; altrimenti
dichiarare che non è designato e perché.]

I dati che il laboratorio inserisce sui propri clienti, fornitori e dipendenti
hanno come titolare il laboratorio. Per quelli il fornitore SaaS è responsabile
del trattamento: vedi [DPA_CLIENTE_OSA.md](DPA_CLIENTE_OSA.md). Le richieste
di quei interessati si rivolgono al laboratorio.

## 2. Dati trattati dal titolare del servizio

Ricavati dalle tabelle e dai log attuali.

| Dato | Dove | Note |
|---|---|---|
| Nome del tenant, ragione sociale OSA, sede, laboratorio, partita IVA | `tenant` | Dati del cliente del contratto |
| Email, ruolo (`admin` o `operatore`), stato attivo, data di creazione | `utenti` | L’email è l’identificativo di accesso |
| Hash della password | `utenti.password_hash` | La password in chiaro non è salvata |
| Hash del token di reset, scadenza (60 minuti), data di uso | `password_reset` | Il token in chiaro viaggia solo nel collegamento email |
| Hash del refresh token, famiglia, scadenza, data di revoca | `refresh_token` | Il token in chiaro non è salvato |
| Email dell’utente, azione (`CANCELLAZIONE` o `RETTIFICA`), entità e dettaglio | `audit_log` | Scritta nella stessa transazione dell’operazione |
| Metodo HTTP, percorso, stato, durata | `logs/gestlab-saas.log` | Il health check riuscito non è registrato |
| Email e indirizzo IP sui tentativi di login limitati | log dell’applicazione | Il contatore (10 errori per email, 50 per IP in 15 minuti) resta in memoria di processo e non è una tabella |

Non sono trattati, nel perimetro attuale: dati di pagamento (il canone dei
primi piloti è manuale, fuori dall’applicazione), documenti di identità,
dati sanitari, dati di minori raccolti in quanto tali.

## 3. Dati trattati per conto del laboratorio

Il laboratorio li inserisce e ne resta titolare.

| Dato | Dove |
|---|---|
| Clienti e fornitori: denominazione, nome, cognome, tipo, partita IVA, codice fiscale, indirizzo, email, telefono, PEC, codice destinatario | `soggetti` |
| Dipendenti del laboratorio: nome, cognome, email, reparto | `dipendenti` |
| Lotti, DDT, lavorazioni, vendite, payload di stampa | tabelle di tracciabilità e `print_jobs` |

Se il cliente o il fornitore è una persona fisica o una ditta individuale, nome,
codice fiscale e recapiti sono dati personali. I lotti e i documenti di
tracciabilità non si cancellano fisicamente dall’applicazione: la scelta di
conservazione è del laboratorio, nei limiti di legge sulla rintracciabilità.

## 4. Finalità e basi giuridiche proposte

Il professionista conferma o sostituisce ogni riga.

| Finalità | Base proposta | Dati |
|---|---|---|
| Erogare il servizio, creare il tenant e gli utenti, reimpostare la password | Esecuzione del contratto, art. 6.1.b | Account, hash dei token di reset |
| Impedire accessi abusivi e revocare le sessioni | Legittimo interesse alla sicurezza del servizio, art. 6.1.f, [DA COMPLETARE: esito del bilanciamento] | Refresh token, contatori di login, log tecnici, audit |
| Addebitare il canone dei primi piloti | Contratto, art. 6.1.b; obblighi contabili, art. 6.1.c | Anagrafica del cliente del contratto, tenuta fuori dall’applicazione |
| Conservare la tracciabilità alimentare inserita dal laboratorio | Istruzioni del titolare (il laboratorio), che può fondarsi sull’obbligo del Reg. (CE) 178/2002 | Lotti e documenti, come responsabile |

Non c’è profilazione né marketing verso gli utenti della console.

## 5. Destinatari e sub-responsabili

Elenco operativo in [DPA_FORNITORI_CLOUD.md](DPA_FORNITORI_CLOUD.md). In sintesi:

- infrastruttura gestita (database, segreti, HTTPS), oggi prevista su AWS, regione [DA COMPLETARE];
- server SMTP che invia solo il collegamento di reset password, fornitore [DA COMPLETARE];
- Sentry, solo se `SENTRY_DSN` è configurato: le eccezioni partono senza dati personali di default;
- il PC di banco del laboratorio, tramite Local Print Agent: i job di stampa tornano sull’apparecchio del cliente, non a un altro titolare.

Nessun altro destinatario è previsto dal codice.

## 6. Trasferimenti

[DA COMPLETARE: se database, backup e segreti restano nello SEE, scriverlo con la regione. Se Sentry o l’SMTP trattano fuori dallo SEE, indicare la garanzia (clausole tipo o decisione di adeguatezza) dopo aver letto il DPA di quel fornitore.]

## 7. Conservazione proposta

Da confermare. Non sono termini già decisi nel software, salvo dove indicato.

| Dato | Termine proposto |
|---|---|
| Account e anagrafica del cliente del contratto | Durata del contratto e, dopo, [DA COMPLETARE] per obblighi contabili |
| Token di reset | 60 minuti, poi inutilizzabile; la riga resta finché [DA COMPLETARE: politica di pulizia] |
| Refresh token | Fino a scadenza o revoca (logout, riuso, cambio password) |
| Log operativo | [DA COMPLETARE: proposta 90 giorni] |
| Audit di cancellazioni e rettifiche | Per la vita del tenant, salvo diverso termine indicato dal professionista |
| Dati di tracciabilità del laboratorio | Secondo le istruzioni del laboratorio e gli obblighi di rintracciabilità; l’applicazione non offre la cancellazione fisica di lotti e documenti |

## 8. Diritti

L’utente della console può chiedere al titolare del servizio accesso,
rettifica, limitazione e opposizione nei casi previsti, e reclamo al Garante
per la protezione dei dati personali (www.garanteprivacy.it).

La cancellazione dell’account è possibile quando non resta un obbligo di
conservazione. I lotti e i documenti del laboratorio non si rimuovono
fisicamente: la richiesta dell’interessato (cliente o dipendente del
laboratorio) va fatta al laboratorio.

L’admin del laboratorio può scaricare da console i dati del proprio tenant
in JSON o in CSV. L’archivio non include gli hash delle password, i token di
reimpostazione, i refresh token e il token del Print Agent. Una richiesta
dell’interessato che non sia questo export si invia a [DA COMPLETARE: email];
se riguarda un cliente o un dipendente del laboratorio, la risposta resta del
laboratorio. L’informativa non va pubblicata prima della firma della checklist.

## 9. Obbligatorietà

Email e password sono necessarie per l’accesso. I dati OSA sono necessari per
etichette e DDT. Il rifiuto impedisce di erogare il servizio, non produce
altri effetti automatizzati.

## 10. Modifiche

Versione bozza: 21 novembre 2026. La data di pubblicazione reale si scrive
qui solo dopo la firma della checklist.
