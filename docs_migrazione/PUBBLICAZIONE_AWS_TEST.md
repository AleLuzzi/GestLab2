# Pubblicazione di GestLab2 su AWS per test

Guida passo passo per pubblicare la console web SaaS di GestLab2 su AWS con il
costo minimo compatibile con il codice attuale.

> Questa guida riguarda `saas.main:app` e la console web nella cartella `web/`.
> La UI desktop Kivy (`main.py`) non viene eseguita sul server web.

## 1. Scelta dell'architettura

Per questo test usare:

- una sola istanza **Amazon Lightsail Linux**;
- Ubuntu LTS;
- FastAPI/Uvicorn per il backend;
- MariaDB/MySQL sulla stessa istanza;
- Nginx come reverse proxy;
- Certbot per HTTPS, quando sarà disponibile un dominio.

Questa scelta è la più economica compatibile con il progetto attuale perché:

- `core/db.py` usa `mysql-connector-python` e query SQL MySQL;
- i repository aprono connessioni MySQL direttamente;
- `saas.main:app` serve insieme API e frontend statico;
- `saas.print_agent` richiede un backend sempre raggiungibile per il polling.

Lambda e database non sono alternative: Lambda esegue codice, mentre un database
conserva i dati. Lambda + DynamoDB potrebbe ridurre il costo a consumo, ma
richiederebbe riscrivere `core/db.py`, i repository e le query SQL. Lambda + RDS
conserverebbe MySQL, ma per un test aggiungerebbe costi, rete privata e
complessità. Questi percorsi sono descritti nella sezione 14.

I prezzi Lightsail, il Free Tier e le promozioni dipendono da regione, account e
data. Verificare sempre il prezzo mostrato nella console AWS prima di creare
l'istanza e attivare un avviso di budget.

## 2. Prerequisiti

Servono:

- account AWS attivo;
- accesso alla console AWS con permessi per Lightsail, IAM e Billing;
- PowerShell sul PC Windows;
- Git installato, se il progetto è in un repository;
- un dominio DNS, solo per configurare HTTPS pubblico;
- un backup del database locale.

Non servono Docker o Lambda per questo percorso.

### 2.1 Configurare AWS CLI (opzionale)

Installare AWS CLI v2 seguendo la documentazione ufficiale AWS, quindi in
PowerShell verificare:

```powershell
aws --version
aws configure
```

Inserire access key, secret key, regione preferita e formato `json` solo se si
intende usare la CLI. Non inserire chiavi AWS nel repository o nei file del
progetto.

### 2.2 Impostare un avviso di costo

Nella console AWS:

1. Aprire **Billing and Cost Management**.
2. Creare un budget mensile con una soglia bassa adatta al test.
3. Configurare almeno una notifica email.
4. Controllare periodicamente **Cost Explorer**.

L'avviso non blocca automaticamente le risorse e non sostituisce il teardown.

## 3. Preparare il progetto localmente

Prima del deploy, lavorare nella root del progetto:

```powershell
Set-Location C:\Users\Ale\GestLab2\GestLab2
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python tests\test_saas_e2e.py
```

Il test e2e usa il database configurato in `core/db.py` e ricrea alcune tabelle
SaaS. Eseguirlo soltanto su un database di test, mai sul database con dati reali.

### 3.1 Non pubblicare i segreti locali

Il file `config.ini` contiene password e token in chiaro. Non copiarlo sul server
e non inserirlo in Git. Prima del deploy:

1. revocare o ruotare eventuali token già esposti;
2. cambiare la password del database locale se è stata condivisa;
3. verificare che `.env`, backup e file di configurazione con segreti siano in
   `.gitignore`;
4. creare segreti nuovi per l'ambiente AWS.

Il modulo `core/env.py` dà precedenza alle variabili d'ambiente rispetto a
`config.ini`, quindi sul server verranno usate le variabili AWS.

Variabili necessarie:

