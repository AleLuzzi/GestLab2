# Contratto di servizio SaaS — bozza pilota

Testo di lavoro del 21 novembre 2026 per i primi laboratori paganti con
**contratto e pagamento manuali** (cfr. checklist prodotto, Fase C). Non è un
contratto firmato. I campi `[DA COMPLETARE]` vanno chiusi dal professionista
prima della firma.

Allegati previsti alla firma:

- [DPA_CLIENTE_OSA.md](DPA_CLIENTE_OSA.md) (art. 28 GDPR)
- [INFORMATIVA_PRIVACY.md](INFORMATIVA_PRIVACY.md) (art. 13, se pubblicata dal titolare)
- [CHECKLIST_LEGALE.md](CHECKLIST_LEGALE.md) firmata

## 1. Parti e oggetto

**Fornitore:** [DA COMPLETARE: ragione sociale, sede, P.IVA, email contratti]

**Cliente (laboratorio OSA):** [DA COMPLETARE: ragione sociale, sede, P.IVA, email]

Il Fornitore eroga in hosting il software GestLab per la tracciabilità
alimentare interna, la stampa di etichette e documenti di scarico e le vendite
con DDT e ricevuta non fiscale, secondo le funzioni descritte nella
documentazione tecnica in vigore alla data di sottoscrizione.

## 2. Durata, canone e pagamento pilota

Durata: [DA COMPLETARE: mesi o rinnovo tacito].

Canone: [DA COMPLETARE: importo e periodicità].

Per i primi uno-due piloti il pagamento avviene **fuori dall’applicazione**
(fattura o bonifico manuale). Non è incluso billing self-service né
integrazione con circuiti di pagamento.

## 3. Conservazione dei dati di tracciabilità

L’applicazione **non offre** all’operatore la cancellazione fisica di lotti,
movimenti, documenti d’ingresso, lavorazioni né vendite registrate.

- Le anagrafiche (clienti, fornitori, articoli, ricette) possono essere
  **disattivate** senza cancellare lo storico collegato (DDT, lotti, vendite).
- Le rettifiche di giacenza restano tracciate in `movimenti_lotto` con motivo e
  in `audit_log` quando previsto dal prodotto.
- L’export dei dati del tenant (JSON/CSV dall’admin) e le istruzioni per la
  cessazione del servizio sono descritte nel DPA.

Il Cliente resta titolare delle decisioni di conservazione verso le autorità e i
propri clienti, nel rispetto degli obblighi di rintracciabilità alimentare.

## 4. Perimetro del servizio — esclusioni fiscali e di certificazione

Le clausole seguenti replicano il § 11 del DPA e **valgono anche nel presente
contratto**, non solo nell’allegato privacy:

1. GestLab **non** è un registratore telematico e **non** emette corrispettivi
   fiscali né scontrini con valenza fiscale.
2. La ricevuta generata dal Local Print Agent è un **documento non fiscale** e
   non sostituisce lo scontrino del registratore telematico.
3. Il servizio **non** invia fatture al Sistema di Interscambio e **non**
   implementa FatturaPA né fatturazione elettronica (FE) nella versione pilota.
4. Il DDT emesso dall’applicazione è un documento interno di scarico e consegna;
   eventuali obblighi fiscali o doganali restano in capo al Cliente.
5. L’etichetta e la scheda lotto PDF sono **riepiloghi** dei dati inseriti dal
   Cliente; **non** costituiscono certificazione di conformità al Reg. (UE)
   1169/2011 né dichiarazione ufficiale sull’etichettatura.
6. Eventuali funzioni opzionali di registro temperature (HACCP lite) **non**
   sostituiscono un manuale HACCP, procedure ASL, firme o certificazioni.

Il Cliente è e resta **OSA**; verifica obblighi alimentari e fiscali con i
propri consulenti.

## 5. Livello di servizio e supporto

[DA COMPLETARE: finestre di manutenzione, canali di supporto, tempi di risposta
per i piloti.]

Backup e ripristino del database gestito sono descritti nella documentazione
tecnica (`saas/README.md`).

## 6. Riservatezza e dati personali

Il trattamento dei dati personali è disciplinato dal DPA allegato. Il Fornitore
agisce come responsabile per i dati inseriti nel tenant del Cliente.

## 7. Limitazione di responsabilità

[DA COMPLETARE: massimale, esclusioni, con il professionista.]

Senza pregiudizio di quanto sopra, nessuna parte potrà sostenere che il
software, da solo, soddisfi obblighi fiscali (RT, FE) o di certificazione
legali di etichette o HACCP.

## 8. Legge e foro

[DA COMPLETARE: legge italiana e foro, allineati al DPA.]

---

Versione bozza: 21 novembre 2026.