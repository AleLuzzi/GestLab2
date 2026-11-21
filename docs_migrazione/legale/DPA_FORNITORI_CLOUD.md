# Sub-responsabili e DPA di infrastruttura

Il fornitore cloud non firma un testo scritto da GestLab: si accetta il suo
DPA (art. 28) dall’account del servizio. Questo foglio elenca chi tratta dati
per davvero, in base al codice e a `deploy/gestlab.production.env.example`, e
cosa va verificato prima del primo canone.

Stato al 21 novembre 2026: le istanze AWS di produzione non sono create. I
nomi sotto sono il profilo previsto, non un contratto già accettato.

## 1. Registro sub-responsabili

Compilare una riga solo quando il servizio è acceso in produzione.

| Servizio | Chi | Dati | Dove | Stato |
|---|---|---|---|---|
| Database MySQL o MariaDB gestito, backup con point-in-time recovery | [DA COMPLETARE: AWS RDS o equivalente, account, regione] | Tutti i dati del tenant e degli account | [DA COMPLETARE: regione SEE] | Non creato |
| Secret Manager | [DA COMPLETARE: stesso account AWS] | Segreti dell’applicazione, non i dati dei lotti | [DA COMPLETARE: regione] | Non creato |
| Hosting HTTPS dell’API e della console | [DA COMPLETARE: istanza o load balancer, regione] | Traffico in transito | [DA COMPLETARE: regione] | Il Lightsail di test non è l’ambiente vendibile |
| SMTP del reset password | [DA COMPLETARE: fornitore] | Email dell’utente e collegamento monouso | [DA COMPLETARE: paese] | Facoltativo: senza `SMTP_HOST` e `SMTP_FROM` il reset risponde 503 |
| Error tracking | Sentry (Functional Software), solo con `SENTRY_DSN` | Eccezioni; il codice non invia dati personali di default | [DA COMPLETARE: regione del progetto Sentry] | Spento se il DSN è vuoto |

Il PC di banco e il Local Print Agent non sono sub-responsabili: sono
apparecchi del laboratorio. Il token sta in `%ProgramData%\GestLab\print-agent.env`.

## 2. Adempimenti verso AWS (o il provider scelto)

Prima di caricare dati di un pilota pagante:

1. Aprire l’account a nome di [DA COMPLETARE: ragione sociale del fornitore SaaS].
2. Accettare il DPA art. 28 del provider (per AWS: AWS Data Processing Addendum)
   e conservare la prova (data, account, versione).
3. Scegliere una regione nello SEE per database, backup, segreti e calcolo.
   Annotarla nella tabella sopra. Se una regione esce dallo SEE, fermarsi e
   far indicare al professionista la garanzia (clausole tipo o decisione di
   adeguatezza) prima del go-live.
4. Attivare la cifratura a riposo del database gestito e il TLS verso MySQL,
   già richiesto dal profilo `GESTLAB_HOSTING=managed` tramite `DB_SSL_CA`.
5. Limitare le utenze IAM a chi amministra la produzione. Lo staging usa un
   server database diverso (`GESTLAB_PEER_DB_HOST`).
6. Verificare che i backup automatici e il point-in-time recovery siano accesi
   e che la retention sia scritta nel DPA con il laboratorio.
7. Non usare l’istanza Lightsail di test come produzione: non ha il profilo
   `GESTLAB_HOSTING=managed`.

## 3. Adempimenti verso SMTP e Sentry

SMTP: accettare il DPA del fornitore prima di impostare `SMTP_FROM`. Il
messaggio contiene l’indirizzo dell’utente e un collegamento con il token in
chiaro; nel database resta solo l’hash. Non mettere altri dati personali nel
template.

Sentry: lasciare il DSN vuoto finché non si accetta il DPA Sentry e non si
fissa la regione. Il comportamento attuale, coperto da `tests/test_osservabilita.py`,
è di non allegare dati personali di default. Non cambiare quella configurazione
senza aggiornare l’informativa.

## 4. Cosa non inventare in questo foglio

Non risulta un DPA già firmato, una regione scelta, un nome di società del
fornitore SaaS né un’entità AWS collegata a questo repository. Quei dati si
scrivono qui quando esistono, non prima.
