from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogHeadlineText,
    MDDialogSupportingText,
)
from kivymd.uix.screen import MDScreen

from recycleviews import SelectableBox

from core import Reparto
from core.repositories import reparti as reparti_repo


class RigaReparto(SelectableBox):
    '''Riga selezionabile per l'elenco dei reparti. '''


class Anag_reparti(MDScreen):
    def __init__(self, **kwargs):
        super(Anag_reparti, self).__init__(**kwargs)

        self.modalita_inserimento = False
        self.modalita_modifica = False
        self.reparto_selezionato = None
        self.dati_reparti = []

        self._aggiorna()
        self.ids.rv_elenco.layout_manager.bind(
            selected_nodes=self._on_selezione_elenco)

    def _aggiorna(self):
        """Ricarica i reparti dal DB e popola la RecycleView."""
        try:
            self.dati_reparti = reparti_repo.fetch_all()
        except Exception:
            self.dati_reparti = []

        self.ids.rv_elenco.data = [
            {
                'label_1': str(x.id),
                'label_2': str(x.reparto),
            }
            for x in self.dati_reparti
        ]
        self.ids.entry_filtro.text = ''
        self.ids.label_errore.text = ''
        self._disabilita_campi()

    def _filtra_reparti(self, text):
        """Filtra l'elenco in base al testo digitato."""
        testo_ricerca = text.lower()
        self.ids.rv_elenco.data = [
            {
                'label_1': str(x.id),
                'label_2': str(x.reparto),
            }
            for x in self.dati_reparti
            if testo_ricerca in str(x.reparto).lower() or testo_ricerca in str(x.id)
        ]

    def _reset_ricerca(self):
        """Svuota il filtro e ripristina l'elenco completo."""
        if self.modalita_inserimento or self.modalita_modifica:
            return
        self._aggiorna()

    def _on_selezione_elenco(self, *args):
        """Popola i dettagli del reparto selezionato."""
        if self.modalita_inserimento or self.modalita_modifica:
            return

        sel = self.ids.rv_elenco.layout_manager.selected_nodes
        if not sel:
            return

        idx = sel[0]
        id_selezionato = int(self.ids.rv_elenco.data[idx]['label_1'])

        reparto = next(
            (r for r in self.dati_reparti if int(r.id) == id_selezionato), None
        )
        if not reparto:
            return

        self.reparto_selezionato = reparto

        self.ids.campo_reparto.text = str(reparto.reparto)
        self.ids.checkbox_flag1.active = bool(reparto.flag1_dip)
        self.ids.checkbox_flag2.active = bool(reparto.flag2_prod)

        self._disabilita_campi()
        self.ids.btn_modifica.disabled = False
        self.ids.btn_elimina.disabled = False

    def _nuovo(self):
        """Prepara l'interfaccia per l'inserimento di un nuovo reparto."""
        self.modalita_inserimento = True

        self.ids.rv_elenco.layout_manager.clear_selection()
        self.reparto_selezionato = None

        self.ids.campo_reparto.text = ''
        self.ids.checkbox_flag1.active = False
        self.ids.checkbox_flag2.active = False
        self.ids.campo_reparto.readonly = False
        self.ids.checkbox_flag1.disabled = False
        self.ids.checkbox_flag2.disabled = False

        self.ids.btn_nuovo.disabled = True
        self.ids.btn_modifica.disabled = True
        self.ids.btn_elimina.disabled = True
        self.ids.btn_salva.disabled = False
        self.ids.btn_annulla.disabled = False

    def _modifica(self):
        """Abilita i campi per la modifica del reparto selezionato."""
        if not self.reparto_selezionato:
            return

        self.modalita_modifica = True

        self.ids.campo_reparto.readonly = False
        self.ids.checkbox_flag1.disabled = False
        self.ids.checkbox_flag2.disabled = False

        self.ids.btn_nuovo.disabled = True
        self.ids.btn_modifica.disabled = True
        self.ids.btn_elimina.disabled = True
        self.ids.btn_salva.disabled = False
        self.ids.btn_annulla.disabled = False

    def _salva(self):
        """Valida e salva il record (inserimento o modifica)."""
        reparto_nome = self.ids.campo_reparto.text.strip()
        if not reparto_nome:
            self.ids.label_errore.text = 'Il campo Reparto è obbligatorio.'
            return

        self.ids.label_errore.text = ''

        flag1 = 1 if self.ids.checkbox_flag1.active else 0
        flag2 = 1 if self.ids.checkbox_flag2.active else 0

        try:
            if self.modalita_inserimento:
                reparti_repo.insert(Reparto(
                    reparto=reparto_nome,
                    flag1_dip=flag1,
                    flag2_prod=flag2,
                ))
            else:
                if not self.reparto_selezionato:
                    return
                self.reparto_selezionato.reparto = reparto_nome
                self.reparto_selezionato.flag1_dip = flag1
                self.reparto_selezionato.flag2_prod = flag2
                reparti_repo.save(self.reparto_selezionato)

            self.modalita_inserimento = False
            self.modalita_modifica = False
            self.reparto_selezionato = None
            self._aggiorna()
            self._disabilita_campi()
        except Exception as e:
            self.ids.label_errore.text = 'Errore durante l\'operazione: {}'.format(e)

    def _annulla(self):
        """Annulla le modifiche correnti e ripristina la UI."""
        self.modalita_inserimento = False
        self.modalita_modifica = False
        self.reparto_selezionato = None

        self._aggiorna()
        self._disabilita_campi()

    def _elimina(self):
        """Apre un dialog di conferma prima di eliminare il reparto."""
        if not self.reparto_selezionato:
            self.ids.label_errore.text = 'Nessun record selezionato per l\'eliminazione.'
            return

        reparto = self.reparto_selezionato
        self.dialog_conferma_elimina = MDDialog(
            MDDialogHeadlineText(
                text='Eliminare il reparto?',
                halign='left',
            ),
            MDDialogSupportingText(
                text='Il reparto "{}" (ID {}) sarà eliminato definitivamente dal database.'
                     .format(reparto.reparto, reparto.id),
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
        """Elimina definitivamente il reparto selezionato."""
        self._annulla_elimina()
        if not self.reparto_selezionato:
            self.ids.label_errore.text = 'Nessun record selezionato per l\'eliminazione.'
            return

        try:
            reparti_repo.delete(self.reparto_selezionato)
        except Exception as e:
            self.ids.label_errore.text = 'Impossibile eliminare il reparto: {}'.format(e)
            return

        self.ids.label_errore.text = ''
        self.reparto_selezionato = None
        self._aggiorna()
        self._disabilita_campi()

    def _disabilita_campi(self):
        """Riporta l'interfaccia allo stato iniziale di blocco (sola lettura)."""
        self.modalita_inserimento = False
        self.modalita_modifica = False

        self.ids.campo_reparto.readonly = True
        self.ids.checkbox_flag1.disabled = True
        self.ids.checkbox_flag2.disabled = True

        self.ids.btn_nuovo.disabled = False
        self.ids.btn_modifica.disabled = True
        self.ids.btn_salva.disabled = True
        self.ids.btn_annulla.disabled = True
        self.ids.btn_elimina.disabled = True

    def indietro(self):
        self.manager.current = 'menu'
