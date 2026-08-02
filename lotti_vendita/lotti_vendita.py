import datetime

from kivymd.uix.screen import MDScreen

from recycleviews import SelectableLabel

import controller_db as db


class Lotti_vendita(MDScreen):
    def __init__(self, **kwargs):
        super(Lotti_vendita, self).__init__(**kwargs)

        oggi = datetime.date.today()

        self.rv.data = [{'text': str(x)} for x in range(10)]
        self.rv2.data = [{'text': str(x)} for x in range(10)]

    def indietro(self):
        self.manager.current = 'menu'

