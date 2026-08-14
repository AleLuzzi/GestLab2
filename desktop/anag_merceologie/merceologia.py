"""Compatibilita': re-export del modello Merceologia dal core.

Per evitare doppia manutenzione, il modello unico vive in ``core.core_models``.
Questo modulo mantiene il vecchio import ``from .merceologia import Merceologia``
funzionante.
"""

from core import Merceologia

__all__ = ["Merceologia"]
