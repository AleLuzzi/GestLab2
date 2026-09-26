from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogHeadlineText,
    MDDialogSupportingText,
)
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen

from recycleviews import SelectableBox

from core import Taglio
from core.repositories import merceologie as merceologie_repo
from core.repositories import tagli as tagli_repo


class RigaTaglio(SelectableBox):
    """Riga selezionabile per l'elenco dei tagli."""


class Anag_tagli(MDScreen):
    def __init__(self, **kwargs):
        super(Anag_tagli, self).__init__(**kwargs)

        self.modalita_inserimento = False
        self.modalita_modifica = False
        self.taglio_selezionato = None
        self.dati_tagli = []
        self.merceologie_map_id_nome = {}
        self.merceologie_map_nome_id = {}

        self._carica_merceologie()
        self._aggiorna()
        self.ids.rv_elenco.layout_manager.bind(
            selected_nodes=self._on_selezione_elenco)

    def _carica_merceologie(self):
        """Carica la lista delle merceologie e costruisce il dropdown."""
        self.merceologie_map_id_nome = {}
        self.merceologie_map_nome_id = {}
        try:
            merceologie = merceologie_repo.fetch_all()
        except Exception:
            merceologie = []

        for m in merceologie:
            self.merceologie_map_id_nome[str(m.id)] = str(m.merceologia)
            self.merceologie_map_nome_id[str(m.merceologia)] = m.id

        self.menu_merceologie = MDDropdownMenu(
            caller=self.ids.campo_merceologia,
            items=[
                {
                    'text': m.merceologia,
                    'on_release': lambda x=m.merceologia: self._seleziona_merceologia(x),
                }
                for m in merceologie
            ],
        )
        self.ids.campo_merceologia.bind(focus=self._on_merceologia_focus)

    def _on_merceologia_focus(self, instance, value):
        if value and not self.ids.campo_merceologia.readonly:
            self.menu_merceologie.open()

    def _seleziona_merceologia(self, nome_merceologia):
        self.ids.campo_merceologia.text = nome_merceologia
        self.menu_merceologie.dismiss()

    def _aggiorna(self):
        """Ricarica i tagli dal DB e popola la RecycleView."""
        try:
            self.dati_tagli = tagli_repo.fetch_all()
        except Exception:
            self.dati_tagli = []

        self.ids.rv_elenco.data = [
            {
                'label_1': str(x.id),
                'label_2': self._testo_taglio(x),
            }
            for x in self.dati_tagli
        ]
        self.ids.entry_filtro.text = ''
        self.ids.label_errore.text = ''
        self._disabilita_campi()

    def _testo_taglio(self, taglio):
        nome_merceologia = self.merceologie_map_id_nome.get(str(taglio.id_merceologia), '')
        if nome_merceologia:
            return f"{taglio.taglio} - {nome_merceologia}"
        return taglio.taglio

    def _filtra_tagli(self, text):
        """Filtra i tagli in base al testo digitato."""
        testo_ricerca = text.lower()
        self.ids.rv_elenco.data = [
            {
                'label_1': str(x.id),
                'label_2': self._testo_taglio(x),
            }
            for x in self.dati_tagli
            if (
                testo_ricerca in str(x.taglio).lower()
                or testo_ricerca in str(x.id)
                or testo_ricerca in str(self.merceologie_map_id_nome.get(str(x.id_merceologia), '')).lower()
            )
        ]

    def _reset_ricerca(self):
        """Svuota il filtro e ripristina l'elenco completo."""
        if self.modalita_inserimento or self.modalita_modifica:
            return
        self._aggiorna()

    def _on_selezione_elenco(self, *args):
        """Popola i dettagli del taglio selezionato."""
        if self.modalita_inserimento or self.modalita_modifica:
            return

        sel = self.ids.rv_elenco.layout_manager.selected_nodes
        if not sel:
            return

        idx = sel[0]
        id_selezionato = int(self.ids.rv_elenco.data[idx]['label_1'])

        taglio = next(
            (t for t in self.dati_tagli if int(t.id) == id_selezionato), None
        )
        if not taglio:
            return

        self.taglio_selezionato = taglio
        self.ids.campo_taglio.text = str(taglio.taglio)
        nome_merceologia = self.merceologie_map_id_nome.get(str(taglio.id_merceologia), '')
        self.ids.campo_merceologia.text = nome_merceologia

        self._disabilita_campi()
        self.ids.btn_modifica.disabled = False
        self.ids.btn_elimina.disabled = False

    def _nuovo(self):
        """Prepara l'interfaccia per l'inserimento di un nuovo taglio."""
        self.modalita_inserimento = True

        self.ids.rv_elenco.layout_manager.clear_selection()
        self.taglio_selezionato = None

        self.ids.campo_taglio.text = ''
        self.ids.campo_merceologia.text = ''
        self.ids.campo_taglio.readonly = False
        self.ids.campo_merceologia.readonly = False

        self.ids.btn_nuovo.disabled = True
        self.ids.btn_modifica.disabled = True
        self.ids.btn_elimina.disabled = True
        self.ids.btn_salva.disabled = False
        self.ids.btn_annulla.disabled = False

    def _modifica(self):
        """Abilita i campi per la modifica del taglio selezionato."""
        if not self.taglio_selezionato:
            return

        self.modalita_modifica = True

        self.ids.campo_taglio.readonly = False
        self.ids.campo_merceologia.readonly = False

        self.ids.btn_nuovo.disabled = True
        self.ids.btn_modifica.disabled = True
        self.ids.btn_elimina.disabled = True
        self.ids.btn_salva.disabled = False
        self.ids.btn_annulla.disabled = False

    def _salva(self):
        """Valida e salva il record (inserimento o modifica)."""
        nome_taglio = self.ids.campo_taglio.text.strip()
        if not nome_taglio:
            self.ids.label_errore.text = 'Il campo Taglio è obbligatorio.'
            return

        self.ids.label_errore.text = ''

        merceologia_selected = (self.ids.campo_merceologia.text or '').strip()
        merceologia_id = self.merceologie_map_nome_id.get(merceologia_selected)

        try:
            if self.modalita_inserimento:
                tagli_repo.insert(Taglio(
                    taglio=nome_taglio,
                    id_merceologia=merceologia_id,
                ))
            else:
                if not self.taglio_selezionato:
                    return
                self.taglio_selezionato.taglio = nome_taglio
                self.taglio_selezionato.id_merceologia = merceologia_id
                tagli_repo.save(self.taglio_selezionato)

            self.modalita_inserimento = False
            self.modalita_modifica = False
            self.taglio_selezionato = None
            self._aggiorna()
            self._disabilita_campi()
        except Exception as e:
            self.ids.label_errore.text = 'Errore durante l\'operazione: {}'.format(e)

    def _annulla(self):
        """Annulla le modifiche correnti e ripristina la UI."""
        self.modalita_inserimento = False
        self.modalita_modifica = False
        self.taglio_selezionato = None

        self._aggiorna()
        self._disabilita_campi()

    def _elimina(self):
        """Apre un dialog di conferma prima di eliminare il taglio."""
        if not self.taglio_selezionato:
            self.ids.label_errore.text = 'Nessun record selezionato per l\'eliminazione.'
            return

        taglio = self.taglio_selezionato
        self.dialog_conferma_elimina = MDDialog(
            MDDialogHeadlineText(
                text='Eliminare il taglio?',
                halign='left',
            ),
            MDDialogSupportingText(
                text='Il taglio "{}" (ID {}) sarà eliminato definitivamente dal database.'
                     .format(taglio.taglio, taglio.id),
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
        """Elimina definitivamente il taglio selezionato."""
        self._annulla_elimina()
        if not self.taglio_selezionato:
            self.ids.label_errore.text = 'Nessun record selezionato per l\'eliminazione.'
            return

        try:
            tagli_repo.delete(self.taglio_selezionato)
        except Exception as e:
            self.ids.label_errore.text = 'Impossibile eliminare il taglio: {}'.format(e)
            return

        self.ids.label_errore.text = ''
        self.taglio_selezionato = None
        self._aggiorna()
        self._disabilita_campi()

    def _disabilita_campi(self):
        """Riporta l'interfaccia allo stato iniziale di blocco (sola lettura)."""
        self.modalita_inserimento = False
        self.modalita_modifica = False

        self.ids.campo_taglio.readonly = True
        self.ids.campo_merceologia.readonly = True

        self.ids.btn_nuovo.disabled = False
        self.ids.btn_modifica.disabled = True
        self.ids.btn_salva.disabled = True
        self.ids.btn_annulla.disabled = True
        self.ids.btn_elimina.disabled = True

    def indietro(self):
        self.manager.current = 'menu'
