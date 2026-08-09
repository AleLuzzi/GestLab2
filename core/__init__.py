"""Core applicativo unificato (GestLab2 + Laboratorio).

Contiene la business logic e il data layer framework-agnostici, indipendenti
dalla UI (Tkinter/Kivy) e pronti per essere riusati dal backend SaaS.
"""

from . import db, config, env
from .core_models import (
    Dipendente,
    Fornitore,
    Taglio,
    Merceologia,
    Ingrediente,
    Reparto,
    MovIngressoMerce,
)

__all__ = [
    "db",
    "config",
    "env",
    "Dipendente",
    "Fornitore",
    "Taglio",
    "Merceologia",
    "Ingrediente",
    "Reparto",
    "MovIngressoMerce",
]
