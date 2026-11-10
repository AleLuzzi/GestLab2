"""Servizio applicativo per le vendite tracciate."""

from saas.repositories import tracciabilita_repo


def lotti_disponibili_vendita(tenant_id):
    """Restituisce i lotti vendibili in ordine FEFO per il tenant."""
    return tracciabilita_repo.lotti_disponibili_vendita(tenant_id)


def crea_vendita(tenant_id, data_vendita, cliente_id, tipo_documento):
    """Crea un documento di vendita persistente per il tenant."""
    return tracciabilita_repo.crea_vendita(
        tenant_id=tenant_id,
        data_vendita=data_vendita,
        cliente_id=cliente_id,
        tipo_documento=tipo_documento,
    )


def crea_vendita_completa(tenant_id, data_vendita, cliente_id, tipo_documento, righe):
    """Crea testata, righe e scarichi nella stessa transazione."""
    return tracciabilita_repo.crea_vendita_completa(
        tenant_id=tenant_id,
        data_vendita=data_vendita,
        cliente_id=cliente_id,
        tipo_documento=tipo_documento,
        righe=righe,
    )


def aggiungi_righe_vendita(tenant_id, vendita_id, righe):
    """Registra righe e scarichi di magazzino per il documento."""
    return tracciabilita_repo.aggiungi_righe_vendita(
        tenant_id=tenant_id,
        vendita_id=vendita_id,
        righe=righe,
    )
