from kivy.app import App

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button, Label
import datetime
import mysql.connector
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.metrics import dp
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, Rectangle
from kivy.lang import Builder

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
        if is_selected:
            # print("selection changed to {0}".format(rv.data[index]))
            pass
        else:
            # print("selection removed for {0}".format(rv.data[index]))
            pass
        
class Lotti_vendita(Screen):
    def __init__(self, **kwargs):
        super(Lotti_vendita, self).__init__(**kwargs)

        oggi = datetime.date.today()

        self.conn = mysql.connector.connect(host="127.0.0.1",
                                   database="data",
                                   user="root",
                                   password='')

        self.c = self.conn.cursor()

        self.rv.data = [{'text': str(x)} for x in range(8)]
        self.rv2.data = [{'text': str(x)} for x in range(5)]
        print(self.ids)


    def indietro(self):
        self.manager.current = 'menu'
