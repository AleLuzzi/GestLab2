import kivy.app

from kivy.uix.screenmanager import ScreenManager, Screen, WipeTransition
from kivy.uix.recycleview import RecycleView
import datetime
from kivy.properties import NumericProperty, StringProperty
from kivy import Config
import configparser
import mysql.connector

Config.set('graphics', 'multisamples', '0')
# Config.set('graphics', 'fullscreen', 'auto')

class RV(RecycleView):
    def __init__(self, **kwargs):
        super(RV, self).__init__(**kwargs)
        self.data = [{'text': str(x)} for x in range(20)]


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

    def indietro(self):
        # print(self.ids.txtinp.text, self.ids.fornit.text, self.ids.articolo.text)
        self.manager.current = 'menu'

    def leggi_file_ini():
        ini = configparser.ConfigParser()
        ini.read('config.ini')
        return ini

    # config_ini = leggi_file_ini()

    conn = mysql.connector.connect(host="192.168.0.100",
                                   database="data",
                                   user="root",
                                   password='')

    c = conn.cursor()

   # lista_tagli = []
    lista_fornitori = []

   # c.execute("SELECT taglio FROM tagli")

   # for lista in c:
   #     lista_tagli.extend(lista)

    c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1")

    for lista in c:
        lista_fornitori.extend(lista)

    c.execute("SELECT prog_acq FROM progressivi")
    prog_lotto_acq = c.fetchone()[0]

    oggi = datetime.date.today()


class main(kivy.app.App):
    def build(self):
        sm = ScreenManager(transition=WipeTransition())
        sm.add_widget(menu(name='menu'))
        sm.add_widget(IngressoMerce(name='IngressoMerce'))
        return sm

main().run()