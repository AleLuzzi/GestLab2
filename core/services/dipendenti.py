"""Servizio Dipendenti: business logic per la gestione dei dipendenti.

Orchestra il repository ``core.repositories.dipendenti`` e il modello
``Dipendente``. Usato dalla UI anagrafica e (in futuro) dal backend SaaS.
"""

from core import Dipendente
from core.repositories import dipendenti as repo


def lista_dipendenti(tenant_id=None):
    """Restituisce tutti i dipendenti (oggetti ``Dipendente``).

    Args:
        tenant_id: se valorizzato filtra per tenant (SaaS).
    """
    return repo.fetch_all(tenant_id)


def trova_dipendente(dipendente_id, tenant_id=None):
    """Cerca un dipendente per ID (opzionalmente scoped al tenant)."""
    return repo.find_by_id(dipendente_id, tenant_id)


def crea_dipendente(nome, email="", reparto=None, tenant_id=None):
    """Crea e salva un nuovo dipendente.

    Args:
        nome: nome del dipendente (obbligatorio).
        email: email (opzionale).
        reparto: id reparto (opzionale).
        tenant_id: se valorizzato, assegna il tenant (SaaS).

    Returns:
        L'oggetto ``Dipendente`` creato (con ``id`` valorizzato).
    """
    nu_Dipendente = Dipendente(nome=nome, email=email, reparto=reparto)
    return repo.insert(nu_Dipendente, tenant_id)


def aggiorna_dipendente(dipendente, nome=None, email=None, reparto=None, tenant_id=None):
    """Aggiorna i campi di un dipendente esistente e lo salva."""
    if nome is not None:
        dipendente.nome = nome
    if email is not None:
        dipendente.email = email
    if reparto is not None:
        dipendente.reparto = reparto
    return repo.save(dipendente, tenant_id)


def elimina_dipendente(dipendente, tenant_id=None):
    """Elimina un dipendente dal database."""
    repo.delete(dipendente, tenant_id)
