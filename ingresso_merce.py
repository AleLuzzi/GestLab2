from kivy.app import App

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button, Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
import datetime
import mysql.connector
from kivy.properties import BooleanProperty
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.metrics import dp
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.uix.popup import Popup
import controller_db as db

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
        if is_selected:
            print("selection changed to {0}".format(rv.data[index]))
        else:
            print("selection removed for {0}".format(rv.data[index]))

class Ingresso_merce(Screen):
    def __init__(self, **kwargs):
        super(Ingresso_merce, self).__init__(**kwargs)

        oggi = datetime.date.today()

        self.ids.label_data.text = str(oggi.strftime('%d/%m/%y'))

        prog_lotto_acq = db._recupera_progressivo_ingresso()
        self.ids.label_prog_ingresso.text = str(prog_lotto_acq)+'A'

        lista_fornitori = db._recupera_lista_fornitori()
        self.ids.spinner_fornitori.values = lista_fornitori

    def _aggiorna_rv_lista_tagli(self, cat_m):
        self.cat_m = cat_m
        lista = db._lista_tagli(cat_m)
        self.ids.rv_articoli.data = [{'text': str(x).upper()} for x in lista]

    def _selezione(self):
        for i in self.ids.rv_articoli.layout_manager.selected_nodes:
            print(self.ids.rv_articoli.data[i]['text'])
        # print(self.cat_m)

    def indietro(self):
        self.manager.current = 'menu'

        ''' INIZIALIZZO LISTE CHE CONTIENGONO LE SELEZIONI '''
        self.lista_righe_riepilogo = []
        self.lista_selezioni = []
        self.lista_riepilogo = []
        self.tot_articoli = 0
        
    def conferma_selezione(self, dat):
        #TODO: aggiungere i controlli
        index = 0
        while index < len(dat):
            if dat[index]['selected']:
                self.tot_articoli += 1
                dat[index]['merc'] = self._recupera_merceologia(dat[index]['cat_merc'])
                dat[index]['peso'] = self.txtinp_peso_ricevuto.text
                dat[index]['riga'] = self.tot_articoli
                self.lista_riepilogo.append(dat[index])
                break
            index += 1
        # self.lbl_conteggio_selezioni.text = f"Articoli \nInseriti:\n     {self._conta_articoli_inseriti(self.lista_riepilogo)}"
        # self.txtinp_peso_ricevuto.text=str('')
        '''
        else:
            content= Button(text="Mancano dati \n CONTROLLA")
            popup = Popup(title = 'ATTENZIONE !!!',
                          content=content,
                          auto_dismiss=False,
                          size_hint=(None, None), size=(400, 400))
            content.bind(on_press=popup.dismiss)
            popup.open()
        '''

    def _aggiorna_rv_riepilogo(self, dat):
        return [{'lbl_1': str(x['text']), 'lbl_2': str(x['merc']), 
                 'lbl_3': str(x['peso']), 'lbl_4': str(x['riga'])} for x in dat]
    
    def _conta_articoli_inseriti(self, dat):
        return len(dat)
    
    def _recupera_merceologia(self, cat):
        self.c.execute("SELECT merceologia FROM merceologie WHERE Id = %s", [cat,])
        merc = self.c.fetchone()[0]
        return merc
    
    def _recupera_righe_selezionate(self): 
        righe = []
        if self.lista_riepilogo:
            for dic in self.lista_riepilogo:
                righe.append(str(dic['riga']))
        else:
            return '0'
        return righe
    
    def _salva_dati(self, arg):
        #TODO aggiungere controlli
        lista = [] 
        '''
        data = arg
        
        for dic in data:
            lista.append([str(self.prog_lotto_acq)+'A', 
                          self.oggi, 
                          self.txtinput_num_documento.text, 
                          self.spinner_fornitori.text, 
                          dic['text'], 
                          dic['peso'], 
                          dic['peso'], 
                          'no'])
        '''
        sql_ins = "INSERT INTO ingresso_merce VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        self.c.executemany(sql_ins, lista)
        self.conn.commit()
        sql_update = "UPDATE progressivi SET prog_acq = %s"
        self.c.execute(sql_update, (self.prog_lotto_acq + 1,))
        self.conn.commit()
        self.conn.close()
        
    