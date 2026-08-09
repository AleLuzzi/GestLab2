import datetime

from kivymd.uix.screen import MDScreen

from recycleviews import SelectableBox

from core.repositories import lotti as lotti_repo


class Multicampo(SelectableBox):
    ''' Riga selezionabile per l'elenco dei lotti aperti. '''


class Chiudi_lotto(MDScreen):
    def __init__(self, **kwargs):
        super(Chiudi_lotto, self).__init__(**kwargs)

        oggi = datetime.date.today()

        dati = lotti_repo.lotti_aperti()

        self.ids.rv.data = [{'label_1': str(x['number']),
                             'label_2': str(x['fornit']),
                             'label_3': str(x['name']),
                             'label_4': str(x['peso'])} for x in dati]

    def indietro(self):
        self.manager.current = 'menu'

