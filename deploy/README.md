# Deploy automatico su AWS Lightsail

Gli script in questa cartella pubblicano la console web SaaS (`saas.main:app`)
su una istanza Amazon Lightsail, seguendo la procedura descritta in
[`docs_migrazione/PUBBLICAZIONE_AWS_TEST.md`](../docs_migrazione/PUBBLICAZIONE_AWS_TEST.md).

Guida d'uso: [`docs_migrazione/PUBBLICAZIONE_AWS_AUTOMATICA.md`](../docs_migrazione/PUBBLICAZIONE_AWS_AUTOMATICA.md).

Lo script `update-server.sh` esegue il bootstrap prima del riavvio del servizio,
applicando anche gli aggiornamenti dello schema ai database esistenti.

Non committare `gestlab.env` ne' i file `.pem`.
