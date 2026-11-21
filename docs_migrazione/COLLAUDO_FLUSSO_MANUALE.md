# Collaudo flusso pilota — solo manuale utente

Protocollo per verificare che un **operatore nuovo** (senza accesso a
`ISTRUZIONI_USO.md`, README o chat di sviluppo) completi il percorso pilota
usando unicamente [MANUALE_UTENTE.md](MANUALE_UTENTE.md). Le schermate di
riferimento opzionali restano in [sequenza_pilota/](sequenza_pilota/) come
indicato nel manuale.

## Ruoli

| Ruolo | Chi | Documenti ammessi |
|---|---|---|
| Preparazione laboratorio | Admin del pilota (giorno 0) | Manuale § 1–2 |
| Collaudo | Operatore che non ha mai usato GestLab | **Solo** manuale § 1 e § 3–7 |
| Osservatore | Referente interno | Questa scheda + cronometro |

L’admin configura anagrafiche, ricetta e dati OSA **prima** che l’operatore
inizi il collaudo (manuale § 2). L’operatore non deve ricevere URL di API,
comandi da terminale né account admin.

## Prerequisiti

- [ ] Console raggiungibile da browser (tablet o PC) con URL fornito dall’admin.
- [ ] Account **operatore** (email e password) creato dall’admin.
- [ ] Catalogo, fornitore abilitato all’ingresso, almeno un cliente, un
  dipendente, una ricetta attiva e prezzo unitario sul prodotto da vendere
  (manuale § 2).
- [ ] Local Print Agent **opzionale** per questa scheda: etichetta e ricevuta
  si validano almeno con **Genera etichetta (PDF)** e messaggio di conferma
  vendita; la stampa fisica resta nel gate tablet del pilota.

## Percorso da completare (operatore)

Segnare l’ora di inizio. L’operatore deve arrivare al fondo senza assistenza
tecnica (solo chiarimenti sul testo del manuale).

| # | Sezione manuale | Esito atteso | OK / KO | Note |
|---|---|---|---|---|
| 1 | § 1 Accedere | Login operatore, Home visibile | | |
| 2 | § 3 Ingresso merce | DDT confermato, lotto acquisto in Lotti | | |
| 3 | § 4 Lavorazione | Lotto prodotto (`V`) creato con scadenza/origine dichiarate | | |
| 4 | § 5 Etichetta | PDF con ingredienti, allergeni, lotto, scadenza | | |
| 5 | § 6 Vendita DDT | DDT registrato, giacenza scalata, PDF scaricabile | | |
| 6 | § 6.3 (facoltativo) | Ristampa DDT senza nuovo numero | | |
| 7 | § 7 Genealogia | Dal lotto `V` si raggiunge DDT e fornitore del lotto `A` | | |
| 8 | § 7 | **Scarica scheda PDF** apre un PDF coerente | | |

**Criterio superamento:** tutte le righe obbligatorie (1–5 e 7–8) segnate OK;
tempo genealogia lotto `V` → fornitore **≤ 60 secondi** (manuale § 7);
nessun uso di fogli Excel o strumenti fuori manuale.

## Esito

| Campo | Valore |
|---|---|
| Data | |
| Tenant / laboratorio | |
| Operatore (iniziali) | |
| Osservatore | |
| Durata totale (min) | |
| Durata genealogia (s) | |
| Esito complessivo | SUPERATO / NON SUPERATO |

### Fuori perimetro di questa scheda

- Installazione server, backup, `.env` (sviluppo).
- Collaudo fisico tablet/scanner (checklist § 3 UX, gate § 4).
- HACCP lite (opzionale su richiesta pilota).

## Ripetibilità automatica (regressione)

Il percorso operatore sugli endpoint della console è ripetibile in ambiente
isolato con `tests/test_flusso_pilota_manuale.py` (allineamento testi manuale ↔
UI e flusso API con ruolo `operatore`). Non sostituisce la firma di un operatore
umano su questa scheda.