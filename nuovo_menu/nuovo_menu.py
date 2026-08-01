import datetime

from kivy.clock import Clock
from kivy.properties import BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.tab import MDTabsItem, MDTabsItemText

import controller_db as db


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class Multicampo_menu(RecycleDataViewBehavior, MDBoxLayout):
    ''' Add selection support to the row '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(Multicampo_menu, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(Multicampo_menu, self).on_touch_down(touch):
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


class TabPrimi(MDBoxLayout):
    pass


class TabSecondi(MDBoxLayout):
    pass


class TabContorni(MDBoxLayout):
    pass


class TabRiepilogoMenu(MDBoxLayout):
    pass


class Nuovo_menu(MDScreen):
    def __init__(self, **kwargs):
        super(Nuovo_menu, self).__init__(**kwargs)

        self.tab_primi = TabPrimi()
        self.tab_secondi = TabSecondi()
        self.tab_contorni = TabContorni()
        self.tab_riepilogo = TabRiepilogoMenu()
        self.ids.tabs.add_widget(MDTabsItem(MDTabsItemText(text='Primi')))
        self.ids.tabs.add_widget(MDTabsItem(MDTabsItemText(text='Secondi')))
        self.ids.tabs.add_widget(MDTabsItem(MDTabsItemText(text='Contorni')))
        self.ids.tabs.add_widget(MDTabsItem(MDTabsItemText(text='Riepilogo')))
        self.ids.carousel.add_widget(self.tab_primi)
        self.ids.carousel.add_widget(self.tab_secondi)
        self.ids.carousel.add_widget(self.tab_contorni)
        self.ids.carousel.add_widget(self.tab_riepilogo)
        Clock.schedule_once(
            lambda x: self.ids.tabs.switch_tab(text='Primi'), 1.0)

        oggi = datetime.date.today()

        primi = db._recupera_primi()
        secondi = db._recupera_secondi()
        contorni = db._recupera_contorni()

        self.tab_primi.ids.rv_primi.data = [{'label_1': str(x['prodotto'].upper()),
                                             'label_2': str(x['plu'])} for x in primi]

        self.tab_secondi.ids.rv_secondi.data = [{'label_1': str(x['prodotto'].upper()),
                                                 'label_2': str(x['plu'])} for x in secondi]

        self.tab_contorni.ids.rv_contorni.data = [{'label_1': str(x['prodotto'].upper()),
                                                   'label_2': str(x['plu'])} for x in contorni]

    def _aggiorna_rv_riepilogo(self):
        if not hasattr(self, 'tab_riepilogo') or not hasattr(self, 'tab_primi'):
            return
        riepilogo = []
        for i in self.tab_primi.ids.rv_primi.layout_manager.selected_nodes:
            riepilogo.append(self.tab_primi.ids.rv_primi.data[i]['label_1'])

        for i in self.tab_secondi.ids.rv_secondi.layout_manager.selected_nodes:
            riepilogo.append(self.tab_secondi.ids.rv_secondi.data[i]['label_1'])

        for i in self.tab_contorni.ids.rv_contorni.layout_manager.selected_nodes:
            riepilogo.append(self.tab_contorni.ids.rv_contorni.data[i]['label_1'])

        self.tab_riepilogo.ids.rv_riepilogo.data = [{'label_1': str(x).upper()} for x in riepilogo]

    def indietro(self):
        self.manager.current = 'menu'

