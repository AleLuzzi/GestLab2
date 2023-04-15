import kivy.app

from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
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
        if is_selected:
            print("selection changed to {0}".format(rv.data[index]))
        else:
            print("selection removed for {0}".format(rv.data[index]))

class RV(RecycleView):
    def __init__(self, **kwargs):
        super(RV, self).__init__(**kwargs)

class Chiudi_lotto(Screen):
    def __init__(self, **kwargs):
        super(Chiudi_lotto, self).__init__(**kwargs)

        ''' DEFINIZIONE BOX ESTERNO E BASSO'''
        
        self.box_esterno = BoxLayout(orientation='horizontal', size_hint=(1, .9), pos_hint={'top':1})
        self.box_basso = BoxLayout(size_hint=(1, .1))
        self.add_widget(self.box_esterno)
        self.add_widget(self.box_basso)

        self.box_sinistra = BoxLayout(orientation='vertical')
        self.box_destra = BoxLayout(orientation='vertical')
        self.box_esterno.add_widget(self.box_sinistra)
        self.box_esterno.add_widget(self.box_destra)

        ''' DEFINIZIONE BTN INDIETRO '''

        self.btn = Button(text='indietro')
        self.box_basso.add_widget(self.btn)
        self.btn.bind(on_press=self.indietro)

        ''' DEFINIZIONE LABEL E RECYCLEVIEW BOX SINISTRA'''

        self.lbl_lista_lotti = Button(text='Lotti aperti')
        self.box_sinistra.add_widget(self.lbl_lista_lotti)

    def indietro(self, instance):
        self.manager.current = 'menu'
