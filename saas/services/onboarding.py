"""Onboarding interno di un laboratorio: tenant, OSA, admin e catalogo."""

import mysql.connector

from saas import auth
from saas.repositories import tenant_repo
from saas.schemas import OnboardingRichiesta


# Anagrafica di partenza per una macelleria. Senza prezzi, EAN, lotti o giacenze:
# il laboratorio li registra con l'ingresso e il listino.
TEMPLATE_MACELLERIA = (
    ("BOV-MEZZENA", "Mezzena bovina", "Bovino", "kg", True),
    ("BOV-MUSCOLO", "Muscolo bovino", "Bovino", "kg", True),
    ("SUI-PANCIA", "Pancia di suino", "Suino", "kg", True),
    ("SUI-SPALLA", "Spalla di suino", "Suino", "kg", True),
    ("SUI-COSCIA", "Coscia di suino", "Suino", "kg", True),
    ("COND-SALE", "Sale", "Condimento", "kg", True),
    ("PREP-SALSICCIA", "Salsicce fresche", "Preparato", "kg", False),
    ("PREP-HAMBURGER", "Hamburger di bovino", "Preparato", "kg", False),
    ("PREP-ARROSTO", "Arrosto di vitello", "Preparato", "kg", False),
)


class OnboardingError(Exception):
    """Dati rifiutati o già presenti: il laboratorio non è stato creato."""


def crea_laboratorio(dati: OnboardingRichiesta) -> dict:
    """Crea il laboratorio e restituisce gli id, senza la password."""
    try:
        auth.valida_password(dati.password)
    except ValueError as exc:
        raise OnboardingError(str(exc)) from exc
    articoli = () if dati.catalogo == "vuoto" else TEMPLATE_MACELLERIA
    try:
        esito = tenant_repo.esegui_onboarding(
            dati.nome,
            dati.piano,
            dati.ragione_sociale,
            dati.indirizzo,
            dati.laboratorio,
            dati.partita_iva,
            str(dati.email),
            auth.hash_password(dati.password),
            articoli,
        )
    except mysql.connector.IntegrityError as exc:
        messaggio = str(exc).lower()
        if getattr(exc, "errno", None) == 1062 and "email" in messaggio:
            raise OnboardingError(
                "Esiste già un utente con questa email."
            ) from exc
        raise OnboardingError(
            "Impossibile completare l'onboarding: un dato risulta già presente."
        ) from exc
    except mysql.connector.Error as exc:
        raise OnboardingError("Impossibile creare il laboratorio.") from exc
    return {
        "tenant_id": esito["tenant_id"],
        "utente_id": esito["utente_id"],
        "email": str(dati.email),
        "catalogo": dati.catalogo,
        "articoli": esito["articoli"],
    }
