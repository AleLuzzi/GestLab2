"""Servizio Tagli: business logic per la gestione dei tagli.

Orchestra il repository ``core.repositories.tagli`` e il modello
``Taglio``. Usato dalla UI anagrafica e dal backend SaaS.
"""

from core import Taglio
from core.repositories import tagli as repo


def lista_tagli(tenant_id=None):
    """Restituisce tutti i tagli (oggetti ``Taglio``)."""
    return repo.fetch_all(tenant_id)


def trova_taglio(taglio_id, tenant_id=None):
    """Cerca un taglio per ID (opzionalmente scoped al tenant)."""
    return repo.find_by_id(taglio_id, tenant_id)


def crea_taglio(taglio, id_merceologia=None, tenant_id=None):
    """Crea e salva un nuovo taglio."""
    nuovo = Taglio(taglio=taglio, id_merceologia=id_merceologia)
    return repo.insert(nuovo, tenant_id)


def aggiorna_taglio(taglio_obj, nome=None, id_merceologia=None, tenant_id=None):
    """Aggiorna i campi di un taglio esistente e lo salva."""
    if nome is not None:
        taglio_obj.taglio = nome
    if id_merceologia is not None:
        taglio_obj.id_merceologia = id_merceologia
    return repo.save(taglio_obj, tenant_id)


def elimina_taglio(taglio_obj, tenant_id=None):
    """Elimina un taglio dal database."""
    repo.delete(taglio_obj, tenant_id)
