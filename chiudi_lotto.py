from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
import datetime
import mysql.connector
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.metrics import dp


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

class Multicampo(BoxLayout):
    pass

items = [{'number': '20230V', 'name': 'Spalla', 'size': '1.50 ', 'in_stock': True},
         {'number': '20240V', 'name': 'Costine', 'size': '1.60 ', 'in_stock': False},
         {'number': '20250V', 'name': 'Guanciali', 'size': '1.30 ', 'in_stock': True},
         {'number': '20260V', 'name': 'Busto', 'size': '1.40 ', 'in_stock': True}
        ]

class Chiudi_lotto(Screen):
    def __init__(self, **kwargs):
        super(Chiudi_lotto, self).__init__(**kwargs)

        oggi = datetime.date.today()
        
        self.conn = mysql.connector.connect(host="127.0.0.1",
                                   database="data",
                                   user="root",
                                   password='')

        self.c = self.conn.cursor()

        # self.rv.data = [{'text': str(x)} for x in range(10)]
        self.rv.data = [{'label_1': str(x['number']), 
                         'label_2': str(x['name']), 
                         'label_3': str(x['size']), 
                         'checkbox_1': x['in_stock']} for x in items]

    def indietro(self):
        self.manager.current = 'menu'
