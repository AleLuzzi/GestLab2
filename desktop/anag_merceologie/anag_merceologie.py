from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogHeadlineText,
    MDDialogSupportingText,
)
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen

from recycleviews import SelectableBox

from core import Merceologia
from core.repositories import reparti as reparti_repo
from core.repositories import merceologie as merceologie_repo


class RigaMerceologia(SelectableBox):
    ''' Riga selezionabile per l'elenco delle merceologie. '''


class Anag_merceologie(MDScreen):
    def __init__(self, **kwargs):
        super(Anag_merceologie, self).__init__(**kwargs)

        self.modalita_inserimento = False
        self.modalita_modifica = False
        self.merceologia_selezionata = None
        self.dati_merceologie = []
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
            reparti = reparti_repo.reparti_abilitati()
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
        """Ricarica le merceologie dal DB e popola la RecycleView."""
        try:
            self.dati_merceologie = merceologie_repo.fetch_all()
        except Exception:
            self.dati_merceologie = []

        self.ids.rv_elenco.data = [
            {
                'label_1': str(x.id),
                'label_2': str(x.merceologia),
            }
            for x in self.dati_merceologie
        ]
        self.ids.entry_filtro.text = ''

    def _filtra_merceologie(self, text):
        """Filtra l'elenco in base al testo digitato."""
        testo_ricerca = text.lower()
        self.ids.rv_elenco.data = [
            {
                'label_1': str(x.id),
                'label_2': str(x.merceologia),
            }
            for x in self.dati_merceologie
            if testo_ricerca in str(x.merceologia).lower() or testo_ricerca in str(x.id)
        ]

    def _reset_ricerca(self):
        """Svuota il filtro e ripristina l'elenco completo."""
        if self.modalita_inserimento or self.modalita_modifica:
            return
        self._aggiorna()

    def _on_selezione_elenco(self, *args):
        """Popola i dettagli della merceologia selezionata."""
        if self.modalita_inserimento or self.modalita_modifica:
            return

        sel = self.ids.rv_elenco.layout_manager.selected_nodes
        if not sel:
            return

        idx = sel[0]
        id_selezionato = int(self.ids.rv_elenco.data[idx]['label_1'])

        merceologia = next(
            (m for m in self.dati_merceologie if int(m.id) == id_selezionato), None
        )
        if not merceologia:
            return

        self.merceologia_selezionata = merceologia

        self.ids.campo_nome.text = str(merceologia.merceologia)

        reparto_id = merceologia.id_reparto
        nome_reparto = self.reparti_map_id_nome.get(
            str(reparto_id), '') if reparto_id is not None else ''
        self.ids.campo_reparto.text = nome_reparto

        self.ids.check_inv.active = bool(merceologia.flag1_inv)
        self.ids.check_taglio.active = bool(merceologia.flag2_taglio)
        self.ids.check_ing_base.active = bool(merceologia.flag3_ing_base)

        self._disabilita_campi()
        # Con una merceologia selezionata è possibile modificarla o eliminarla
        self.ids.btn_elimina.disabled = False

    # ------------------------------------------------------------------ #
    #  Azioni
    # ------------------------------------------------------------------ #
    def _nuovo(self):
        """Prepara l'interfaccia per l'inserimento di una nuova merceologia."""
        self.modalita_inserimento = True

        self.ids.rv_elenco.layout_manager.clear_selection()
        self.merceologia_selezionata = None

        self.ids.campo_nome.text = ''
        self.ids.campo_reparto.text = ''
        self.ids.campo_reparto.readonly = False

        self.ids.check_inv.active = False
        self.ids.check_taglio.active = False
        self.ids.check_ing_base.active = False

        self.ids.btn_nuovo.disabled = True
        self.ids.btn_modifica.disabled = True
        self.ids.btn_elimina.disabled = True
        self.ids.btn_salva.disabled = False
        self.ids.btn_annulla.disabled = False

    def _modifica(self):
        """Abilita i campi per la modifica della merceologia selezionata."""
        if not self.merceologia_selezionata:
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
        nome_merceologia = self.ids.campo_nome.text.strip()
        if not nome_merceologia:
            self.ids.label_errore.text = 'Il campo Nome è obbligatorio.'
            return

        self.ids.label_errore.text = ''

        reparto_selected = (self.ids.campo_reparto.text or '').strip()
        reparto_id = self.reparti_map_nome_id.get(reparto_selected)

        flag1_inv = 1 if self.ids.check_inv.active else 0
        flag2_taglio = 1 if self.ids.check_taglio.active else 0
        flag3_ing_base = 1 if self.ids.check_ing_base.active else 0

        try:
            if self.modalita_inserimento:
                merceologie_repo.insert(Merceologia(
                    merceologia=nome_merceologia,
                    id_reparto=reparto_id,
                    flag1_inv=flag1_inv,
                    flag2_taglio=flag2_taglio,
                    flag3_ing_base=flag3_ing_base,
                ))
            else:
                if not self.merceologia_selezionata:
                    return
                self.merceologia_selezionata.merceologia = nome_merceologia
                self.merceologia_selezionata.id_reparto = reparto_id
                self.merceologia_selezionata.flag1_inv = flag1_inv
                self.merceologia_selezionata.flag2_taglio = flag2_taglio
                self.merceologia_selezionata.flag3_ing_base = flag3_ing_base
                merceologie_repo.save(self.merceologia_selezionata)

            self.modalita_inserimento = False
            self.modalita_modifica = False
            self.merceologia_selezionata = None
            self._aggiorna()
            self._disabilita_campi()
        except Exception as e:
            self.ids.label_errore.text = 'Errore durante l\'operazione: {}'.format(e)

    def _annulla(self):
        """Annulla le modifiche correnti e ripristina la UI."""
        self.modalita_inserimento = False
        self.modalita_modifica = False
        self.merceologia_selezionata = None

        self._aggiorna()
        self._disabilita_campi()

    def _elimina(self):
        """Apre un dialog di conferma prima di eliminare la merceologia."""
        if not self.merceologia_selezionata:
            self.ids.label_errore.text = 'Nessun record selezionato per l\'eliminazione.'
            return

        merceologia = self.merceologia_selezionata
        self.dialog_conferma_elimina = MDDialog(
            MDDialogHeadlineText(
                text='Eliminare la merceologia?',
                halign='left',
            ),
            MDDialogSupportingText(
                text='La merceologia "{}" (ID {}) sarà eliminata definitivamente '
                     'dal database. L\'operazione non può essere annullata.'.format(
                         merceologia.merceologia, merceologia.id),
                halign='left',
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text='Annulla'),
                    style='text',
                    on_release=self._annulla_elimina,
                ),
                MDButton(
                    MDButtonText(text='Elimina'),
                    style='filled',
                    theme_bg_color='Custom',
                    md_bg_color='#B71C1C',
                    on_release=self._conferma_elimina,
                ),
                spacing='8dp',
            ),
        )
        self.dialog_conferma_elimina.open()

    def _annulla_elimina(self, *args):
        """Chiude il dialog di conferma senza eliminare nulla."""
        if hasattr(self, 'dialog_conferma_elimina'):
            self.dialog_conferma_elimina.dismiss()

    def _conferma_elimina(self, *args):
        """Elimina definitivamente la merceologia selezionata."""
        self._annulla_elimina()
        if not self.merceologia_selezionata:
            self.ids.label_errore.text = 'Nessun record selezionato per l\'eliminazione.'
            return

        try:
            merceologie_repo.delete(self.merceologia_selezionata)
        except Exception as e:
            self.ids.label_errore.text = 'Impossibile eliminare la merceologia: {}'.format(e)
            return

        self.ids.label_errore.text = ''
        self.merceologia_selezionata = None
        self._aggiorna()
        self._disabilita_campi()

    def _disabilita_campi(self):
        """Riporta l'interfaccia allo stato iniziale di blocco (sola lettura)."""
        self.modalita_inserimento = False
        self.modalita_modifica = False

        self.ids.campo_reparto.readonly = True
        self.ids.check_inv.disabled = True
        self.ids.check_taglio.disabled = True
        self.ids.check_ing_base.disabled = True

        self.ids.btn_nuovo.disabled = False
        self.ids.btn_modifica.disabled = False
        self.ids.btn_salva.disabled = True
        self.ids.btn_annulla.disabled = True
        self.ids.btn_elimina.disabled = True

    def _abilita_campi(self):
        """Abilita i campi per la modifica."""
        self.ids.check_inv.disabled = False
        self.ids.check_taglio.disabled = False
        self.ids.check_ing_base.disabled = False

    def indietro(self):
        self.manager.current = 'menu'
