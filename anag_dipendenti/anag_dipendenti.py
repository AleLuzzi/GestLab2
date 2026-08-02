from kivy.clock import Clock
from kivy.properties import BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen

from .dipendente import Dipendente
import controller_db as db


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class RigaDipendente(RecycleDataViewBehavior, MDBoxLayout):
    ''' Add selection support to the row '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(RigaDipendente, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(RigaDipendente, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        prev_selected = rv.data[index].get('selected', False)
        self.selected = is_selected
        rv.data[index]['selected'] = is_selected
        if prev_selected != is_selected:
            if is_selected:
                print("selection changed to {0}".format(rv.data[index]))
            else:
                print("selection removed for {0}".format(rv.data[index]))


class Anag_dipendenti(MDScreen):
    def __init__(self, **kwargs):
        super(Anag_dipendenti, self).__init__(**kwargs)

        self.modalita_inserimento = False
        self.modalita_modifica = False
        self.dipendente_selezionato = None
        self.dati_dipendenti = []
        self.reparti_map_id_nome = {}
        self.reparti_map_nome_id = {}

        self._carica_reparti()
        self._aggiorna()
        self.ids.rv_elenco.layout_manager.bind(
            selected_nodes=self._on_selezione_elenco)

    # ------------------------------------------------------------------ #
    #  Helper reparti
    # ------------------------------------------------------------------ #
    def _carica_reparti(self):
        """Carica la lista reparti (mostra il nome, salva l'ID)."""
        self.reparti_map_id_nome = {}
        self.reparti_map_nome_id = {}
        try:
            reparti = db._recupera_reparti()
        except Exception:
            reparti = []

        for r in reparti:
            rid = r['id']
            rnome = r['reparto']
            self.reparti_map_id_nome[rid] = rnome
            self.reparti_map_nome_id[rnome] = rid

        self.menu_reparti = MDDropdownMenu(
            caller=self.ids.campo_reparto,
            items=[
                {
                    'text': r['reparto'],
                    'on_release': lambda x=r['reparto']: self._seleziona_reparto(x),
                }
                for r in reparti
            ],
        )
        self.ids.campo_reparto.bind(focus=self._on_reparto_focus)

    def _on_reparto_focus(self, instance, value):
        if value and not self.ids.campo_reparto.readonly:
            self.menu_reparti.open()

    def _seleziona_reparto(self, reparto):
        self.ids.campo_reparto.text = reparto
        self.menu_reparti.dismiss()

    # ------------------------------------------------------------------ #
    #  Caricamento elenco
    # ------------------------------------------------------------------ #
    def _aggiorna(self):
        """Ricarica i dipendenti dal DB e popola la RecycleView."""
        try:
            self.dati_dipendenti = Dipendente.fetch_all(db.c)
        except Exception:
            self.dati_dipendenti = []

        self.ids.rv_elenco.data = [
            {
                'label_1': str(x.id),
                'label_2': str(x.nome),
            }
            for x in self.dati_dipendenti
        ]
        self.ids.entry_filtro.text = ''

    def _filtra_dipendenti(self, text):
        """Filtra l'elenco in base al testo digitato."""
        testo_ricerca = text.lower()
        self.ids.rv_elenco.data = [
            {
                'label_1': str(x.id),
                'label_2': str(x.nome),
            }
            for x in self.dati_dipendenti
            if testo_ricerca in str(x.nome).lower() or testo_ricerca in str(x.id)
        ]

    def _reset_ricerca(self):
        """Svuota il filtro e ripristina l'elenco completo."""
        if self.modalita_inserimento or self.modalita_modifica:
            return
        self._aggiorna()

    def _on_selezione_elenco(self, *args):
        """Popola i dettagli del dipendente selezionato."""
        if self.modalita_inserimento or self.modalita_modifica:
            return

        sel = self.ids.rv_elenco.layout_manager.selected_nodes
        if not sel:
            return

        idx = sel[0]
        id_selezionato = int(self.ids.rv_elenco.data[idx]['label_1'])

        dipendente = next(
            (d for d in self.dati_dipendenti if int(d.id) == id_selezionato), None
        )
        if not dipendente:
            return

        self.dipendente_selezionato = dipendente

        self.ids.campo_nome.text = str(dipendente.nome)
        self.ids.campo_email.text = str(dipendente.email)

        reparto_id = dipendente.reparto
        nome_reparto = self.reparti_map_id_nome.get(
            str(reparto_id), '') if reparto_id is not None else ''
        self.ids.campo_reparto.text = nome_reparto

        self._disabilita_campi()

    # ------------------------------------------------------------------ #
    #  Azioni
    # ------------------------------------------------------------------ #
    def _nuovo(self):
        """Prepara l'interfaccia per l'inserimento di un nuovo dipendente."""
        self.modalita_inserimento = True

        self.ids.rv_elenco.layout_manager.clear_selection()
        self.dipendente_selezionato = None

        self.ids.campo_nome.text = ''
        self.ids.campo_email.text = ''
        self.ids.campo_reparto.text = ''
        self.ids.campo_reparto.readonly = False

        self.ids.btn_nuovo.disabled = True
        self.ids.btn_modifica.disabled = True
        self.ids.btn_elimina.disabled = True
        self.ids.btn_salva.disabled = False
        self.ids.btn_annulla.disabled = False

    def _modifica(self):
        """Abilita i campi per la modifica del dipendente selezionato."""
        if not self.dipendente_selezionato:
            return

        self.modalita_modifica = True

        self.ids.campo_reparto.readonly = False

        self.ids.btn_nuovo.disabled = True
        self.ids.btn_modifica.disabled = True
        self.ids.btn_elimina.disabled = True
        self.ids.btn_salva.disabled = False
        self.ids.btn_annulla.disabled = False

    def _salva(self):
        """Valida e salva il record (inserimento o modifica)."""
        nome_dipendente = self.ids.campo_nome.text.strip()
        if not nome_dipendente:
            self.ids.label_errore.text = 'Il campo Nome è obbligatorio.'
            return

        self.ids.label_errore.text = ''

        email_dipendente = self.ids.campo_email.text.strip()
        reparto_selected = (self.ids.campo_reparto.text or '').strip()
        reparto_id = self.reparti_map_nome_id.get(reparto_selected)

        try:
            if self.modalita_inserimento:
                Dipendente(nome=nome_dipendente, email=email_dipendente,
                           reparto=reparto_id).insert(db.c, db.conn)
            else:
                if not self.dipendente_selezionato:
                    return
                self.dipendente_selezionato.nome = nome_dipendente
                self.dipendente_selezionato.email = email_dipendente
                self.dipendente_selezionato.reparto = reparto_id
                self.dipendente_selezionato.save(db.c, db.conn)

            self.modalita_inserimento = False
            self.modalita_modifica = False
            self.dipendente_selezionato = None
            self._aggiorna()
            self._disabilita_campi()
        except Exception as e:
            self.ids.label_errore.text = 'Errore durante l\'operazione: {}'.format(e)

    def _annulla(self):
        """Annulla le modifiche correnti e ripristina la UI."""
        self.modalita_inserimento = False
        self.modalita_modifica = False
        self.dipendente_selezionato = None

        self._aggiorna()
        self._disabilita_campi()

    def _elimina(self):
        """Elimina il dipendente selezionato previa conferma."""
        if not self.dipendente_selezionato:
            self.ids.label_errore.text = 'Nessun record selezionato per l\'eliminazione.'
            return

        try:
            self.dipendente_selezionato.delete(db.c, db.conn)
        except Exception as e:
            self.ids.label_errore.text = 'Impossibile eliminare il dipendente: {}'.format(e)
            return

        self.ids.label_errore.text = ''
        self.dipendente_selezionato = None
        self._aggiorna()
        self._disabilita_campi()

    def _disabilita_campi(self):
        """Riporta l'interfaccia allo stato iniziale di blocco (sola lettura)."""
        self.modalita_inserimento = False
        self.modalita_modifica = False

        self.ids.campo_reparto.readonly = True

        self.ids.btn_nuovo.disabled = False
        self.ids.btn_modifica.disabled = False
        self.ids.btn_salva.disabled = True
        self.ids.btn_annulla.disabled = True
        self.ids.btn_elimina.disabled = True

    def indietro(self):
        self.manager.current = 'menu'

