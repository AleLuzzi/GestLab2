# TODO — Mostrare il nome del reparto nel tab Dipendenti

- [x] Raccogliere informazioni e creare il piano
- [ ] core/core_models.py: aggiungere `reparto_nome` al modello `Dipendente`
- [ ] core/repositories/dipendenti.py: LEFT JOIN con `reparti` in `fetch_all` e `find_by_id`
- [ ] saas/schemas.py: aggiungere `reparto_nome` a `DipendenteOut`
- [ ] saas/main.py: popolare `reparto_nome` nelle risposte dipendenti
- [ ] web/app.js: mostrare `reparto_nome` nella tabella (fallback all'ID)
- [ ] Verifica/test dell'endpoint `/api/v1/dipendenti`
