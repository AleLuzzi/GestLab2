import kivy.app

from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

class Chiudi_lotto(Screen):
    def __init__(self, **kwargs):
        super(Chiudi_lotto, self).__init__(**kwargs)
        self.btn = Button(text='indietro')
        self.add_widget(self.btn)
        self.btn.bind(on_press=self.indietro)

    def indietro(self, instance):
        self.manager.current = 'menu'
