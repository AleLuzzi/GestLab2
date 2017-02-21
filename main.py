from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, WipeTransition
import sqlite3
import datetime


class menu(Screen):
    def ingresso_merce(self):
        self.manager.current = 'IngressoMerce'

    @staticmethod
    def esci():
        App.get_running_app().stop()


class IngressoMerce(Screen):
    # Connessione al database
    conn = sqlite3.connect('./data.db',
                           detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    c = conn.cursor()

    lista_tagli = []
    lista_fornitori = []

    for lista in c.execute("SELECT taglio FROM tagli"):
        lista_tagli.extend(lista)

    for lista in c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1"):
        lista_fornitori.extend(lista)

    c.execute("SELECT prog_acq FROM progressivi")
    prog_lotto_acq = c.fetchone()[0]

    data = datetime.date.today()

    def indietro(self):
        self.manager.current = 'menu'


class main(App):
    def build(self):
        sm = ScreenManager(transition=WipeTransition())
        sm.add_widget(menu(name='menu'))
        sm.add_widget(IngressoMerce(name='IngressoMerce'))
        return sm

main().run()
