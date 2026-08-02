# TODO - Implementazione anag_dipendenti in GestLab2

## Obiettivo
Portare il modulo `anag_dipendenti` dal progetto `GestioneLaboratorio`
(C:\Users\Ale\Documents\GestioneLaboratorio\Laboratorio\anag_dipendenti)
in GestLab2 in stile KivyMD 2.x coerente con gli altri moduli.

## Passi

- [x] `controller_db.py`: aggiungere funzioni CRUD per dipendenti e reparti
- [x] `anag_dipendenti/__init__.py`: export classe
- [x] `anag_dipendenti/anag_dipendenti.py`: classe `Anag_dipendenti(MDScreen)` con CRUD
- [x] `anag_dipendenti/anag_dipendenti.kv`: UI KivyMD 2.x
- [x] `main.py`: registrazione schermata + metodo menu
- [x] `main.kv`: include del .kv + bottone "Dipendenti"
- [x] Verifica: `python -m py_compile` su tutti i file
- [x] Test avvio `python main.py`

## Aggiunta MDDialog di conferma eliminazione dipendente

- [x] `anag_dipendenti/anag_dipendenti.py`: import dialog/button KivyMD 2.x
- [x] `anag_dipendenti/anag_dipendenti.py`: `_elimina()` apre dialog di conferma
- [x] `anag_dipendenti/anag_dipendenti.py`: metodi `_conferma_elimina()` e `_annulla_elimina()`
- [x] Verifica: `python -m py_compile` su `anag_dipendenti/anag_dipendenti.py`
- [x] Test runtime costruzione/apertura MDDialog (test isolato)

