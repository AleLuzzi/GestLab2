import kivy.app

from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

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
