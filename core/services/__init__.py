"""Service layer condiviso (framework-agnostico).

Contiene la business logic applicativa, indipendente dalla UI e dal DB.
I servizi orchestrano i repository e i modelli di ``core`` e sono riusabili
sia dalle UI desktop (Tkinter/Kivy) sia dal backend SaaS (FastAPI).
"""

from . import (
    barcode,
    dipendenti,
    fornitori,
    ingresso_merce,
    lotti,
    menu,
    merceologie,
    printing,
    reparti,
    tagli,
    vendite,
)

__all__ = [
    "dipendenti",
    "reparti",
    "fornitori",
    "tagli",
    "lotti",
    "ingresso_merce",
    "menu",
    "vendite",
    "printing",
    "barcode",
]
