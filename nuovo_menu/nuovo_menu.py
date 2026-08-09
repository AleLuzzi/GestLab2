import datetime

from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.tab import MDTabsItem, MDTabsItemText

from recycleviews import SelectableBox

from core.repositories import prodotti as prodotti_repo


class Multicampo_menu(SelectableBox):
    ''' Riga selezionabile per la scelta degli articoli del menu. '''


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

        primi = prodotti_repo.recupera_primi()
        secondi = prodotti_repo.recupera_secondi()
        contorni = prodotti_repo.recupera_contorni()

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
