import datetime

from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.tab import MDTabsItem, MDTabsItemText

from recycleviews import SelectableBox, SelectableLabel

from core.repositories import lotti as lotti_repo
from core.repositories import prodotti as prodotti_repo


class Multicampo_riepilogo_ingresso_merce(SelectableBox):
    ''' Riga selezionabile per il riepilogo ingresso merce. '''


class TabIntestazione(MDBoxLayout):
    pass


class TabCorpo(MDBoxLayout):
    screen = None

    def aggiorna_tagli(self, cat_m):
        self.screen._aggiorna_rv_lista_tagli(cat_m)

    def conferma(self):
        self.screen._selezione()


class TabRiepilogo(MDBoxLayout):
    screen = None

    def cancella_riga(self):
        self.screen._cancella_riga_da_riepilogo()


class Ingresso_merce(MDScreen):
    def __init__(self, **kwargs):
        super(Ingresso_merce, self).__init__(**kwargs)

        self.tab_intestazione = TabIntestazione()
        self.tab_corpo = TabCorpo()
        self.tab_riepilogo = TabRiepilogo()
        self.tab_intestazione.screen = self
        self.tab_corpo.screen = self
        self.tab_riepilogo.screen = self
        self.ids.tabs.add_widget(MDTabsItem(MDTabsItemText(text='Intestazione')))
        self.ids.tabs.add_widget(MDTabsItem(MDTabsItemText(text='Corpo Documento')))
        self.ids.tabs.add_widget(MDTabsItem(MDTabsItemText(text='Riepilogo')))
        self.ids.carousel.add_widget(self.tab_intestazione)
        self.ids.carousel.add_widget(self.tab_corpo)
        self.ids.carousel.add_widget(self.tab_riepilogo)
        Clock.schedule_once(
            lambda x: self.ids.tabs.switch_tab(text='Intestazione'), 1.0)

        oggi = datetime.date.today()

        self.tab_intestazione.ids.label_data.text = str(oggi.strftime('%d/%m/%y'))

        prog_lotto_acq = lotti_repo.recupera_progressivo_ingresso()
        self.tab_intestazione.ids.label_prog_ingresso.text = str(prog_lotto_acq) + 'A'

        lista_fornitori = lotti_repo.recupera_lista_fornitori()
        self.menu_fornitori = MDDropdownMenu(
            caller=self.tab_intestazione.ids.spinner_fornitori,
            items=[
                {
                    'text': fornitore,
                    'on_release': lambda x=fornitore: self._seleziona_fornitore(x),
                }
                for fornitore in lista_fornitori
            ],
        )
        self.tab_intestazione.ids.spinner_fornitori.bind(
            focus=self._on_fornitore_focus)

    def _on_fornitore_focus(self, instance, value):
        if value:
            self.menu_fornitori.open()

    def _seleziona_fornitore(self, fornitore):
        self.tab_intestazione.ids.spinner_fornitori.text = fornitore
        self.menu_fornitori.dismiss()

    def _aggiorna_rv_lista_tagli(self, cat_m):
        self.cat_m = prodotti_repo.recupera_merceologia_da_id(cat_m)
        lista = prodotti_repo.lista_tagli(cat_m)
        self.tab_corpo.ids.rv_articoli.data = [{'text': str(x).upper()} for x in lista]

    def _selezione(self):
        for i in self.tab_corpo.ids.rv_articoli.layout_manager.selected_nodes:
            self.tab_riepilogo.ids.rv_riepilogo_ingresso_merce.data.extend([{
                'label_1': self.tab_corpo.ids.rv_articoli.data[i]['text'],
                'label_2': self.cat_m.upper(),
                'label_3': self.tab_corpo.ids.txtinp_peso.text,
            }])
        self.tab_corpo.ids.txtinp_peso.text = ''
        self.tab_corpo.ids.label_conteggio.text = 'Articoli inseriti ' + str(
            len(self.tab_riepilogo.ids.rv_riepilogo_ingresso_merce.data))

    def _cancella_riga_da_riepilogo(self):
        del self.tab_riepilogo.ids.rv_riepilogo_ingresso_merce.data[
            self.tab_riepilogo.ids.rv_riepilogo_ingresso_merce.layout_manager.selected_nodes[0]]
        self.tab_corpo.ids.label_conteggio.text = 'Articoli inseriti ' + str(
            len(self.tab_riepilogo.ids.rv_riepilogo_ingresso_merce.data))

    def indietro(self):
        self.manager.current = 'menu'
