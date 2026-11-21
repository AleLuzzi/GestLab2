# Piloti paganti — contratto e canone manuali (v1)

Decisione di prodotto (allineata a [PIANO_PRODOTTO_VENDIBILE.md](PIANO_PRODOTTO_VENDIBILE.md) § 7.5 e § 5):
i **primi uno–due laboratori pilota paganti** usano contratto e incasso **fuori
dall’applicazione**. Il rilascio del prodotto vendibile **non** dipende da
Stripe, portale self-service o registrazione pubblica.

Billing self-service resta in [§ 5 Fuori perimetro v1](CHECKLIST_PRODOTTO_VENDIBILE.md#5-fuori-perimetro-v1).

## Cosa fa (e non fa) il software

| Aspetto | Comportamento v1 |
| --- | --- |
| Registrazione pubblica | Assente: nuovo tenant solo con `python -m saas.onboarding` (procedura interna) |
| Incasso canone | Fuori dall’app: fattura e bonifico (o equivalente) gestiti dal fornitore |
| Campo `tenant.piano` | Etichetta commerciale (`basic` / `pro` / `enterprise`), **non** stato di pagamento |
| Login | Controlla solo utente attivo e credenziali; **non** verifica canone o abbonamento |
| API | Nessun endpoint di billing, checkout abbonamento o integrazione Stripe |

Vedi anche [CREAZIONE_NUOVO_TENANT.md](CREAZIONE_NUOVO_TENANT.md) (onboarding interno) e
[legale/CONTRATTO_SAAS_PILOTA.md](legale/CONTRATTO_SAAS_PILOTA.md) (bozza contratto § 2).

## Sequenza operativa per un pilota pagante

1. **Commerciale e legale** — compilare e far firmare contratto pilota + DPA; chiudere la
   [CHECKLIST_LEGALE.md](legale/CHECKLIST_LEGALE.md) con il professionista prima del
   primo canone.
2. **Registro interno** — annotare il laboratorio nel registro sotto (fuori dal DB).
3. **Onboarding tecnico** — dopo la firma, creare il tenant:
   ```text
   python -m saas.onboarding --nome "…" --piano basic …
   ```
4. **Go-live** — collaudo assistito, Print Agent sul banco, credenziali al referente.
5. **Canone** — emettere fattura e registrare l’incasso nel gestionale contabile del
   fornitore (non in GestLab). Impostare promemoria rinnovo manuale.

Non attivare un pilota **pagante** sul Lightsail di test né su ambienti senza backup/PITR
gestiti (cfr. checklist Fase C).

## Registro piloti (manuale, fuori repository)

Tenere aggiornata una copia interna (foglio di calcolo o cartella contratti). Esempio:

| # pilota | Tenant ID (dopo onboarding) | Ragione sociale | Contratto firmato il | Primo canone fatturato | Note |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |
| 2 | | | | | |

Dopo il **secondo** pilota con canone incassato, valutare billing self-service
(`SAAS_MIGRATION_PLAN.md`, fase billing) come progetto separato — non gate v1.

## Criterio di verifica checklist

- Nessuna dipendenza codice o UI su Stripe/abbonamento per usare la console.
- Processo e contratto documentati; massimo due piloti in questa modalità prima di
  aprire il tema portale pagamenti.

Versione: 21 novembre 2026.