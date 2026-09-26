# Pubblicazione automatica su AWS Lightsail

Questa guida spiega come usare gli script in `deploy/` per pubblicare la console
web SaaS di GestLab2 (`saas.main:app`) su una istanza Amazon Lightsail.

La procedura manuale equivalente resta in
[`PUBBLICAZIONE_AWS_TEST.md`](PUBBLICAZIONE_AWS_TEST.md). Non va eliminata: gli
script coprono il deploy ripetibile, non il budget AWS, la migrazione dati
locali, il Print Agent sul PC né i test funzionali in console.

## Cosa fanno gli script

| File | Ruolo |
|---|---|
| `deploy/publish-lightsail.ps1` | Dal PC Windows: crea (se manca) istanza Lightsail, Static IP, porte 80/443, copia il codice, lancia il bootstrap |
| `deploy/setup-server.sh` | Sull'istanza Ubuntu: MariaDB, Nginx, venv, systemd, bootstrap SaaS |
| `deploy/update-server.sh` | Aggiorna il codice e riavvia il servizio |
| `deploy/destroy-lightsail.ps1` | Elimina istanza e Static IP |
| `deploy/gestlab.env.example` | Modello delle variabili; copiare in `gestlab.env` |
| `requirements-web.txt` | Dipendenze backend senza Kivy/KivyMD |

Non vengono pubblicati `config.ini`, `.env` locale, `venv/` né i file `.pem`.

## Prerequisiti sul PC

1. Account AWS e avviso di costo (sezione 2 di `PUBBLICAZIONE_AWS_TEST.md`).
2. [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) configurato:

   ```powershell
   aws --version
   aws configure
   ```

   Regione consigliata per l'Italia: `eu-central-1` (Francoforte). Lightsail non
   è disponibile in tutte le regioni (per esempio spesso manca `eu-south-1`
   Milano). Verificare con:

   ```powershell
   aws lightsail get-regions --query "regions[].name" --output text
   ```

3. OpenSSH client (`ssh` e `scp`, presenti in Windows 10/11).
4. `tar` (incluso in Windows 10/11 recenti).
5. Permessi IAM per Lightsail.

Prima esecuzione dello script, se PowerShell blocca i `.ps1`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Prima configurazione dei segreti

I segreti non vanno in Git. Alla prima esecuzione lo script crea
`deploy/gestlab.env` (già in `.gitignore`) e genera password DB e `JWT_SECRET`
se mancano.

Obbligatorio: email dell'admin SaaS.

```powershell
cd C:\Users\Ale\GestLab2\GestLab2
.\deploy\publish-lightsail.ps1 -AdminEmail "tu@example.com"
```

In alternativa copiare il modello e compilare a mano:

```powershell
Copy-Item deploy\gestlab.env.example deploy\gestlab.env
notepad deploy\gestlab.env
.\deploy\publish-lightsail.ps1
```

La password admin, se non indicata, viene generata e scritta solo in
`deploy/gestlab.env`. Conservare quel file.

## Deploy completo (caso più comune)

Dalla root del repository:

```powershell
.\deploy\publish-lightsail.ps1 -AdminEmail "tu@example.com"
```

Comportamento predefinito:

- regione `eu-central-1`;
- istanza `gestlab-test`, piano `nano_3_0`, Ubuntu 24.04;
- nuova key pair Lightsail salvata in `deploy/gestlab-test-key.pem`;
- Static IP `gestlab-test-ip`;
- **codice del workspace locale** (anche se non è stato fatto `git push`);
- HTTP sull'IP pubblico, senza HTTPS.

Al termine lo script stampa URL della console, `/docs`, `/health` e il percorso
del file env.

Aprire `http://<IP>/` e accedere con `GESTLAB_ADMIN_EMAIL` /
`GESTLAB_ADMIN_PASSWORD`.

Il primo avvio può richiedere 10–20 minuti (creazione VM, `apt upgrade`, pip).

## Parametri utili

```powershell
.\deploy\publish-lightsail.ps1 `
  -Region eu-west-1 `
  -InstanceName gestlab-test `
  -BundleId nano_3_0 `
  -BlueprintId ubuntu_24_04 `
  -AdminEmail "tu@example.com" `
  -AdminPassword "ScegliUnaPasswordLunga" `
  -TenantNome "Laboratorio Test AWS" `
  -Source Local
```

