import kivy.app

from kivy.uix.screenmanager import ScreenManager, Screen, WipeTransition
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
import datetime
from kivy import Config
import configparser
import mysql.connector

Config.set('graphics', 'multisamples', '0')
# Config.set('graphics', 'fullscreen', 'auto')

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
        self.data = [{'text': 'nessuna selezione'}]


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

    def aggiorna_rv(self, cat):
        cat_merc = [cat,]
        lista = []
        query = 'SELECT taglio FROM tagli WHERE Id_Merceologia=%s'
        self.c.execute(query, cat_merc)
        for x in self.c:
            lista.extend(x)
        lista_rv = [{'text': x, 'cat_merc': cat_merc[0]} for x in lista]          
        return lista_rv

    def confermato(self, dat, sli_val):
        index = 0
        while index < len(dat):
            if dat[index]['selected']:
                print(dat[index])
            index += 1
    

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

    lista_fornitori = []

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