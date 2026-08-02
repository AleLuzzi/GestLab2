# TODO - Miglioramenti code quality GestLab2

## Obiettivo
Migliorare chiarezza, manutenibilità e performance di `main.py` e `main.kv`,
con alcuni interventi mirati su `controller_db.py` e deduplicazione delle
classi RecycleView selezionabili.

## Passi main.py
- [x] Guard `if __name__ == '__main__':`
- [x] Naming PEP 8: `menu` -> `Menu`, `main` -> `MainApp`
- [x] Costanti per i nomi delle schermate
- [x] Docstring sui metodi di navigazione
- [x] `Config.set` spostato e commentato
- [x] `esci()` usa `App.get_running_app().stop()`

## Passi main.kv
- [x] Path immagine con forward slash
- [x] Template `<MenuButton@MDButton>` per ridurre ripetizione
- [x] Gestione esplicita bottone "Impostazioni"
- [x] Uso template nei bottoni del menu

## Passi aggiuntivi
- [x] `controller_db.py`: lettura credenziali da `config.ini`
- [x] `controller_db.py`: helper per riuso cursore / connessione
- [x] Modulo condiviso `recycleviews.py` con classi selezionabili
- [x] Deduplicazione classi nei moduli (anag_dipendenti, chiudi_lotto, ingresso_merce, lotti_vendita, nuovo_menu)
- [x] Rimozione print di debug nei gestori di selezione
- [x] Verifica `python -m py_compile` su tutti i file
- [x] Verifica runtime: `BUILD_OK` (app.build() riuscito con KV caricato)

