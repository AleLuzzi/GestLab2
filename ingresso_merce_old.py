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
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.metrics import dp
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.uix.popup import Popup

Builder.load_string("""

<SelectableLabel>:
    # Draw a background to indicate selection
    canvas.before:
        Color:
            rgba: (.05, 0.5, .9, .8) if self.selected else (.5, .5, .5, 1)
        Rectangle:
            pos: self.pos
            size: self.size

<RvMultiCampo>:
    orientation: 'horizontal'
    lbl_1: ''
    lbl_2: ''
    lbl_3: ''
    lbl_4: ''
    Label:
        text: root.lbl_1
    Label:
        text: root.lbl_2
    Label:
        text: root.lbl_3
    Label:
        text: root.lbl_4
""")

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class SelectableRecycleGridLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleGridLayout):
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
            # print("selection changed to {0}".format(rv.data[index]))
            pass
        else:
            # print("selection removed for {0}".format(rv.data[index]))
            pass


class RvMultiCampo(BoxLayout):
    pass


class RV(RecycleView):
    def __init__(self, **kwargs):
        super(RV, self).__init__(**kwargs)

class MyLabel(Label):
    def on_size(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(.05, .05, .9, .8)
            Rectangle(pos=self.pos, size=self.size)
        
class Ingresso_merce(Screen):
    def __init__(self, **kwargs):
        super(Ingresso_merce, self).__init__(**kwargs)

        self.oggi = datetime.date.today()

        self.conn = mysql.connector.connect(host="192.168.0.100",
                                   database="db_prova",
                                   user="prova",
                                   password='')

        self.c = self.conn.cursor()

        ''' INIZIALIZZO LISTE CHE CONTIENGONO LE SELEZIONI '''
        lista_fornitori = []
        self.lista_righe_riepilogo = []
        self.lista_selezioni = []
        self.lista_riepilogo = []
        self.tot_articoli = 0
        
        self.prog_lotto_acq = self._recupera_progressivo_ingresso()

        lista_fornitori = self._recupera_lista_fornitori()

        ''' DEFINIZIONE BTN INDIETRO COMUNE A TUTTI I TAB '''

        self.btn = Button(text='indietro', size_hint=(1,.1))        
        self.btn.bind(on_press=self.indietro)
        self.add_widget(self.btn)
        
        ''' DEFINIZIONE TAB PANEL '''
        
        self.tab_panel = TabbedPanel(do_default_tab=(False), 
                                    size_hint=(1,.9), pos_hint={'top':1})
        self.tab_panel_tab1 = TabbedPanelItem(text='Intestazione')
        self.tab_panel_tab2 = TabbedPanelItem(text='Corpo \n Documento')
        self.tab_panel_tab2.bind(on_press=lambda x:self._tab2_premuto())
        self.tab_panel_tab3 = TabbedPanelItem(text='Riepilogo')
        self.tab_panel_tab3.bind(on_press=lambda x:self._tab3_premuto())
        
        self.add_widget(self.tab_panel)
        self.tab_panel.add_widget(self.tab_panel_tab1)
        self.tab_panel.add_widget(self.tab_panel_tab2)
        self.tab_panel.add_widget(self.tab_panel_tab3)

        ''' DEFINIZIONE BOX E WIDGET CONTENUTI NEL TAB1 -INTESTAZIONE- '''
        
        self.box_layout_tab1 = BoxLayout(orientation='vertical')

        self.lbl_progressivo_lotto_ingresso_txt = MyLabel(text='Progressivo Lotto ingresso')
        self.lbl_progressivo_ingresso = Label(text=str(self.prog_lotto_acq)+'V')
        self.lbl_fornitore_txt = MyLabel(text='Fornitore')
        self.spinner_fornitori = Spinner(values=lista_fornitori)
        self.lbl_data_txt = MyLabel(text='Data Documento')
        self.lbl_data = Label(text=str(self.oggi.strftime('%d/%m/%y')))
        self.lbl_num_documento = MyLabel(text='Numero Documento')
        self.txtinput_num_documento = TextInput(font_size=40)

        self.box_layout_tab1.add_widget(self.lbl_progressivo_lotto_ingresso_txt)
        self.box_layout_tab1.add_widget(self.lbl_progressivo_ingresso)
        self.tab_panel_tab1.add_widget(self.box_layout_tab1)
        self.box_layout_tab1.add_widget(self.lbl_fornitore_txt)
        self.box_layout_tab1.add_widget(self.spinner_fornitori)
        self.box_layout_tab1.add_widget(self.lbl_data_txt)
        self.box_layout_tab1.add_widget(self.lbl_data)
        self.box_layout_tab1.add_widget(self.lbl_num_documento)
        self.box_layout_tab1.add_widget(self.txtinput_num_documento)

        ''' DEFINIZIONE BOX ESTERNO TAB2 - CORPO DOCUMENTO '''
        
        self.box_esterno = BoxLayout(orientation='horizontal')
        self.tab_panel_tab2.add_widget(self.box_esterno)

        self.box_sinistra = BoxLayout(orientation='vertical')
        self.box_destra = BoxLayout(orientation='vertical')
        self.box_esterno.add_widget(self.box_sinistra)
        self.box_esterno.add_widget(self.box_destra)

        ''' DEFINIZIONE BOX E TOGGLE BUTTON PER SCELTA CAT MERCEOLOGICA '''
        
        self.box_layout_toggle_btn = BoxLayout(orientation='horizontal', size_hint=(1, .1))

        self.tgl_btn1 = ToggleButton(text='Agnello', group='merceologia', size_hint=(.25, 1), pos_hint={"top":1})
        self.tgl_btn1.bind(on_press=lambda x:self.aggiorna_rv('12'))
        self.tgl_btn2 = ToggleButton(text='Bovino', group='merceologia', size_hint=(.25, 1), pos_hint={"top":1})
        self.tgl_btn2.bind(on_press=lambda x:self.aggiorna_rv('10'))
        self.tgl_btn3 = ToggleButton(text='Vitello', group='merceologia', size_hint=(.25, 1), pos_hint={"top":1})
        self.tgl_btn3.bind(on_press=lambda x:self.aggiorna_rv('13'))
        self.tgl_btn4 = ToggleButton(text='Suino', group='merceologia', size_hint=(.25, 1), pos_hint={"top":1})
        self.tgl_btn4.bind(on_press=lambda x:self.aggiorna_rv('11'))
        
        self.box_layout_toggle_btn.add_widget(self.tgl_btn1)
        self.box_layout_toggle_btn.add_widget(self.tgl_btn2)
        self.box_layout_toggle_btn.add_widget(self.tgl_btn3)
        self.box_layout_toggle_btn.add_widget(self.tgl_btn4)

        ''' DEFINIZIONE BOX E RECYCLEVIEW '''
        
        self.box_layout_recicleview = BoxLayout(orientation='vertical')

        recycle_box_layout = SelectableRecycleBoxLayout(default_size=(None, dp(50)), default_size_hint=(1, None),
                                                        size_hint=(1, None), orientation='vertical', multiselect='False')
        recycle_box_layout.bind(minimum_height=recycle_box_layout.setter("height"))
        self.mostra_dati = RV()
        self.mostra_dati.add_widget(recycle_box_layout)
        self.mostra_dati.viewclass= 'SelectableLabel'
        
        self.box_layout_recicleview.add_widget(self.mostra_dati)

        ''' BOXLAYOUT SINISTRO CON TOGGLE BTN E RECYCLEVIEW'''

        self.box_sinistra.add_widget(self.box_layout_toggle_btn)
        self.box_sinistra.add_widget(self.box_layout_recicleview)

        ''' BOXLAYOUT DESTRO '''

        self.btn_quantita_richiesta = Label(text='Quantità ricevuta', size_hint=(1, .1), pos_hint={"top":1})
        self.box_destra.add_widget(self.btn_quantita_richiesta)

        ''' DEFINIZIONE BOXLAYOUT E TOGGLE_BTN PER SELEZIONE KG/PZ'''

        self.box_kg_pz = BoxLayout(orientation='horizontal', size_hint=(1, .1), pos_hint={'top':1})
        self.tgl_btn_kg = ToggleButton(text='Kg', group='peso', state='down')
        self.tgl_btn_pz = ToggleButton(text='Pz', group='peso')
        
        self.box_destra.add_widget(self.box_kg_pz)
        self.box_kg_pz.add_widget(self.tgl_btn_kg)
        self.box_kg_pz.add_widget(self.tgl_btn_pz)

        ''' DEFINIZIONE BOXLAYOUT E SLIDER PER INSERIMENTO PESO ORDINATO'''

        self.box_txtinp_peso_ricevuto = BoxLayout(orientation='vertical', size_hint=(1, .1), pos_hint={'top':1})
        self.txtinp_peso_ricevuto = TextInput(font_size=40, text='', multiline=False, hint_text='inserisci il peso qui', input_type='number')
        
        self.box_destra.add_widget(self.box_txtinp_peso_ricevuto)
        self.box_txtinp_peso_ricevuto.add_widget(self.txtinp_peso_ricevuto)
        
        ''' DEFINIZIONE BOXLAYOUT E BOTTONI PER INSERIMENTO PESO VELOCE'''

        self.box_btn_peso_veloce = BoxLayout(orientation='horizontal', size_hint=(1, .1), pos_hint={'top':1})
        self.btn_peso_veloce_1 = Button(text='0.5')
        self.btn_peso_veloce_1.bind(on_press=lambda x:self.pressione_btn_peso_veloce(value=0.5))
        self.btn_peso_veloce_2 = Button(text='1')
        self.btn_peso_veloce_2.bind(on_press=lambda x:self.pressione_btn_peso_veloce(value=1))
        self.btn_peso_veloce_3 = Button(text='1.5')
        self.btn_peso_veloce_3.bind(on_press=lambda x:self.pressione_btn_peso_veloce(value=1.5))
        self.btn_peso_veloce_4 = Button(text='2')
        self.btn_peso_veloce_4.bind(on_press=lambda x:self.pressione_btn_peso_veloce(value=2))

        self.box_destra.add_widget(self.box_btn_peso_veloce)
        self.box_btn_peso_veloce.add_widget(self.btn_peso_veloce_1)
        self.box_btn_peso_veloce.add_widget(self.btn_peso_veloce_2)
        self.box_btn_peso_veloce.add_widget(self.btn_peso_veloce_3)
        self.box_btn_peso_veloce.add_widget(self.btn_peso_veloce_4)

        ''' BOTTONE CONFERMA SELEZIONI  E CONTEGGIO ARTICOLI INSERITI TAB2 - CORPO DOCUMENTO'''

        self.box_tot_e_conferma_selezioni = BoxLayout(orientation='horizontal', size_hint=(1, .1), pos_hint={'top':1})
        self.btn_conferma_selezioni = Button(text='Conferma', size_hint=(.75, 1))
        self.lbl_conteggio_selezioni = Label(text='Articoli \n Inseriti', size_hint=(.25, 1))
        self.btn_conferma_selezioni.bind(on_press=lambda x:self.conferma_selezione(self.mostra_dati.data))
        self.box_destra.add_widget(self.box_tot_e_conferma_selezioni)
        self.box_tot_e_conferma_selezioni.add_widget(self.btn_conferma_selezioni)
        self.box_tot_e_conferma_selezioni.add_widget(self.lbl_conteggio_selezioni)

        ''' DEFINIZIONE BOX ESTERNO TAB3 - RIEPILOGO '''
        self.box_esterno_riepilogo = BoxLayout(orientation='horizontal')
        self.tab_panel_tab3.add_widget(self.box_esterno_riepilogo)

        self.box_sinistra_riepilogo = BoxLayout(orientation='vertical')
        self.box_destra_riepilogo = BoxLayout(orientation='vertical')

        self.box_esterno_riepilogo.add_widget(self.box_sinistra_riepilogo)
        self.box_esterno_riepilogo.add_widget(self.box_destra_riepilogo)

        '''BOX E RECYCLEVIEW TAB 3 PER RIEPILOGO '''

        self.grid_intestazione_colonne = GridLayout(cols=4, size_hint=(1, 0.1))
        self.lbl1 = MyLabel(text='ARTICOLO')
        self.lbl2 = MyLabel(text='MERCEOLOGIA')
        self.lbl3 = MyLabel(text='PESO')
        self.lbl4 = MyLabel(text='RIGA')

        self.grid_intestazione_colonne.add_widget(self.lbl1)
        self.grid_intestazione_colonne.add_widget(self.lbl2)
        self.grid_intestazione_colonne.add_widget(self.lbl3)
        self.grid_intestazione_colonne.add_widget(self.lbl4)


        self.box_layout_recicleview_riepilogo = BoxLayout(orientation='vertical')

        recycle_box_layout_riepilogo = RecycleBoxLayout(default_size=(None, dp(20)), default_size_hint=(1, None),
                                                        size_hint=(1,None), orientation='vertical')
        recycle_box_layout_riepilogo.bind(minimum_height=recycle_box_layout_riepilogo.setter("height"))
        self.mostra_dati_riepilogo = RV()
        self.mostra_dati_riepilogo.add_widget(recycle_box_layout_riepilogo)
        self.mostra_dati_riepilogo.viewclass= 'RvMultiCampo'

        self.box_layout_recicleview_riepilogo.add_widget(self.mostra_dati_riepilogo)
        self.box_sinistra_riepilogo.add_widget(self.grid_intestazione_colonne)
        self.box_sinistra_riepilogo.add_widget(self.box_layout_recicleview_riepilogo)

        ''' BTN PER MODIFICA RIEPILOGO TAB3'''
        self.box_cancella_riga = BoxLayout(orientation='vertical', size_hint=(1, 0.1))
        self.lbl_cancella_riga = Label(text='cancella riga')

        self.grid_riga_da_cancellare = GridLayout(cols = 2)
        self.spinner_riga_da_cancellare = Spinner(text='seleziona riga', values = self.lista_righe_riepilogo, size_hint=(0.3, None))
        self.btn_conferma_cancella = Button(text='conferma', size_hint=(0.3, None))
        self.btn_conferma_cancella.bind(on_press=lambda x:self._cancella_riga_da_spinner(self.spinner_riga_da_cancellare.text))

        self.box_salva_dati = BoxLayout(size_hint_y=(.3) )
        self.btn_salva_dati = Button(text='Salva dati')
        self.btn_salva_dati.bind(on_press=lambda x:self._salva_dati(self.lista_riepilogo))
        
        self.box_cancella_riga.add_widget(self.lbl_cancella_riga)
        self.grid_riga_da_cancellare.add_widget(self.spinner_riga_da_cancellare)
        self.grid_riga_da_cancellare.add_widget(self.btn_conferma_cancella)
        self.box_salva_dati.add_widget(self.btn_salva_dati)
        
        self.box_destra_riepilogo.add_widget(self.box_cancella_riga)
        self.box_destra_riepilogo.add_widget(self.grid_riga_da_cancellare)
        self.box_destra_riepilogo.add_widget(self.box_salva_dati)

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
        self.lbl_conteggio_selezioni.text = f"Articoli \nInseriti:\n     {self._conta_articoli_inseriti(self.lista_riepilogo)}"
        self.txtinp_peso_ricevuto.text=str('')
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

    def pressione_btn_peso_veloce(self, value):
        self.txtinp_peso_ricevuto.text = str(value)
        
    def aggiorna_rv(self, cat):
        self.lista_selezioni.clear()
        self.c = self.conn.cursor()
        cat_merc = [cat,]
        query = 'SELECT taglio FROM tagli WHERE Id_Merceologia=%s'
        self.c.execute(query, cat_merc)
        for x in self.c:
            self.lista_selezioni.extend(x)
        self.mostra_dati.data = [{'text': x, 'cat_merc': cat_merc[0]} for x in self.lista_selezioni]

    def _aggiorna_rv_riepilogo(self, dat):
        return [{'lbl_1': str(x['text']), 'lbl_2': str(x['merc']), 
                 'lbl_3': str(x['peso']), 'lbl_4': str(x['riga'])} for x in dat]
    
    def _conta_articoli_inseriti(self, dat):
        return len(dat)
    
    def _tab2_premuto(self):
        if self.txtinput_num_documento.text != '' and self.spinner_fornitori.text != '':
            pass
        else:
            content= Button(text="Mancano dati nell'intestazione documento \n torna indietro")
            popup = Popup(title = 'ATTENZIONE !!!',
                          content=content,
                          auto_dismiss=False,
                          size_hint=(None, None), size=(400, 400))
            content.bind(on_press=popup.dismiss)
            popup.open()
        
    def _tab3_premuto(self):
        self.lista_righe_riepilogo = self._recupera_righe_selezionate()
        self.spinner_riga_da_cancellare.values = self.lista_righe_riepilogo
        self.mostra_dati_riepilogo.data = self._aggiorna_rv_riepilogo(self.lista_riepilogo)
        
    def _recupera_progressivo_ingresso(self):
        self.c.execute("SELECT prog_acq FROM progressivi")
        prog_ingresso = self.c.fetchone()[0]
        return prog_ingresso
    
    def _recupera_lista_fornitori(self):
        self.c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1")
        fornitori = []
        for lista in self.c:
            fornitori.extend(lista)
        return fornitori
    
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
    
    def _cancella_riga_da_spinner(self, val):
        if self.lista_riepilogo:
            i = 0
            for i in range(len(self.lista_riepilogo)):
                if str(self.lista_riepilogo[i]['riga']) == self.spinner_riga_da_cancellare.text:
                    del self.lista_riepilogo[i]
                    break
        self.mostra_dati_riepilogo.data.clear()
        self.mostra_dati_riepilogo.data = self._aggiorna_rv_riepilogo(self.lista_riepilogo)
        self.spinner_riga_da_cancellare.values = self._recupera_righe_selezionate()
        self.lbl_conteggio_selezioni.text = f"Articoli \nInseriti:\n     {self._conta_articoli_inseriti(self.lista_riepilogo)}"

    def _salva_dati(self, arg):
        #TODO aggiungere controlli 
        data = arg
        lista = []
        for dic in data:
            lista.append([str(self.prog_lotto_acq)+'A', 
                          self.oggi, 
                          self.txtinput_num_documento.text, 
                          self.spinner_fornitori.text, 
                          dic['text'], 
                          dic['peso'], 
                          dic['peso'], 
                          'no'])
        
        print(lista)
        sql_ins = "INSERT INTO ingresso_merce VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        self.c.executemany(sql_ins, lista)
        self.conn.commit()
        sql_update = "UPDATE progressivi SET prog_acq = %s"
        self.c.execute(sql_update, (self.prog_lotto_acq + 1,))
        self.conn.commit()
        self.conn.close()
        
    def indietro(self, instance):
        self.manager.current = 'menu'