```text
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=gestlab
DB_USER=gestlab_app
DB_PWD=<password-lunga-del-db>
JWT_SECRET=<segreto-casuale-lungo>
GESTLAB_ADMIN_EMAIL=<email-admin-di-test>
GESTLAB_ADMIN_PASSWORD=<password-admin-di-test>
GESTLAB_TENANT_NOME=Laboratorio Test AWS
```

Generare un segreto JWT casuale, per esempio da PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 4. Creare l'istanza Lightsail

Nella console AWS:

1. Aprire **Lightsail**.
2. Selezionare la regione più vicina agli utenti di test.
3. Selezionare **Create instance**.
4. Piattaforma: **Linux/Unix**.
5. Blueprint: **Ubuntu LTS** disponibile nella regione scelta.
6. Selezionare il piano più piccolo disponibile che rispetti il budget.
7. Dare all'istanza un nome, per esempio `gestlab-test`.
8. Creare o selezionare una chiave SSH.
9. Creare l'istanza.

Dopo la creazione:

1. assegnare un **Static IP** e collegarlo all'istanza;
2. annotare l'indirizzo IP pubblico;
3. nella scheda **Networking** lasciare aperta la porta TCP `22` solo per la
   manutenzione e aprire `80` e `443` per il sito;
4. non aprire la porta `3306` a Internet.

Per il test iniziale si può usare direttamente l'IP su HTTP. Per HTTPS servirà
un dominio che punti allo Static IP.

## 5. Collegarsi via SSH

Dalla console Lightsail usare **Connect using SSH**, oppure da PowerShell:

```powershell
ssh ubuntu@<IP_STATICO>
```

Se viene usata una chiave scaricata da Lightsail:

```powershell
ssh -i C:\percorso\lightsail-key.pem ubuntu@<IP_STATICO>
```

I comandi delle sezioni successive sono da eseguire nella shell Ubuntu
sull'istanza, salvo diversa indicazione.

## 6. Installare il sistema e i componenti

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx mariadb-server
sudo systemctl enable --now mariadb
sudo systemctl enable --now nginx
```

Verificare le versioni:

```bash
python3 --version
mariadb --version
nginx -v
```

## 7. Creare database e utente applicativo

Avviare la console MariaDB:

```bash
sudo mariadb
```

Eseguire il seguente SQL, sostituendo la password con una nuova password lunga:

```sql
CREATE DATABASE gestlab CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'gestlab_app'@'127.0.0.1' IDENTIFIED BY '<PASSWORD_DB_NUOVA>';
GRANT ALL PRIVILEGES ON gestlab.* TO 'gestlab_app'@'127.0.0.1';
FLUSH PRIVILEGES;
EXIT;
```

L'utente applicativo è limitato al database GestLab. Non usare `root` nel file
di configurazione dell'applicazione.

Verificare la connessione:

```bash
mariadb -h 127.0.0.1 -u gestlab_app -p gestlab
```

## 8. Importare lo schema e creare il database

### 8.1 Test con database vuoto (nuovo flusso unificato)

A partire da 2026-09-11, lo schema è consolidato in un unico file `saas/init_database.sql`.
Copiare il progetto sul server, quindi dalla root del progetto eseguire:

```bash
cd /opt/gestlab/app
. .venv/bin/activate
python3 -m saas.bootstrap
```

Questo comando:
- Legge il file unificato `saas/init_database.sql`
- Crea tutte le tabelle di business (dipendenti, fornitori, prodotti, ecc.) con supporto multi-tenant
- Crea le tabelle SaaS (tenant, utenti, dispositivi_stampa, print_jobs)
- Crea un tenant e utente admin iniziale

Il bootstrap è idempotente: se le tabelle o l'utente esistono già, il comando
non le ricrea e completa comunque con successo.

Verificare che lo schema sia stato creato:

```bash
mariadb -h 127.0.0.1 -u gestlab_app -p gestlab \
  -e "SHOW TABLES;"
