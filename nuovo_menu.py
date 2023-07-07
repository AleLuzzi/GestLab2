from kivy.app import App

from kivy.uix.screenmanager import Screen
import datetime

class Nuovo_menu(Screen):
    def __init__(self, **kwargs):
        super(Nuovo_menu, self).__init__(**kwargs)

        oggi = datetime.date.today()

    def indietro(self):
        self.manager.current = 'menu'
