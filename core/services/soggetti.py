"""Servizio per l'anagrafica condivisa di clienti e fornitori."""

from core.repositories import soggetti as repo


def lista_soggetti(tenant_id):
    return repo.lista(tenant_id)


def trova_soggetto(tenant_id, soggetto_id):
    return repo.trova(tenant_id, soggetto_id)


def crea_soggetto(tenant_id, payload):
    return repo.crea(tenant_id, payload)


def aggiorna_soggetto(tenant_id, soggetto_id, payload):
    return repo.aggiorna(tenant_id, soggetto_id, payload)


def disattiva_soggetto(tenant_id, soggetto_id):
    return repo.disattiva(tenant_id, soggetto_id)
