"""Servizio Reparti: business logic per la gestione dei reparti.

Orchestra il repository ``core.repositories.reparti`` e il modello
``Reparto``. Usato dalla UI anagrafica e dal backend SaaS.
"""

from core import Reparto
from core.repositories import reparti as repo


def lista_reparti(tenant_id=None):
    """Restituisce tutti i reparti (oggetti ``Reparto``)."""
    return repo.fetch_all(tenant_id)


def trova_reparto(reparto_id, tenant_id=None):
    """Cerca un reparto per ID (opzionalmente scoped al tenant)."""
    return repo.find_by_id(reparto_id, tenant_id)


def crea_reparto(nome, flag1_dip=0, flag2_prod=0, tenant_id=None):
    """Crea e salva un nuovo reparto."""
    nuovo_reparto = Reparto(reparto=nome, flag1_dip=flag1_dip, flag2_prod=flag2_prod)
    return repo.insert(nuovo_reparto, tenant_id)


def aggiorna_reparto(reparto, nome=None, flag1_dip=None, flag2_prod=None, tenant_id=None):
    """Aggiorna i campi di un reparto esistente e lo salva."""
    if nome is not None:
        reparto.reparto = nome
    if flag1_dip is not None:
        reparto.flag1_dip = int(flag1_dip)
    if flag2_prod is not None:
        reparto.flag2_prod = int(flag2_prod)
    return repo.save(reparto, tenant_id)


def elimina_reparto(reparto, tenant_id=None):
    """Elimina un reparto dal database."""
    repo.delete(reparto, tenant_id)
