"""Onboarding interno di un laboratorio: tenant, OSA, admin e catalogo."""

import mysql.connector

from saas import auth
from saas.repositories import tenant_repo
from saas.schemas import OnboardingRichiesta


# Anagrafica di partenza per una macelleria. Senza prezzi, EAN, lotti o giacenze:
# il laboratorio li registra con l'ingresso e il listino.
TEMPLATE_MACELLERIA = (
    ("BOV-MEZZENA", "Mezzena bovina", "Bovino", "kg", True),
    ("BOV-COLLO", "Collo bovino", "Bovino", "kg", True),
    ("BOV-REALE", "Reale bovino", "Bovino", "kg", True),
    ("BOV-SOTTOSPAL", "Sottospalla bovina", "Bovino", "kg", True),
    ("BOV-FESONE", "Fesone di spalla bovino", "Bovino", "kg", True),
    ("BOV-CAPPELLO", "Cappello del prete bovino", "Bovino", "kg", True),
    ("BOV-FUSELLO", "Girello di spalla bovino", "Bovino", "kg", True),
    ("BOV-TRAVERSIN", "Copertina di sotto bovina", "Bovino", "kg", True),
    ("BOV-BRIONE", "Brione bovino", "Bovino", "kg", True),
    ("BOV-PETTO", "Petto bovino", "Bovino", "kg", True),
    ("BOV-FIOCCO", "Fiocco bovino", "Bovino", "kg", True),
    ("BOV-BIANCO", "Biancostato bovino", "Bovino", "kg", True),
    ("BOV-PANCIA", "Pancia bovina", "Bovino", "kg", True),
    ("BOV-SCALFO", "Scalfo bovino", "Bovino", "kg", True),
    ("BOV-GER-ANT", "Geretto anteriore bovino", "Bovino", "kg", True),
    ("BOV-COSTATA", "Costata bovina", "Bovino", "kg", True),
    ("BOV-CONTROF", "Controfiletto bovino", "Bovino", "kg", True),
    ("BOV-FILETTO", "Filetto bovino", "Bovino", "kg", True),
    ("BOV-SCAMONE", "Scamone bovino", "Bovino", "kg", True),
    ("BOV-FIANCH", "Fianchetto bovino", "Bovino", "kg", True),
    ("BOV-NOCE", "Noce bovina", "Bovino", "kg", True),
    ("BOV-FESA", "Fesa bovina", "Bovino", "kg", True),
    ("BOV-SOTTOF", "Sottofesa bovina", "Bovino", "kg", True),
    ("BOV-CODONE", "Codone bovino", "Bovino", "kg", True),
    ("BOV-GIRELLO", "Girello bovino", "Bovino", "kg", True),
    ("BOV-PESCE", "Pesce bovino", "Bovino", "kg", True),
    ("BOV-GER-POST", "Geretto posteriore bovino", "Bovino", "kg", True),
    ("BOV-CODA", "Coda bovina", "Bovino", "kg", True),
    ("SUI-MEZZENA", "Mezzena di suino", "Suino", "kg", True),
    ("SUI-COPPA", "Coppa di suino", "Suino", "kg", True),
    ("SUI-LONZA", "Lonza di suino", "Suino", "kg", True),
    ("SUI-FILETTO", "Filetto di suino", "Suino", "kg", True),
    ("SUI-COSTINE", "Costine di suino", "Suino", "kg", True),
    ("SUI-SPALLA", "Spalla di suino", "Suino", "kg", True),
    ("SUI-PANCIA", "Pancetta di suino", "Suino", "kg", True),
    ("SUI-GUANCIA", "Guanciale di suino", "Suino", "kg", True),
    ("SUI-LARDO", "Lardo di suino", "Suino", "kg", True),
    ("SUI-COSCIA", "Coscia di suino", "Suino", "kg", True),
    ("SUI-STINCO", "Stinco di suino", "Suino", "kg", True),
    ("SUI-PIEDE", "Piedino di suino", "Suino", "kg", True),
    ("SUI-CODA", "Coda di suino", "Suino", "kg", True),
    ("VIT-MEZZENA", "Mezzena di vitello", "Vitello", "kg", True),
    ("VIT-GER-POST", "Garretto posteriore di vitello", "Vitello", "kg", True),
    ("VIT-PESCE", "Pesce di vitello", "Vitello", "kg", True),
    ("VIT-FESA", "Fesa di vitello", "Vitello", "kg", True),
    ("VIT-SCAMONE", "Scamone di vitello", "Vitello", "kg", True),
    ("VIT-NOCE", "Noce di vitello", "Vitello", "kg", True),
    ("VIT-SOTTOF", "Sottofesa di vitello", "Vitello", "kg", True),
    ("VIT-GIRELLO", "Girello di vitello", "Vitello", "kg", True),
    ("VIT-LOMBO", "Lombo di vitello", "Vitello", "kg", True),
    ("VIT-CARRE", "Carrè di vitello", "Vitello", "kg", True),
    ("VIT-COPPA", "Coppa di vitello", "Vitello", "kg", True),
    ("VIT-PANCIA", "Pancia di vitello", "Vitello", "kg", True),
    ("VIT-PETTO", "Petto di vitello", "Vitello", "kg", True),
    ("VIT-COLLO", "Collo di vitello", "Vitello", "kg", True),
    ("VIT-SPALLA", "Spalla di vitello", "Vitello", "kg", True),
    ("VIT-GER-ANT", "Garretto anteriore di vitello", "Vitello", "kg", True),
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
