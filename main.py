import kivy.app
from kivy.uix.screenmanager import ScreenManager, Screen, WipeTransition
import sqlite3
import datetime
from kivy.properties import NumericProperty, StringProperty
from kivy.core.window import Window


class menu(Screen):
    def ingresso_merce(self):
        self.manager.current = 'IngressoMerce'

    @staticmethod
    def esci():
        kivy.app.App.get_running_app().stop()


class IngressoMerce(Screen):
    txtinp = NumericProperty(0)
    fornit = StringProperty()
    articolo = StringProperty()
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
        print(self.ids.txtinp.text, self.ids.fornit.text, self.ids.articolo.text)
        self.manager.current = 'menu'


class main(kivy.app.App):
    def build(self):
        Window.size = (800, 400)
        sm = ScreenManager(transition=WipeTransition())
        sm.add_widget(menu(name='menu',))
        sm.add_widget(IngressoMerce(name='IngressoMerce'))
        return sm

main().run()
