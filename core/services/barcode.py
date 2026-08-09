"""Service layer barcode (lookup EAN/QR).

Gestisce la lettura di codici a barre (EAN-13, QR) e il lookup del prodotto
associato. In un contesto SaaS il lookup avviene via API
(``GET /api/v1/prodotti/ean/{codice}``) con scoping per tenant; qui e'
esposto come funzione di servizio riusabile sia dal backend sia dalla UI.

I lettori barcode commerciali sono *keyboard-wedge* (HID): inviano la stringa
+ Enter come una tastiera. La validazione EAN-13 check digit e' quindi
obbligatoria per scartare letture errate (vedi ``SAAS_PRINTING_BARCODE_PLAN.md``).
"""

from typing import Optional


def valida_ean13(codice: str) -> bool:
    """Verifica la check digit di un codice EAN-13.

    Args:
        codice: stringa EAN-13 (12 cifre + check digit).

    Returns:
        ``True`` se il codice ha 13 cifre e la check digit e' corretta.
    """
    if not isinstance(codice, str) or not codice.isdigit() or len(codice) != 13:
        return False

    # Somma: posizioni dispari (1,3,5...) peso 1; pari peso 3; ultima = check.
    somma = sum(int(d) for d in codice[:-1][0::2]) + \
        3 * sum(int(d) for d in codice[:-1][1::2])
    check = (10 - (somma % 10)) % 10
    return check == int(codice[-1])


def normalizza_codice(codice: str) -> str:
    """Rimuove spazi, trattini e caratteri non desiderati dal codice letto."""
    if not codice:
        return ""
    return "".join(ch for ch in codice.strip() if ch.isalnum())


def lookup_prodotto(codice: str, tenant_id: Optional[int] = None) -> Optional[dict]:
    """Cerca un prodotto mediante codice EAN.

    Normalizza il codice, valida l'EAN-13 (se applicabile) ed esegue il lookup
    nel repository ``prodotti``. In SaaS il ``tenant_id`` scopa la ricerca.

    Args:
        codice: codice EAN letto dal barcode.
        tenant_id: id del tenant (opzionale; ``None`` = nessun filtro).

    Returns:
        Un dict con i dati del prodotto, oppure ``None`` se non trovato.
    """
    from core.repositories import prodotti as prodotti_repo

    codice = normalizza_codice(codice)
    if not codice:
        return None

    # Se sembra un EAN-13, validiamo la check digit.
    if len(codice) == 13 and not valida_ean13(codice):
        return None

    # Lookup per EAN sul repository prodotti (aggiungere metodo dedicato).
    # Nota: il repository prodotti recupera per merceologia; per il lookup
    # diretto EAN aggiungere una funzione ``prodotti.trova_per_ean`` in core.
    return prodotti_repo.trova_per_ean(codice, tenant_id)


# ------------------------------------------------------------------------- #
#  Helpers per la gestione input da lettore HID
# ------------------------------------------------------------------------- #

def e_un_input_barcode(completo: str, separatore_atteso="\r") -> bool:
    """Indica se una stringa intera puo' essere il risultato di un lettore.

    I lettori HID inviano il codice seguito da Enter (``\\r`` o ``\\n``).
    Se la stringa termina con il separatore e contiene solo alfanumerici
    (prevalentemente cifre), e' molto probabilmente un barcode.
    """
    if not completo:
        return False
    if not completo.endswith(separatore_atteso):
        return False
    chunk = completo[:-len(separatore_atteso)]
    return chunk.isalnum() and any(ch.isdigit() for ch in chunk)
