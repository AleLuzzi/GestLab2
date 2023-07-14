from kivy.app import App

from kivy.uix.screenmanager import Screen
import datetime
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
import mysql.connector
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.metrics import dp
import controller_db as db

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class SelectableLabel(RecycleDataViewBehavior, Label):
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
        self.selected = is_selected

        rv.data[index]['selected'] = self.selected


class Multicampo_menu(BoxLayout):
    pass


class Nuovo_menu(Screen):
    def __init__(self, **kwargs):
        super(Nuovo_menu, self).__init__(**kwargs)

        oggi = datetime.date.today()
        
        primi = db._recupera_primi()
        secondi = db._recupera_secondi()
        contorni = db._recupera_contorni()

        self.rv_primi.data = [{'label_1': str(x['prodotto']),
                               'label_2': str(x['plu'])} for x in primi]
        
        self.rv_secondi.data = [{'label_1': str(x['prodotto']),
                               'label_2': str(x['plu'])} for x in secondi]
        
        self.rv_contorni.data = [{'label_1': str(x['prodotto']),
                                  'label_2': str(x['plu'])} for x in contorni]

    def indietro(self):
        self.manager.current = 'menu'