```

Dovrai vedere 19 tabelle. Per verificare l'admin creato:

```bash
mariadb -h 127.0.0.1 -u gestlab_app -p gestlab \
  -e "SELECT id, email, ruolo FROM utenti;"
```

### 8.2 Migrazione di dati esistenti dal database locale

Se hai dati locali da migrare:

1. **Fare un backup del database locale:**
   ```bash
   # Da PowerShell sul PC locale
   mysqldump -h localhost -u root -p data > gestlab_backup.sql
   ```

2. **Importare il backup su AWS:**
   ```bash
   # Sull'istanza AWS
   cd /tmp
   scp -i <chiave>.pem ubuntu@<IP_LOCALE>:gestlab_backup.sql .
   mariadb -h 127.0.0.1 -u gestlab_app -p gestlab < gestlab_backup.sql
   ```

3. **Eseguire il bootstrap per aggiungere le tabelle SaaS:**
   ```bash
   cd /opt/gestlab/app
   . .venv/bin/activate
   python -m saas.bootstrap
   ```

4. **Mappare i dati migrati a un tenant:**
   - Il bootstrap crea un tenant con ID = 2 per i dati nuovi
   - I dati importati dal vecchio database potrebbero avere `tenant_id = NULL`
   - Eseguire un UPDATE per associarli al tenant corretto:

   ```bash
   mariadb -h 127.0.0.1 -u gestlab_app -p gestlab << 'EOF'
   UPDATE dipendenti SET tenant_id = 2 WHERE tenant_id IS NULL;
   UPDATE fornitori SET tenant_id = 2 WHERE tenant_id IS NULL;
   UPDATE prodotti SET tenant_id = 2 WHERE tenant_id IS NULL;
   UPDATE reparti SET tenant_id = 2 WHERE tenant_id IS NULL;
   UPDATE merceologie SET tenant_id = 2 WHERE tenant_id IS NULL;
   UPDATE tagli SET tenant_id = 2 WHERE tenant_id IS NULL;
   UPDATE ingresso_merce SET tenant_id = 2 WHERE tenant_id IS NULL;
   UPDATE progressivi SET tenant_id = 2 WHERE tenant_id IS NULL;
   EOF
   ```

5. **Verificare l'isolamento multi-tenant:**
   - Creare un secondo tenant dall'API
   - Creare un secondo utente in quel tenant
   - Verificare che i dati restino isolati per tenant
   - Non esporre i dati di un tenant all'altro

## 9. Copiare il codice sul server

### 9.1 Da repository Git

```bash
sudo mkdir -p /opt/gestlab
sudo chown ubuntu:ubuntu /opt/gestlab
cd /opt/gestlab
git clone <URL_DEL_REPOSITORY> app
cd /opt/gestlab/app
```

### 9.2 Da archivio locale

In alternativa creare un archivio escludendo ambiente virtuale, segreti e cache,
caricarlo con `scp` e decomprimerlo in `/opt/gestlab/app`.

Non copiare:

- `venv/`;
- `.env` locale;
- `config.ini` con password o token;
- dump di produzione non necessari al test.

## 10. Installare l'ambiente Python

```bash
cd /opt/gestlab/app
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
```

Per il backend web installare le dipendenze necessarie:

```bash
pip install -r requirements.txt
  
```

`kivy` e `kivymd` servono alla UI desktop e non sono necessari per il backend
web. Evitare di installarli sul server Lightsail del test per ridurre tempi,
dipendenze e consumo di memoria.

## 11. Configurare le variabili d'ambiente

Creare un file leggibile soltanto da `root` e dall'utente del servizio:

```bash
sudo install -d -m 750 /etc/gestlab
sudo nano /etc/gestlab/gestlab.env
```

Inserire, usando valori nuovi e reali soltanto sul server:

```text
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=gestlab
DB_USER=gestlab_app
DB_PWD=<PASSWORD_DB_NUOVA>
JWT_SECRET=<JWT_SECRET_GENERATO>
GESTLAB_ADMIN_EMAIL=<EMAIL_ADMIN>
GESTLAB_ADMIN_PASSWORD=<PASSWORD_ADMIN_NUOVA>
GESTLAB_TENANT_NOME=Laboratorio Test AWS
```

Proteggere il file:

```bash
sudo chown root:ubuntu /etc/gestlab/gestlab.env
sudo chmod 640 /etc/gestlab/gestlab.env

