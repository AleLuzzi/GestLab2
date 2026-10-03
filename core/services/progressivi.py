"""Servizio Progressivi: gestione dei contatori per tenant."""

from core import Progressivi
from core.repositories import progressivi as repo


def lista_progressivi(tenant_id=None):
    """Restituisce i record progressivi (opzionalmente filtrati per tenant)."""
    return repo.fetch_all(tenant_id)


def crea_progressivi(prog_acq, prog_ven, tenant_id=None):
    """Crea il record progressivi per il tenant."""
    record = Progressivi(
        prog_acq=prog_acq,
        prog_ven=prog_ven,
        tenant_id=tenant_id,
    )
    return repo.insert(record, tenant_id)


def aggiorna_progressivi(record, prog_acq=None, prog_ven=None, tenant_id=None):
    """Aggiorna i contatori del record esistente."""
    if prog_acq is not None:
        record.prog_acq = prog_acq
    if prog_ven is not None:
        record.prog_ven = prog_ven
    return repo.save(record, tenant_id)


def elimina_progressivi(record, tenant_id=None):
    """Elimina il record progressivi."""
    repo.delete(record, tenant_id)
