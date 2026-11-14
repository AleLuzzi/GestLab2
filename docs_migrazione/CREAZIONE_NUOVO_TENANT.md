# Creazione di un nuovo laboratorio

Procedura interna per aprire un tenant GestLab. Il comando crea tenant, dati OSA, primo admin e catalogo in una sola operazione. Non serve eseguire SQL.

Il self-service pubblico resta fuori da questa procedura.

## Prima di iniziare

Servono il progetto aggiornato, l'ambiente virtuale e le variabili d'ambiente del database già usate dal backend. Raccogliere questi dati dal laboratorio:

| Dato | Vincolo |
| --- | --- |
| Nome del tenant | Obbligatorio, al massimo 255 caratteri |
| Piano | `basic`, `pro` oppure `enterprise` |
| Ragione sociale OSA | Obbligatoria |
| Sede | Indirizzo della sede, obbligatorio |
| Laboratorio | Nome del laboratorio, obbligatorio |
| Partita IVA | 11 cifre, senza prefisso |
| Email del primo admin | Non deve esistere già |
| Password del primo admin | Almeno 10 caratteri, una lettera e un numero |
| Catalogo | `vuoto` oppure `macelleria` |

`macelleria` inserisce l'anagrafica di partenza: mezzena e muscolo bovino, pancia, spalla e coscia di suino, sale, salsicce fresche, hamburger e arrosto. Non inserisce prezzi, EAN, lotti né giacenze. `vuoto` non inserisce articoli: prima dell'ingresso vanno creati da Configurazioni, Articoli.

## Comando

Dalla cartella del progetto, con l'ambiente virtuale attivo:

```text
python -m saas.onboarding --nome "Macelleria Rossi" --piano basic --ragione-sociale "Rossi Carni Srl" --sede "Via Roma 1, Milano" --laboratorio "Laboratorio Rossi" --partita-iva 12345678901 --email admin@rossi.example --catalogo macelleria
```

La password non va messa nel comando: il programma la chiede due volte e non la ristampa. Il risultato atteso è simile a questo:

```text
Laboratorio creato. Tenant ID: 12
Admin ID: 20
Email: admin@rossi.example
Catalogo: macelleria (9 articoli)
```

Se un passaggio fallisce, non resta un tenant parziale. Gli errori più comuni sono:

- `La password deve contenere almeno 10 caratteri.` e gli altri messaggi della policy password.
- `La partita IVA deve essere di 11 cifre.`
- `Esiste già un utente con questa email.`
- `Le password non coincidono.` quando le due digitazioni sono diverse.

Lo script `saas/crea_tenant.py` non crea più un tenant. Rimanda a questo comando.

## Login e primo ingresso

Aprire la console e accedere con l'email e la password del primo admin. Il ruolo è `admin`.

Per registrare il primo ingresso, sempre dalla console:

1. Configurazioni, poi Clienti e fornitori. Creare un'anagrafica con il ruolo Fornitore e la casella Abilitato per ingresso merce.
2. Ingresso merce. In intestazione scegliere quel fornitore. Negli articoli scegliere una voce del catalogo, per esempio Pancia di suino, indicare la quantità e confermare il riepilogo.

Con il catalogo `vuoto`, prima del punto 2 creare l'articolo da Configurazioni, Articoli. Non si interviene sul database.

Prezzo, ricette e altri utenti non fanno parte di questa creazione. Il prezzo si imposta sul listino prima di una vendita. Gli altri utenti si aggiungono dopo l'accesso, dalla sezione Admin.
