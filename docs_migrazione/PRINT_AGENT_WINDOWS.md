# Local Print Agent come servizio Windows

Il PC di banco esegue l'agent come servizio `GestLabPrintAgent`. Windows lo
avvia dopo la rete, al boot, e lo riavvia se il processo termina. Il token del
dispositivo non sta nel repository.

## Token

Un amministratore del tenant registra il banco una sola volta:

```text
POST /api/v1/dispositivi
{"nome": "Banco 1", "stampante_dymo": "DYMO LabelWriter 450"}
```

La risposta contiene `token`. Va copiato subito: le letture successive del
dispositivo non lo restituiscono. Il nome della stampante deve essere quello
installato in Windows per tutti gli utenti, non solo per la sessione corrente.

## Installazione

Sul PC di banco, in PowerShell avviato come amministratore, dalla cartella del
progetto:

```text
.\deploy\installa-print-agent.ps1 -Url "https://app.example.com" -Token "<TOKEN>"
```

Lo script salva URL, token e intervallo in
`%ProgramData%\GestLab\print-agent.env`, limita la lettura a SYSTEM e agli
amministratori, installa `pywin32` nell'ambiente del banco e registra il
servizio con avvio automatico ritardato. Indica anche al servizio dove trovare
`pywin32` e il progetto, perché l'host del servizio non eredita l'ambiente
dell'utente. Non ristampa il token.

Per cambiare URL o token, rieseguire lo stesso comando e riavviare il servizio:

```text
Restart-Service GestLabPrintAgent
```

Per rimuoverlo:

```text
.\deploy\installa-print-agent.ps1 -Rimuovi
```

Il file con il token non viene cancellato dalla rimozione. Va eliminato a mano
se il banco non deve più stampare.

## Riavvio del PC

`sc.exe qc GestLabPrintAgent` deve mostrare `START_TYPE` `AUTO_START` e
`DELAYED`. Dopo un riavvio, senza aprire una finestra di Python:

```text
Get-Service GestLabPrintAgent
```

Lo stato atteso è `Running`. Se il processo esce, Windows lo rilancia dopo 5
secondi, fino a tre volte nell'arco di un giorno.
