"""Servizio Vendite: business logic per la vendita dei lotti.

Orchestra i repository ``lotti`` per i lotti aperti. In futuro conterra'
anche il calcolo totali, IVA e la generazione di scontrini/DDT (vedi
``core.services.printing``). Usato dalla UI Vendita e dal backend SaaS.
"""

from core.repositories import lotti as lotti_repo


def lotti_aperti():
    """Restituisce i lotti aperti disponibili alla vendita."""
    return lotti_repo.lotti_aperti()


def chiudi_lotto(progressivo_acq):
    """Segna un lotto come chiuso.

    Nota: implementazione basilare; la logica completa di chiusura (recupero
    del movimento, aggiornamento ``lotto_chiuso``) andra' sviluppata nel
    repository ``lotti`` lato SaaS.
    """
    raise NotImplementedError(
        "La chiusura completa del lotto sara' implementata nel service layer SaaS."
    )
