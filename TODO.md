# TODO - Riscrittura per KivyMD 2.x

## Problema
- `requirements.txt` richiedeva `kivymd==1.2.0` ma nel venv è installato KivyMD **2.0.1.dev0**.
- KivyMD 2.x ha riscritto completamente le API: `MDTabsBase` non esiste più
  (sostituito da `MDTabsPrimary`/`MDTabsItem`/`MDTabsCarousel`).
- Altri widget cambiati: `MDRaisedButton`/`MDFlatButton` -> `MDButton`+`MDButtonText`,
  `MDTopAppBar` (title -> `MDTopAppBarTitle`), `MDTextField` (hint_text -> `MDTextFieldHintText`),
  colori tema M3 (`bg_normal` -> `surfaceColor`, `primary_light` -> `primaryContainerColor`, ecc.)

## Piano di riscrittura

### File Python
- [x] `ingresso_merce/ingresso_merce.py`: rimuovere `MDTabsBase`, usare `MDTabsItem`+`MDTabsItemText`+`MDTabsCarousel`
- [x] `nuovo_menu/nuovo_menu.py`: idem per i suoi 4 tab

### File KV
- [x] `main.kv`: `MDFillRoundFlatIconButton` -> `MDButton`+`MDButtonText`
- [x] `ingresso_merce/ingresso_merce.kv`: `MDTabs` -> `MDTabsPrimary`+`MDTabsCarousel`, appbar, bottoni, textfield, colori
- [x] `nuovo_menu/nuovo_menu.kv`: idem
- [x] `chiudi_lotto/chiudi_lotto.kv`: bottoni, appbar, colori
- [x] `lotti_vendita/lotti_vendita.kv`: idem

### Configurazione
- [x] `requirements.txt`: aggiornare `kivymd==2.0.1.dev0`

### Verifica
- [x] `python -m py_compile` su tutti i file
- [x] Test import `from kivymd.uix.tab import MDTabsPrimary`
- [x] Avvio app `python main.py` senza errori

---

## FIX CRITICO: FBO Initialization failed con MDTabsItem

### Sintomo
Dopo la riscrittura, all'avvio `python main.py` l'app si fermava con:
```
Exception: FBO Initialization failed: Incomplete attachment (36054)
```
in `kivymd/uix/behaviors/ripple_behavior.py` -> `M3CommonRipple.init_fbos()`.

### Causa
KivyMD 2.0.1.dev0 applica a `MDTabsItem` la regola KV:
```
<MDTabsItem>
    size_hint: None, None
    height: self.minimum_height   # = 0 al momento dell'init!
```
`MDTabsItem` eredita `StateLayerBehavior` -> `M3RectangularRippleBehavior`,
che in `__init__` crea una `Fbo(size=self.size)`. Dato che all'init l'altezza è 0,
la FBO ha dimensione `(100, 0)` -> Kivy genera `Incomplete attachment (36054)`
(le FBO con larghezza o altezza 0 falliscono su questa GPU/driver NVIDIA).

### Fix applicato
Patch al file installato della libreria:
`venv/lib/site-packages/kivymd/uix/tab/tab.kv`:
```
<MDTabsItem>
    orientation: "vertical"
    size_hint: None, None
    height: 64 if self.minimum_height == 0 else self.minimum_height
    spacing: "4dp"
    padding: 0, "12dp", 0, "8dp"
```
Così all'init la FBO ha altezza 64 (non-zero) e la creazione riesce;
poi `minimum_height` viene ricalcolato automaticamente con i figli.

### Verifica
- App completa avviata con successo (`APP RUN OK: nessun errore durante l'avvio`).

