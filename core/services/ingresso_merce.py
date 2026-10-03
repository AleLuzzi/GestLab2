"""Servizio Ingresso Merce: business logic per ingresso merce e DDT.

Orchestra i repository ``lotti``, ``prodotti`` e ``ingresso_merce_repo``.
Usato dalla UI ingresso merce e dal backend SaaS (endpoint /ingresso-merce).
"""

from core.repositories import lotti as lotti_repo
from core.repositories import prodotti as prodotti_repo
from core.repositories import ingresso_merce_repo as mov_repo
from core.core_models import MovIngressoMerce


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


def salva_movimenti(prog_acq, data, num_ddt, fornitore, righe, tenant_id):
    """Salva atomicamente le righe di un ingresso per il tenant corrente."""
    movimenti = [
        MovIngressoMerce(
            prog_acq=prog_acq,
            data=data,
            num_ddt=num_ddt,
            fornitore=fornitore,
            taglio=riga.taglio,
            peso_i=str(riga.peso),
            peso_f=str(riga.peso),
            lotto_chiuso="no",
            id_merc=riga.id_merc,
        )
        for riga in righe
    ]
    return mov_repo.insert_many(movimenti, tenant_id)


def elimina_movimento(movimento):
    """Elimina un movimento di ingresso merce."""
    mov_repo.delete(movimento)
