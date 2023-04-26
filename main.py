from kivy.app import App

from kivy.uix.screenmanager import ScreenManager, Screen, WipeTransition
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy import Config
import configparser
from chiudi_lotto import Chiudi_lotto
from ingresso_merce import Ingresso_merce

Config.set('graphics', 'multisamples', '0')
# Config.set('graphics', 'fullscreen', 'auto')

class menu(Screen):
    def ingresso_merce(self):
        self.manager.current = 'IngressoMerce'

    def chiudi_lotto(self):
        self.manager.current = 'ChiudiLotto'

    @staticmethod
    def esci():
        App.get_running_app().stop()

    
class main(App):
    def build(self):
        sm = ScreenManager(transition=WipeTransition())
        sm.add_widget(menu(name='menu'))
        sm.add_widget(Ingresso_merce(name='IngressoMerce'))
        sm.add_widget(Chiudi_lotto(name='ChiudiLotto'))
        return sm

main().run()