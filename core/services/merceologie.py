"""Servizio Merceologie: business logic per la gestione delle merceologie.

Orchestra il repository ``core.repositories.merceologie`` e il modello
``Merceologia``. Usato dalla UI anagrafica e (in futuro) dal backend SaaS.
"""

from core import Merceologia
from core.repositories import merceologie as repo


def lista_merceologie(tenant_id=None):
    """Restituisce tutte le merceologie (oggetti ``Merceologia``).

    Args:
        tenant_id: se valorizzato filtra per tenant (SaaS).
    """
    return repo.fetch_all(tenant_id)


def trova_merceologia(merceologia_id, tenant_id=None):
    """Cerca una merceologia per ID (opzionalmente scoped al tenant)."""
    return repo.find_by_id(merceologia_id, tenant_id)


def crea_merceologia(merceologia, id_reparto=None, flag1_inv=0, flag2_taglio=0, flag3_ing_base=0, tenant_id=None):
    """Crea e salva una nuova merceologia.

    Args:
        merceologia: nome della merceologia (obbligatorio).
        id_reparto: id reparto (opzionale).
        flag1_inv: flag inventario (0/1, default 0).
        flag2_taglio: flag taglio (0/1, default 0).
        flag3_ing_base: flag ingredienti base (0/1, default 0).
        tenant_id: se valorizzato, assegna il tenant (SaaS).

    Returns:
        L'oggetto ``Merceologia`` creato (con ``id`` valorizzato).
    """
    nu_Merceologia = Merceologia(
        merceologia=merceologia,
        id_reparto=id_reparto,
        flag1_inv=flag1_inv,
        flag2_taglio=flag2_taglio,
        flag3_ing_base=flag3_ing_base,
    )
    return repo.insert(nu_Merceologia, tenant_id)


def aggiorna_merceologia(merceologia, merceologia_nome=None, id_reparto=None, 
                         flag1_inv=None, flag2_taglio=None, flag3_ing_base=None, tenant_id=None):
    """Aggiorna i campi di una merceologia esistente e la salva."""
    if merceologia_nome is not None:
        merceologia.merceologia = merceologia_nome
    if id_reparto is not None:
        merceologia.id_reparto = id_reparto
    if flag1_inv is not None:
        merceologia.flag1_inv = int(flag1_inv)
    if flag2_taglio is not None:
        merceologia.flag2_taglio = int(flag2_taglio)
    if flag3_ing_base is not None:
        merceologia.flag3_ing_base = int(flag3_ing_base)
    return repo.save(merceologia, tenant_id)


def elimina_merceologia(merceologia, tenant_id=None):
    """Elimina una merceologia dal database."""
    repo.delete(merceologia, tenant_id)
