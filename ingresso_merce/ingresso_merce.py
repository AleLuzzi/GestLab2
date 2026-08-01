import datetime

from kivy.clock import Clock
from kivy.properties import BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.tab import MDTabsItem, MDTabsItemText

import controller_db as db


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class Multicampo_riepilogo_ingresso_merce(RecycleDataViewBehavior, MDBoxLayout):
    ''' Add selection support to the row '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(Multicampo_riepilogo_ingresso_merce, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(Multicampo_riepilogo_ingresso_merce, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        prev_selected = rv.data[index].get('selected', False)
        self.selected = is_selected
        rv.data[index]['selected'] = is_selected
        if prev_selected != is_selected:
            if is_selected:
                print("selection changed to {0}".format(rv.data[index]))
            else:
                print("selection removed for {0}".format(rv.data[index]))


class SelectableLabel(RecycleDataViewBehavior, MDLabel):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(SelectableLabel, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        prev_selected = rv.data[index].get('selected', False)
        self.selected = is_selected
        rv.data[index]['selected'] = is_selected
        if prev_selected != is_selected:
            if is_selected:
                print("selection changed to {0}".format(rv.data[index]))
            else:
                print("selection removed for {0}".format(rv.data[index]))


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

        prog_lotto_acq = db._recupera_progressivo_ingresso()
        self.tab_intestazione.ids.label_prog_ingresso.text = str(prog_lotto_acq) + 'A'

        lista_fornitori = db._recupera_lista_fornitori()
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
        self.cat_m = db._recupera_merceologia_da_id(cat_m)
        lista = db._lista_tagli(cat_m)
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

