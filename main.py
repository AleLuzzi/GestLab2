from kivy import Config
from kivy.uix.screenmanager import ScreenManager, WipeTransition
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from chiudi_lotto import Chiudi_lotto
from ingresso_merce import Ingresso_merce
from lotti_vendita import Lotti_vendita
from nuovo_menu import Nuovo_menu

Config.set('graphics', 'multisamples', '0')


class menu(MDScreen):
    def ingresso_merce(self):
        self.manager.current = 'IngressoMerce'

    def nuovo_lotto(self):
        self.manager.current = 'IngressoMerce'

    def chiudi_lotto(self):
        self.manager.current = 'ChiudiLotto'

    def lotti_vendita(self):
        self.manager.current = 'LottiVendita'

    def nuovo_menu(self):
        self.manager.current = 'NuovoMenu'

    @staticmethod
    def esci():
        MDApp.get_running_app().stop()


class main(MDApp):
    def build(self):
        self.theme_cls.primary_palette = 'Green'
        self.theme_cls.theme_style = 'Light'

        sm = ScreenManager(transition=WipeTransition())
        sm.add_widget(menu(name='menu'))
        sm.add_widget(Ingresso_merce(name='IngressoMerce'))
        sm.add_widget(Chiudi_lotto(name='ChiudiLotto'))
        sm.add_widget(Lotti_vendita(name='LottiVendita'))
        sm.add_widget(Nuovo_menu(name='NuovoMenu'))
        return sm


main().run()

