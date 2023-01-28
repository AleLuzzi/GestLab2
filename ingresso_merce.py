from kivy.app import App

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button, Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
import datetime
import mysql.connector

class Ingresso_merce(Screen):
    def __init__(self, **kwargs):
        super(Ingresso_merce, self).__init__(**kwargs)

        oggi = datetime.date.today()

        conn = mysql.connector.connect(host="192.168.0.100",
                                   database="data",
                                   user="root",
                                   password='')

        c = conn.cursor()

        c.execute("SELECT prog_acq FROM progressivi")
        prog_lotto_acq = c.fetchone()[0]

        lista_fornitori = []

        c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1")

        for lista in c:
            lista_fornitori.extend(lista)


        self.btn = Button(text='indietro', size_hint=(1,.1))        
        self.btn.bind(on_press=self.indietro)
        
        self.tab_panel = TabbedPanel(do_default_tab=(False), 
                                    size_hint=(1,.9), pos_hint={'top':1})
        self.tab_panel_tab1 = TabbedPanelItem(text='Intestazione')
        self.tab_panel_tab2 = TabbedPanelItem(text='Corpo \n Documento')
        self.tab_panel_tab3 = TabbedPanelItem(text='Riepilogo')

        self.box_layout_tab1 = BoxLayout(orientation='vertical')

        self.lbl_fornitore_txt = Label(text='Fornitore')
        
        self.spinner_fornitori = Spinner(values=lista_fornitori)
        
        self.lbl_data_txt = Label(text='Data Documento')
        self.lbl_data = Label(text=str(oggi.strftime('%d/%m/%y')))
        self.lbl_num_documento = Label(text='Numero Documento')
        self.txtinput_num_documento = TextInput()
        self.lbl_progressivo_lotto_ingresso_txt = Label(text='Progressivo Lotto ingresso')
        self.lbl_progressivo_ingresso = Label(text=str(prog_lotto_acq)+'V')
        
        self.add_widget(self.btn)
        self.add_widget(self.tab_panel)
        self.tab_panel.add_widget(self.tab_panel_tab1)
        self.tab_panel.add_widget(self.tab_panel_tab2)
        self.tab_panel.add_widget(self.tab_panel_tab3)
        self.tab_panel_tab1.add_widget(self.box_layout_tab1)
        self.box_layout_tab1.add_widget(self.lbl_fornitore_txt)
        self.box_layout_tab1.add_widget(self.spinner_fornitori)
        self.box_layout_tab1.add_widget(self.lbl_data_txt)
        self.box_layout_tab1.add_widget(self.lbl_data)
        self.box_layout_tab1.add_widget(self.lbl_num_documento)
        self.box_layout_tab1.add_widget(self.txtinput_num_documento)
        self.box_layout_tab1.add_widget(self.lbl_progressivo_lotto_ingresso_txt)
        self.box_layout_tab1.add_widget(self.lbl_progressivo_ingresso)


    def indietro(self, instance):
        self.manager.current = 'menu'