| Parametro | Default | Note |
|---|---|---|
| `-Region` | `eu-central-1` | Deve supportare Lightsail |
| `-BundleId` | `nano_3_0` | Se fallisce, elencare con `aws lightsail get-bundles --region ...` |
| `-BlueprintId` | `ubuntu_24_04` | Alternative: `ubuntu_22_04` |
| `-Source Local` | sì | Pacchetto del workspace, senza `venv`, `.env`, `config.ini` |
| `-Source Git` | | `git clone` da GitHub sul server |
| `-GitRepo` / `-GitRef` | repo pubblico / `main` | Usati solo con `-Source Git` |
| `-SkipCreate` | | Non crea l'istanza; fa solo il setup su quella esistente |
| `-UpdateOnly` | | Solo aggiornamento codice + restart |
| `-Domain` / `-Https` | | HTTPS con Certbot; il DNS `A` deve già puntare allo Static IP |

Se `create-instances` rifiuta blueprint o bundle:

```powershell
aws lightsail get-blueprints --region eu-central-1 --query "blueprints[].blueprintId" --output text
aws lightsail get-bundles --region eu-central-1 --query "bundles[].[bundleId,price]" --output table
```

Poi rilanciare con `-BlueprintId` e `-BundleId` corretti.

## Aggiornare il codice dopo il primo deploy

Workspace locale (modifiche non ancora su GitHub):

```powershell
.\deploy\publish-lightsail.ps1 -UpdateOnly -Source Local
```

Dal repository Git (dopo `git push`):

```powershell
.\deploy\publish-lightsail.ps1 -UpdateOnly -Source Git -GitRef main
```

## HTTPS

1. Assegnare un record DNS `A` allo Static IP.
2. Attendere la propagazione.
3. Rilanciare il setup (non solo update) con dominio:

```powershell
.\deploy\publish-lightsail.ps1 -SkipCreate -Domain gestlab.example.com -Https
```

Certbot usa `GESTLAB_ADMIN_EMAIL` come contatto Let's Encrypt, salvo
`LETSENCRYPT_EMAIL` in `gestlab.env`.

## Cosa resta manuale

- Budget e Cost Explorer in console AWS.
- Migrazione di un dump MySQL locale e mapping `tenant_id` (sezione 8.2 della
  guida manuale).
- Test in console (login, anagrafiche, coda di stampa).
- Local Print Agent sul PC che vede la stampante.
- Limitare SSH al proprio IP (console Lightsail, scheda Networking).

## Spegnere e cancellare

Arresto temporaneo: console Lightsail → Stop instance. Lo Static IP può
continuare a costare.

Chiusura completa:

```powershell
.\deploy\destroy-lightsail.ps1
```

Confermare con `s`. Aggiungere `-Force` per saltare la conferma, `-DeleteKeyPair`
per eliminare anche la key pair Lightsail. Lo script non cancella snapshot né
record DNS: verificarli a mano, poi Billing.

## Sicurezza

- Non committare `deploy/gestlab.env` né `deploy/*.pem`.
- Non aprire la porta `3306`.
- Usare HTTPS prima di dati personali reali.
- Ruotare i segreti se sono già finiti in `config.ini` o in chat.
- Dopo il primo deploy, opzionalmente restringere SSH al proprio IP.

## Risoluzione problemi

**AWS CLI: AccessDenied**  
L'utente IAM deve poter gestire Lightsail (istanze, IP statici, key pair, porte).

**SSH timeout**  
Attendere che l'istanza sia `running` e che cloud-init abbia finito. Controllare
che la porta 22 sia aperta e che `deploy/<nome>-key.pem` sia la chiave giusta.
Windows a volte richiede ACL ristrette sul `.pem` (lo script le imposta).

**Health check HTTP fallito**  
Sul server:

```bash
sudo systemctl status gestlab --no-pager
sudo journalctl -u gestlab -n 100 --no-pager
curl http://127.0.0.1:8000/health
```

**Errore MariaDB / bootstrap**  
Verificare `DB_PWD` in `/etc/gestlab/gestlab.env` e che il servizio `mariadb`
sia attivo. `python -m saas.bootstrap` è idempotente.

**Kivy sul server**  
Non deve essere installato. Il setup usa `requirements-web.txt`.

## Relazione con la guida manuale

| Sezioni di `PUBBLICAZIONE_AWS_TEST.md` | Script |
|---|---|
| 4–5 Creazione istanza e SSH | `publish-lightsail.ps1` |
| 6–7 Pacchetti e database | `setup-server.sh` |
| 8.1 / 12 Bootstrap schema vuoto | `setup-server.sh` (`python -m saas.bootstrap`) |
| 9–11 Codice, venv, env | `setup-server.sh` (`-Source Local` o `Git`) |
| 13–14 systemd e Nginx | `setup-server.sh` |
| 14.1 HTTPS | `-Domain` + `-Https` |
| 15 `git pull` + restart | `-UpdateOnly` |
| 18 Cancellazione | `destroy-lightsail.ps1` |
| 2.2 Budget, 8.2 migrazione dati, 16 Print Agent | restano manuali |
