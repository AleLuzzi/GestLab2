# Deploy automatico su AWS Lightsail

Gli script in questa cartella pubblicano la console web SaaS (`saas.main:app`)
su una istanza Amazon Lightsail, seguendo la procedura descritta in
[`docs_migrazione/PUBBLICAZIONE_AWS_TEST.md`](../docs_migrazione/PUBBLICAZIONE_AWS_TEST.md).

Guida d'uso: [`docs_migrazione/PUBBLICAZIONE_AWS_AUTOMATICA.md`](../docs_migrazione/PUBBLICAZIONE_AWS_AUTOMATICA.md).

Lo script `update-server.sh` esegue il bootstrap prima del riavvio del servizio,
applicando anche gli aggiornamenti dello schema ai database esistenti.

Per MySQL/RDS remoto in produzione, impostare `DB_SSL_CA` in
`gestlab.env` al percorso del bundle CA PEM del provider. La connessione
verifica sia il certificato sia l'identità del server e rifiuta l'avvio se la
CA non è configurata. Una connessione a `localhost` o a un IP loopback (come
la MariaDB locale installata dallo script Lightsail) non richiede TLS.

Il pool MySQL è condiviso dal processo applicativo e dimensionato tramite
`DB_POOL_SIZE` (default 10, massimo 32). Ogni processo applicativo ha il proprio
pool; `close()` restituisce la connessione al pool invece di chiuderla.

Non committare `gestlab.env` ne' i file `.pem`.

## Produzione e staging gestiti

Il Lightsail di test resta il percorso di `gestlab.env`: database sulla stessa
istanza, senza `GESTLAB_HOSTING`. Il profilo vendibile è un altro:

- due server applicativi, con HTTPS sul proprio dominio (`certbot --nginx`,
  già previsto da `setup-server.sh --https`); lo staging usa un dominio che
  contiene `staging`;
- due database gestiti distinti, `gestlab_production` e `gestlab_staging`,
  ciascuno con backup automatici e point-in-time recovery; non due schemi
  sulla stessa istanza, perché il ripristino puntuale riguarda il server;
- password del database e `JWT_SECRET` in AWS Secrets Manager (o equivalente),
  iniettati nell'ambiente del servizio. `GESTLAB_SECRET_SOURCE=secrets-manager`
  dichiara questa origine;
- `DB_SSL_CA` punta al bundle CA del provider.

I modelli sono `gestlab.production.env.example` e
`gestlab.staging.env.example`. Con `GESTLAB_HOSTING=managed` il processo non
parte se l'URL non è HTTPS, se il database è locale o senza TLS, se i nomi non
sono quelli previsti, se manca la dichiarazione di point-in-time recovery o se
i due ambienti indicano lo stesso server database.

`/health` risponde 200 solo se il database esegue `SELECT 1`; altrimenti
risponde 503 con `status` `degraded`. Lo script di setup installa un timer
systemd che richiede l'endpoint ogni minuto: un fallimento resta nel journal
come servizio `gestlab-health`. Le richieste diverse dal health check riuscito
sono scritte in `logs/gestlab-saas.log` con metodo, percorso, stato e durata.
Un errore non gestito aggiunge un riferimento assistenza e, se `SENTRY_DSN` è
valorizzato e `sentry-sdk` è installato, lo invia a Sentry senza dati personali
di default.
