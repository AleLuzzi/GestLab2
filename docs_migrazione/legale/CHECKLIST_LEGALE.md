# Checklist legale prima del primo canone

Da completare con il professionista competente. Le bozze in questa cartella
non bastano da sole: il criterio del piano (§ 7.6) è questa checklist firmata.
Finché la firma manca, GestLab resta un pilota tecnico.

Data di preparazione delle bozze: 21 novembre 2026.

## A. Identità

- [ ] Ragione sociale, sede e partita IVA del fornitore SaaS scritte in informativa e DPA.
- [ ] Deciso se designare un DPO; contatti pubblicati oppure motivazione della mancata designazione.
- [ ] Email per le richieste degli interessati attiva e letta.

## B. Testi

- [ ] Informativa art. 13 riletta sul codice attuale (`utenti`, `soggetti`, `dipendenti`, `audit_log`, log, token).
- [ ] Basi giuridiche confermate, compreso il bilanciamento sull’art. 6.1.f per i log di sicurezza.
- [ ] Termini di conservazione confermati, distinti fra account, log, audit e tracciabilità alimentare.
- [ ] L’informativa descrive l’export JSON/CSV dell’admin in console, senza password e token, e non viene pubblicata prima della firma.
- [ ] DPA art. 28 con il laboratorio allegato al contratto manuale del pilota ([CONTRATTO_SAAS_PILOTA.md](CONTRATTO_SAAS_PILOTA.md)).
- [ ] Clausola che esclude registratore telematico, FatturaPA e certificazione di etichette o HACCP presente nel contratto, non solo nel DPA (bozza: § 4 di [CONTRATTO_SAAS_PILOTA.md](CONTRATTO_SAAS_PILOTA.md), allineata al § 11 del DPA).
- [ ] Foro e legge allineati al contratto principale.

## C. Infrastruttura

- [ ] Account cloud intestato al fornitore SaaS, regione SEE annotata in `DPA_FORNITORI_CLOUD.md`.
- [ ] DPA del provider (AWS Data Processing Addendum o equivalente) accettato e archiviato.
- [ ] Database di produzione diverso dallo staging, backup e point-in-time recovery accesi.
- [ ] DPA dell’SMTP accettato prima di abilitare il reset password, oppure reset lasciato disattivo.
- [ ] Sentry spento, oppure DPA accettato e regione annotata, senza invio di dati personali oltre il default del codice.
- [ ] Nessun dato di pilota pagante sul Lightsail di test.

## D. Registro e diritti

- [ ] Registro dei trattamenti del fornitore (come titolare degli account e come responsabile dei dati del laboratorio) redatto dal professionista.
- [ ] Istruzioni scritte al laboratorio su come risponde ai propri clienti e dipendenti: il fornitore non cancella fisicamente lotti e documenti.
- [ ] Procedura interna di avviso al laboratorio in caso di violazione, con il termine ore scelto nel DPA.
- [ ] [DA COMPLETARE: se il trattamento richiede una DPIA. Proposta da far valutare: no, perché non ci sono dati particolari, profilazione né monitoraggio sistematico su larga scala. La decisione è del professionista.]

## E. Firma

Il sottoscritto professionista ha letto le bozze e i punti sopra.

- Nome: [DA COMPLETARE]
- Qualifica: [DA COMPLETARE]
- Data: [DA COMPLETARE]
- Esito: [DA COMPLETARE: bozze utilizzabili con le modifiche indicate / non utilizzabili]

Questa sezione resta vuota di proposito. Non va compilata da chi prepara il software.
