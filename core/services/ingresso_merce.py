"""Servizio Ingresso Merce: business logic per ingresso merce e DDT.

Orchestra i repository ``lotti``, ``prodotti`` e ``ingresso_merce_repo``.
Usato dalla UI ingresso merce e dal backend SaaS (endpoint /ingresso-merce).
"""

from core.repositories import lotti as lotti_repo
from core.repositories import prodotti as prodotti_repo
from core.repositories import ingresso_merce_repo as mov_repo


def progressivo_ingresso():
    """Restituisce il progressivo di ingresso corrente."""
    return lotti_repo.recupera_progressivo_ingresso()


def lista_fornitori_ingresso():
    """Restituisce i fornitori abilitati all'ingresso merce."""
    return lotti_repo.recupera_lista_fornitori()


def tagli_per_merceologia(merceologia_id):
    """Restituisce i nomi dei tagli di una merceologia."""
    return prodotti_repo.lista_tagli(merceologia_id)


def nome_merceologia(merceologia_id):
    """Restituisce il nome della merceologia dato il suo ID."""
    return prodotti_repo.recupera_merceologia_da_id(merceologia_id)


def lista_movimenti():
    """Restituisce tutti i movimenti di ingresso merce."""
    return mov_repo.fetch_all()


def movimenti_per_lotto(progressivo_acq):
    """Restituisce i movimenti di ingresso merce per un lotto."""
    return mov_repo.fetch_by_progressivo(progressivo_acq)


def salva_movimento(movimento):
    """Inserisce o aggiorna un movimento di ingresso merce."""
    if movimento.prog_acq is None:
        return mov_repo.insert(movimento)
    return mov_repo.save(movimento)


def elimina_movimento(movimento):
    """Elimina un movimento di ingresso merce."""
    mov_repo.delete(movimento)
