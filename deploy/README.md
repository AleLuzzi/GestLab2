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
