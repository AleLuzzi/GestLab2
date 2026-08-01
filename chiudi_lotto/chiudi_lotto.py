import datetime

from kivy.properties import BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

import controller_db as db


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class Multicampo(RecycleDataViewBehavior, MDBoxLayout):
    ''' Add selection support to the row '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(Multicampo, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(Multicampo, self).on_touch_down(touch):
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


class Chiudi_lotto(MDScreen):
    def __init__(self, **kwargs):
        super(Chiudi_lotto, self).__init__(**kwargs)

        oggi = datetime.date.today()

        dati = db._recupera_lotti_aperti()

        self.ids.rv.data = [{'label_1': str(x['number']),
                             'label_2': str(x['fornit']),
                             'label_3': str(x['name']),
                             'label_4': str(x['peso'])} for x in dati]

    def indietro(self):
        self.manager.current = 'menu'

