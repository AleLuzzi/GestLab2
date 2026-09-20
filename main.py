"""Applicazione principale GestLab2 - Gestione Laboratorio.

Punto di ingresso dell'applicazione KivyMD: crea lo ScreenManager
e registra tutte le schermate del modulo.
"""

from kivy import Config

# Config deve essere impostata prima di qualsiasi altra importazione Kivy
# per garantire che le opzioni grafiche siano applicate correttamente.
Config.set('graphics', 'multisamples', '0')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, WipeTransition
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from desktop.anag_dipendenti import Anag_dipendenti
from desktop.anag_merceologie import Anag_merceologie
from desktop.anag_reparti import Anag_reparti
from desktop.anag_tagli import Anag_tagli
from desktop.chiudi_lotto import Chiudi_lotto
from desktop.ingresso_merce import Ingresso_merce
from desktop.lotti_vendita import Lotti_vendita
from desktop.nuovo_menu import Nuovo_menu

# --------------------------------------------------------------------------- #
#  Costanti: nomi delle schermate (evita magic string sparse nel codice)
# --------------------------------------------------------------------------- #
SCREEN_MENU = 'menu'
SCREEN_INGRESSO_MERCE = 'IngressoMerce'
SCREEN_CHIUDI_LOTTO = 'ChiudiLotto'
SCREEN_LOTTI_VENDITA = 'LottiVendita'
SCREEN_NUOVO_MENU = 'NuovoMenu'
SCREEN_ANAG_DIPENDENTI = 'AnagDipendenti'
SCREEN_ANAG_MERCEOLOGIE = 'AnagMerceologie'
SCREEN_ANAG_REPARTI = 'AnagReparti'
SCREEN_ANAG_TAGLI = 'AnagTagli'


class Menu(MDScreen):
    """Schermata principale con la griglia di navigazione alle funzioni."""

    def _vai_a(self, nome_schermata):
        """Naviga verso la schermata indicata."""
        self.manager.current = nome_schermata

    def ingresso_merce(self):
        """Apre la schermata Ingresso Merce."""
        self._vai_a(SCREEN_INGRESSO_MERCE)

    def nuovo_lotto(self):
        """Apre la schermata per il nuovo lotto (riusa Ingresso Merce)."""
        self._vai_a(SCREEN_INGRESSO_MERCE)

    def chiudi_lotto(self):
        """Apre la schermata Chiudi Lotti."""
        self._vai_a(SCREEN_CHIUDI_LOTTO)

    def lotti_vendita(self):
        """Apre la schermata Vendita Lotti."""
        self._vai_a(SCREEN_LOTTI_VENDITA)

    def nuovo_menu(self):
        """Apre la schermata Nuovo Menu."""
        self._vai_a(SCREEN_NUOVO_MENU)

    def anag_dipendenti(self):
        """Apre la schermata Anagrafica Dipendenti."""
        self._vai_a(SCREEN_ANAG_DIPENDENTI)

    def anag_merceologie(self):
        """Apre la schermata Anagrafica Merceologie."""
        self._vai_a(SCREEN_ANAG_MERCEOLOGIE)

    def anag_reparti(self):
        """Apre la schermata Anagrafica Reparti."""
        self._vai_a(SCREEN_ANAG_REPARTI)

    def anag_tagli(self):
        """Apre la schermata Anagrafica Tagli."""
        self._vai_a(SCREEN_ANAG_TAGLI)

    @staticmethod
    def esci():
        """Termina l'applicazione."""
        App.get_running_app().stop()


class MainApp(MDApp):
    """Applicazione GestLab2: configura il tema e lo ScreenManager."""

    def build(self):
        """Costruisce l'albero dei widget e lo ScreenManager."""
        self.theme_cls.primary_palette = 'Green'
        self.theme_cls.theme_style = 'Light'

        sm = ScreenManager(transition=WipeTransition())
        sm.add_widget(Menu(name=SCREEN_MENU))
        sm.add_widget(Ingresso_merce(name=SCREEN_INGRESSO_MERCE))
        sm.add_widget(Chiudi_lotto(name=SCREEN_CHIUDI_LOTTO))
        sm.add_widget(Lotti_vendita(name=SCREEN_LOTTI_VENDITA))
        sm.add_widget(Nuovo_menu(name=SCREEN_NUOVO_MENU))
        sm.add_widget(Anag_dipendenti(name=SCREEN_ANAG_DIPENDENTI))
        sm.add_widget(Anag_merceologie(name=SCREEN_ANAG_MERCEOLOGIE))
        sm.add_widget(Anag_reparti(name=SCREEN_ANAG_REPARTI))
        sm.add_widget(Anag_tagli(name=SCREEN_ANAG_TAGLI))
        return sm


if __name__ == '__main__':
    MainApp().run()

