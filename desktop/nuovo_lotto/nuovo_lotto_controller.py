"""Controller KivyMD per la creazione di un lotto di vendita."""

import datetime
from decimal import Decimal, InvalidOperation

from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen

from core.services import vendite as vendite_service


class Nuovo_lotto(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        dati = vendite_service.dati_nuovo_lotto()
        self.progressivo_ven = dati["progressivo_ven"]
        self.lotti_ingresso = dati["lotti_ingresso"]
        self.prodotti = dati["prodotti"]
        self.righe_da_salvare = []
        self.data_ven = datetime.date.today()

        self.ids.label_progressivo.text = (
            f"{self.progressivo_ven}V" if self.progressivo_ven is not None else "Non configurato"
        )
        self.ids.rv_lotti_ingresso.data = [
            {
                "label_1": riga["progressivo_acq"],
                "label_2": riga["data"].strftime("%d/%m/%y") if riga["data"] else "",
                "label_3": riga["prodotto"],
                "label_4": riga["residuo"],
            }
            for riga in self.lotti_ingresso
        ]
        self.ids.rv_righe.data = []
        self.ids.rv_lotti_ingresso.layout_manager.bind(
            selected_nodes=self._aggiorna_lotto_selezionato
        )
        self.menu_prodotti = MDDropdownMenu(
            caller=self.ids.campo_prodotto,
            items=[
                {
                    "text": prodotto,
                    "on_release": lambda prodotto=prodotto: self._seleziona_prodotto(prodotto),
                }
                for prodotto in self.prodotti
            ],
        )
        self.ids.campo_prodotto.bind(focus=self._on_prodotto_focus)

    def _aggiorna_lotto_selezionato(self, _layout, selected):
        if _layout is not self.ids.rv_lotti_ingresso.layout_manager:
            return
        if not selected:
            self.ids.label_lotto_selezionato.text = "Nessun lotto selezionato"
            return
        riga = self.lotti_ingresso[selected[0]]
        self.ids.label_lotto_selezionato.text = (
            f"Lotto {riga['progressivo_acq']} — {riga['prodotto']} "
            f"(residuo: {riga['residuo']})"
        )

    def _on_prodotto_focus(self, _instance, focused):
        if focused and self.prodotti and _instance is self.ids.campo_prodotto:
            self.menu_prodotti.open()

    def _seleziona_prodotto(self, prodotto):
        self.ids.campo_prodotto.text = prodotto
        self.menu_prodotti.dismiss()

    def aggiungi_riga(self):
        selected = self.ids.rv_lotti_ingresso.layout_manager.selected_nodes
        if not selected:
            self.ids.label_errore.text = "Selezionare un lotto di ingresso."
            return

        prodotto = self.ids.campo_prodotto.text.strip()
        if not prodotto:
            self.ids.label_errore.text = "Selezionare il prodotto ottenuto."
            return

        raw_quantita = self.ids.campo_quantita.text.strip().replace(",", ".")
        try:
            quantita = Decimal(raw_quantita)
        except InvalidOperation:
            self.ids.label_errore.text = "Inserire una quantità valida."
            return
        if not quantita.is_finite() or quantita <= 0 or quantita.as_tuple().exponent < -2:
            self.ids.label_errore.text = "La quantità deve essere positiva, con massimo 2 decimali."
            return

        lotto = self.lotti_ingresso[selected[0]]
        riga = {
            "lotto_acq": lotto["progressivo_acq"],
            "prodotto": prodotto,
            "quantita": format(quantita, "f"),
            "prod_origine": lotto["prodotto"],
        }
        self.righe_da_salvare.append(riga)
        self._aggiorna_righe()
        self.ids.campo_quantita.text = ""
        self.ids.label_errore.text = ""

    def _aggiorna_righe(self):
        self.ids.rv_righe.data = [
            {
                "label_1": riga["lotto_acq"],
                "label_2": riga["prodotto"],
                "label_3": riga["quantita"],
                "label_4": riga["prod_origine"],
            }
            for riga in self.righe_da_salvare
        ]
        self.ids.label_conteggio.text = f"Righe inserite: {len(self.righe_da_salvare)}"

    def rimuovi_riga(self):
        selected = self.ids.rv_righe.layout_manager.selected_nodes
        if not selected:
            self.ids.label_errore.text = "Selezionare una riga da rimuovere."
            return
        del self.righe_da_salvare[selected[0]]
        self.ids.rv_righe.layout_manager.clear_selection()
        self._aggiorna_righe()
        self.ids.label_errore.text = ""

    def salva_ed_esci(self):
        if self.progressivo_ven is None:
            self.ids.label_errore.text = "Progressivo di vendita non configurato."
            return
        if not self.righe_da_salvare:
            self.ids.label_errore.text = "Aggiungere almeno una riga prima di salvare."
            return
        try:
            vendite_service.crea_lotto_vendita(
                self.progressivo_ven, self.data_ven, self.righe_da_salvare
            )
        except Exception as exc:
            self.ids.label_errore.text = f"Salvataggio non riuscito: {exc}"
            return
        self.manager.current = "menu"

    def esci_senza_salvare(self):
        if self.righe_da_salvare:
            self.ids.label_errore.text = "Ci sono righe inserite non salvate."
            return
        self.manager.current = "menu"
