"""Servizio Fornitori: business logic per la gestione dei fornitori.

Orchestra il repository ``core.repositories.fornitori`` e il modello
``Fornitore``. Usato dalla UI anagrafica e dal backend SaaS.
"""

from core import Fornitore
from core.repositories import fornitori as repo


def lista_fornitori(tenant_id=None):
    """Restituisce tutti i fornitori (oggetti ``Fornitore``)."""
    return repo.fetch_all(tenant_id)


def trova_fornitore(fornitore_id, tenant_id=None):
    """Cerca un fornitore per ID (opzionalmente scoped al tenant)."""
    return repo.find_by_id(fornitore_id, tenant_id)


def crea_fornitore(azienda, flag1_ing_merce=0, flag2_inventario=0, tenant_id=None):
    """Crea e salva un nuovo fornitore."""
    nuovo = Fornitore(
        azienda=azienda,
        flag1_ing_merce=flag1_ing_merce,
        flag2_inventario=flag2_inventario,
    )
    return repo.insert(nuovo, tenant_id)


def aggiorna_fornitore(
    fornitore,
    azienda=None,
    flag1_ing_merce=None,
    flag2_inventario=None,
    tenant_id=None,
):
    """Aggiorna i campi di un fornitore esistente e lo salva."""
    if azienda is not None:
        fornitore.azienda = azienda
    if flag1_ing_merce is not None:
        fornitore.flag1_ing_merce = int(flag1_ing_merce)
    if flag2_inventario is not None:
        fornitore.flag2_inventario = int(flag2_inventario)
    return repo.save(fornitore, tenant_id)


def elimina_fornitore(fornitore, tenant_id=None):
    """Elimina un fornitore dal database."""
    repo.delete(fornitore, tenant_id)
