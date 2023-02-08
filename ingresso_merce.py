from kivy.app import App

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button, Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
import datetime
import mysql.connector
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.metrics import dp
from kivy.uix.togglebutton import ToggleButton

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


class Ingresso_merce(Screen):
    def __init__(self, **kwargs):
        super(Ingresso_merce, self).__init__(**kwargs)

        oggi = datetime.date.today()

        self.conn = mysql.connector.connect(host="192.168.0.100",
                                   database="data",
                                   user="root",
                                   password='')

        c = self.conn.cursor()

        c.execute("SELECT prog_acq FROM progressivi")
        prog_lotto_acq = c.fetchone()[0]

        lista_fornitori = []

        c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1")

        for lista in c:
            lista_fornitori.extend(lista)

        ''' DEFINIZIONE BTN INDIETRO COMUNE A TUTTI I TAB '''

        self.btn = Button(text='indietro', size_hint=(1,.1))        
        self.btn.bind(on_press=self.indietro)
        self.add_widget(self.btn)
        
        ''' DEFINIZIONE TAB PANEL '''
        
        self.tab_panel = TabbedPanel(do_default_tab=(False), 
                                    size_hint=(1,.9), pos_hint={'top':1})
        self.tab_panel_tab1 = TabbedPanelItem(text='Intestazione')
        self.tab_panel_tab2 = TabbedPanelItem(text='Corpo \n Documento')
        self.tab_panel_tab3 = TabbedPanelItem(text='Riepilogo')

        self.add_widget(self.tab_panel)
        self.tab_panel.add_widget(self.tab_panel_tab1)
        self.tab_panel.add_widget(self.tab_panel_tab2)
        self.tab_panel.add_widget(self.tab_panel_tab3)

        ''' DEFINIZIONE BOX E WIDGET CONTENUTI NEL TAB1 -INTESTAZIONE- '''
        
        self.box_layout_tab1 = BoxLayout(orientation='vertical')

        self.lbl_progressivo_lotto_ingresso_txt = Label(text='Progressivo Lotto ingresso')
        self.lbl_progressivo_ingresso = Label(text=str(prog_lotto_acq)+'V')
        self.lbl_fornitore_txt = Label(text='Fornitore')
        self.spinner_fornitori = Spinner(values=lista_fornitori)
        self.lbl_data_txt = Label(text='Data Documento')
        self.lbl_data = Label(text=str(oggi.strftime('%d/%m/%y')))
        self.lbl_num_documento = Label(text='Numero Documento')
        self.txtinput_num_documento = TextInput()

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

        recycle_box_layout = SelectableRecycleBoxLayout(default_size=(None, dp(56)), default_size_hint=(1, None),
                                                        size_hint=(1, None), orientation='vertical')
        recycle_box_layout.bind(minimum_height=recycle_box_layout.setter("height"))
        self.mostra_dati = RV()
        self.mostra_dati.add_widget(recycle_box_layout)
        self.mostra_dati.viewclass= 'SelectableLabel'
        
        self.box_layout_recicleview.add_widget(self.mostra_dati)

        ''' BOXLAYOUT SINISTRO CON TOGGLE BTN E RECYCLEVIEW'''

        self.box_sinistra.add_widget(self.box_layout_toggle_btn)
        self.box_sinistra.add_widget(self.box_layout_recicleview)

        ''' BOXLAYOUT DESTRO '''

        self.btn_quantita_richiesta = Label(text='Quantità richiesta', size_hint=(1, .1), pos_hint={"top":1})
        self.box_destra.add_widget(self.btn_quantita_richiesta)

        ''' DEFINIZIONE BOXLAYOUT E TOGGLE_BTN PER SELEZIONE KG/PZ'''

        self.box_kg_pz = BoxLayout(orientation='horizontal', size_hint=(1, .1), pos_hint={'top':1})
        self.tgl_btn_kg = ToggleButton(text='Kg', group='peso', state='down')
        self.tgl_btn_pz = ToggleButton(text='Pz', group='peso')
        
        self.box_destra.add_widget(self.box_kg_pz)
        self.box_kg_pz.add_widget(self.tgl_btn_kg)
        self.box_kg_pz.add_widget(self.tgl_btn_pz)

        ''' DEFINIZIONE BOXLAYOUT E SLIDER PER INSERIMENTO PESO ORDINATO'''

        self.box_slider = BoxLayout(orientation='vertical', size_hint=(1, .1), pos_hint={'top':1})
        self.slider_peso = Slider(min=1, max=30, step=0.5)
        self.slider_peso.bind(value=self.OnSliderValueChange)
        self.lbl_slider = Label(text='0')
        
        self.box_destra.add_widget(self.box_slider)
        self.box_slider.add_widget(self.slider_peso)
        self.box_slider.add_widget(self.lbl_slider)

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

    def OnSliderValueChange(self, instance, value):
        self.lbl_slider.text = str(value)
    
    def pressione_btn_peso_veloce(self, value):
        self.lbl_slider.text = str(value)
        self.slider_peso.value = str(value)


    def aggiorna_rv(self, cat):
        self.c = self.conn.cursor()
        cat_merc = [cat,]
        lista = []
        query = 'SELECT taglio FROM tagli WHERE Id_Merceologia=%s'
        self.c.execute(query, cat_merc)
        for x in self.c:
            lista.extend(x)
        self.mostra_dati.data = [{'text': x, 'cat_merc': cat_merc[0]} for x in lista]

    def indietro(self, instance):
        self.manager.current = 'menu'
