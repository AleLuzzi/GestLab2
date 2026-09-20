"""Repository di accesso dati per il core applicativo.

Ogni modulo espone funzioni/classi per l'accesso a una specifica entita',
usando esclusivamente il context manager ``core.db.connection`` e mai una
connessione globale condivisa.
"""

__all__ = ["prodotti", "lotti", "reparti", "fornitori", "dipendenti", "tagli", "ingresso_merce_repo"]
