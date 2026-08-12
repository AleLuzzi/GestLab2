"""Compatibilita': re-export del modello Dipendente dal core.

Per evitare doppia manutenzione, il modello unico vive in ``core.core_models``.
Questo modulo mantiene il vecchio import ``from .dipendente import Dipendente``
funzionante.
"""

from core import Dipendente

__all__ = ["Dipendente"]
