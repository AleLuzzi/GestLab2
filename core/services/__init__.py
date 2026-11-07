"""Service layer condiviso (framework-agnostico).

Contiene la business logic applicativa, indipendente dalla UI e dal DB.
I servizi orchestrano i repository e i modelli di ``core`` e sono riusabili
dal backend SaaS (FastAPI) e da eventuali client futuri.
"""

from . import (
    barcode,
    dipendenti,
    fornitori,
    lotti,
    menu,
    merceologie,
    printing,
    progressivi,
    reparti,
    soggetti,
    tagli,
    vendite,
)

__all__ = [
    "dipendenti",
    "progressivi",
    "reparti",
    "fornitori",
    "soggetti",
    "tagli",
    "lotti",
    "menu",
    "vendite",
    "printing",
    "barcode",
]