#comandi vecchi 
sudo chmod 600 /etc/gestlab/gestlab.env
sudo chown root:root /etc/gestlab/gestlab.env
```


Devi creare un file .env nella root del progetto (/opt/gestlab/app/.env), 
non usare solo /etc/gestlab/gestlab.env.

Esegui sul server:

```bash
sudo cp /etc/gestlab/gestlab.env /opt/gestlab/app/.env
sudo chown ubuntu:ubuntu /opt/gestlab/app/.env
sudo chmod 640 /opt/gestlab/app/.env
```

## 12. Eseguire il bootstrap SaaS

Dalla root del progetto:

```bash
sudo bash -c "cd /opt/gestlab/app && set -a && . /etc/gestlab/gestlab.env && set +a && . .venv/bin/activate && python -m saas.bootstrap"
```

Il comando crea, se mancanti, le tabelle SaaS e l'utente admin iniziale. È
idempotente, ma non usare la password di esempio della documentazione locale.

Controllare che il database risponda:

```bash
mariadb -h 127.0.0.1 -u gestlab_app -p gestlab \
  -e "SHOW TABLES; SELECT email, ruolo FROM utenti;"
```

## 13. Creare il servizio systemd

Creare il servizio:

```bash
sudo nano /etc/systemd/system/gestlab.service
```

Contenuto:

```ini
[Unit]
Description=GestLab SaaS FastAPI
After=network.target mariadb.service
Requires=mariadb.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/gestlab/app
EnvironmentFile=/etc/gestlab/gestlab.env
ExecStart=/opt/gestlab/app/.venv/bin/python -m uvicorn saas.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Attivare il servizio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gestlab
sudo systemctl status gestlab --no-pager
```

Controllare i log:

```bash
sudo journalctl -u gestlab -n 100 --no-pager
```

Prima di configurare Nginx, verificare localmente sull'istanza:

```bash
curl http://127.0.0.1:8000/health
curl -I http://127.0.0.1:8000/
```

La risposta attesa di `/health` è un JSON di stato e la root deve restituire la
pagina della console web.

## 14. Pubblicare con Nginx

Creare la configurazione:

```bash
sudo nano /etc/nginx/sites-available/gestlab
```

Inserire:

```nginx
server {
    listen 80;
    server_name <DOMINIO_O_IP>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Attivare il sito e verificare la configurazione:

```bash
sudo ln -s /etc/nginx/sites-available/gestlab /etc/nginx/sites-enabled/gestlab
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

A questo punto, per un test HTTP, aprire:

```text
http://<IP_STATICO>/
```

La stessa origine serve sia frontend sia API, quindi non serve configurare CORS
per questo deploy.

### 14.1 HTTPS con dominio

Dopo aver creato un record DNS `A` che punti allo Static IP:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <DOMINIO>
```

Seguire la procedura guidata e verificare il rinnovo:

```bash
sudo certbot renew --dry-run
```

Usare l'URL HTTPS anche per il Local Print Agent:

```bash
python -m saas.print_agent --url https://<DOMINIO> --token <TOKEN_DISPOSITIVO>
```

## 15. Test dopo il deploy

Eseguire nell'ordine:

1. Aprire `https://<DOMINIO>/` oppure `http://<IP_STATICO>/`.
2. Aprire `https://<DOMINIO>/docs` e verificare che Swagger risponda.
3. Aprire `https://<DOMINIO>/health`.
4. Effettuare il login con l'admin creato dalle variabili d'ambiente.
5. Creare un reparto o un dipendente dalla console.
6. Ricaricare la pagina e verificare che il record resti nel database.
7. Verificare la coda di stampa senza collegare subito una stampante reale.
8. Creare un secondo utente e verificare il ruolo.
9. Creare un secondo tenant soltanto dopo aver completato il mapping delle
   tabelle business con `tenant_id`.

Controllo API da PowerShell, sostituendo le credenziali:

```powershell
$body = @{ email = '<EMAIL_ADMIN>'; password = '<PASSWORD_ADMIN>' } | ConvertTo-Json
$login = Invoke-RestMethod -Uri 'https://<DOMINIO>/auth/login' `
  -Method Post -ContentType 'application/json' -Body $body

$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri 'https://<DOMINIO>/api/v1/dipendenti' `
  -Headers $headers
```

Per aggiornare il codice:

```bash
cd /opt/gestlab/app
git pull
sudo systemctl restart gestlab
sudo systemctl status gestlab --no-pager
```

## 16. Local Print Agent

Il Local Print Agent deve rimanere sul PC che vede la stampante fisica. Il server
AWS non può raggiungere direttamente una stampante dietro NAT senza un canale
apposito.

Procedura di test:

1. registrare il dispositivo dal pannello Admin;
2. conservare il token soltanto sul PC locale;
3. installare sul PC le dipendenze necessarie;
4. avviare l'agent verso l'URL HTTPS;
5. controllare il polling e lo stato del job nella console.

Non inserire il token dell'agent in Git o nella guida.

## 17. Sicurezza minima per il test

- Non usare `root` per l'applicazione.
- Non esporre la porta `3306`.
- Usare HTTPS prima di provare dati personali reali.
- Cambiare le credenziali demo.
- Usare un `JWT_SECRET` lungo e casuale.
- Non committare `.env`, `config.ini` o dump del database.
- Limitare SSH al proprio IP quando possibile.
- Aggiornare periodicamente Ubuntu e i pacchetti Python.
- Creare uno snapshot Lightsail prima di modifiche allo schema.
- Non usare il test e2e su dati reali: ricrea tabelle SaaS.
- Ruotare password e token se sono stati esposti nel vecchio `config.ini`.

## 18. Spegnere e cancellare le risorse

Per interrompere temporaneamente il test, dalla console Lightsail arrestare
l'istanza. Verificare comunque se lo Static IP continua a generare costi quando
non è associato a un'istanza.

Per chiudere completamente il test:

1. esportare un backup, se serve;
2. eliminare l'istanza Lightsail;
3. eliminare lo Static IP non più utilizzato;
4. eliminare eventuali snapshot;
5. eliminare record DNS non necessari;
6. controllare Billing e Cost Explorer dopo la cancellazione.

Da AWS CLI, usare i nomi corretti della propria regione e istanza:

```powershell
aws lightsail delete-instance --instance-name gestlab-test --region <REGIONE>
```

La cancellazione è distruttiva. Eseguire prima un backup e verificare due volte
il nome della risorsa.

## 19. Evoluzione futura

Quando il test sarà stabile:

- spostare il database su **Amazon RDS for MariaDB/MySQL**;
- usare subnet private e security group dedicati;
- spostare i segreti in **AWS Secrets Manager** o Systems Manager Parameter Store;
- eseguire il backend su **ECS/Fargate** o App Runner;
- usare S3 per PDF e file generati;
- aggiungere backup automatici e monitoring.

### Lambda + DynamoDB

Questa opzione diventa sensata soltanto dopo una riscrittura dell'accesso dati:

- sostituire tutte le query SQL con operazioni DynamoDB;
- progettare chiavi partizione e sort key per `tenant_id`;
- riscrivere transazioni e query aggregate;
- adattare la coda di stampa;
- dividere gli endpoint FastAPI in funzioni Lambda oppure usare un adapter;
- gestire timeout, cold start e connessioni a servizi esterni.

Non è una pubblicazione del codice attuale: è un progetto di migrazione separato.
