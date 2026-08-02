"""Classi condivise per le RecycleView selezionabili di GestLab2.

Questo modulo evita la duplicazione delle stesse classi nei vari moduli
(anag_dipendenti, chiudi_lotto, ingresso_merce, lotti_vendita, nuovo_menu).
"""

from kivy.properties import BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    """Aggiunge selezione e focus alla RecycleBoxLayout."""


class SelectableLabel(RecycleDataViewBehavior, MDLabel):
    """Etichetta selezionabile all'interno di una RecycleView."""

    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        """Aggiorna gli attributi della view quando i dati cambiano."""
        self.index = index
        return super(SelectableLabel, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """Gestisce la selezione al tocco."""
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        """Applica lo stato di selezione all'elemento."""
        self.selected = is_selected
        rv.data[index]['selected'] = self.selected


class SelectableBox(RecycleDataViewBehavior, MDBoxLayout):
    """BoxLayout selezionabile all'interno di una RecycleView."""

    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        """Aggiorna gli attributi della view quando i dati cambiano."""
        self.index = index
        return super(SelectableBox, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """Gestisce la selezione al tocco."""
        if super(SelectableBox, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        """Applica lo stato di selezione all'elemento."""
        self.selected = is_selected
        rv.data[index]['selected'] = is_selected

