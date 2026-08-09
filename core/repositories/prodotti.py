"""Repository per i prodotti (query merceologiche).

Migra le funzioni ``_recupera_primi``, ``_recupera_secondi``,
``_recupera_contorni`` e ``_lista_tagli`` da ``controller_db.py`` usando il
pattern context manager di ``core.db`` (niente connessione globale).
"""

from ..db import connection


def prodotti_per_merceologia(merceologia, tenant_id=None):
    """Restituisce i prodotti (prodotto, plu) di una data merceologia.

    Args:
        merceologia: nome della merceologia.
        tenant_id: se valorizzato filtra ``tenant_id = %s`` (SaaS).
    """
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT prodotto, plu FROM prodotti "
                "WHERE merceologia = %s AND tenant_id = %s",
                (merceologia, tenant_id),
            )
        else:
            c.execute(
                "SELECT prodotto, plu FROM prodotti WHERE merceologia = %s",
                (merceologia,),
            )
        return [{"prodotto": str(x[0]), "plu": str(x[1])} for x in c]


def recupera_primi(tenant_id=None):
    """Prodotti della merceologia 'Primi piatti'."""
    return prodotti_per_merceologia("Primi piatti", tenant_id)


def recupera_secondi(tenant_id=None):
    """Prodotti della merceologia 'Secondi piatti'."""
    return prodotti_per_merceologia("Secondi piatti", tenant_id)


def recupera_contorni(tenant_id=None):
    """Prodotti della merceologia 'Contorni'."""
    return prodotti_per_merceologia("Contorni", tenant_id)


def lista_tagli(merceologia_id, tenant_id=None):
    """Restituisce i tagli (nomi) di una data merceologia (per Id)."""
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT taglio FROM tagli "
                "WHERE Id_Merceologia=%s AND tenant_id = %s",
                (merceologia_id, tenant_id),
            )
        else:
            c.execute(
                "SELECT taglio FROM tagli WHERE Id_Merceologia=%s",
                (merceologia_id,),
            )
        return [x[0] for x in c]


def recupera_merceologia_da_id(merceologia_id):
    """Restituisce il nome della merceologia dato il suo Id."""
    with connection() as conn:
        c = conn.cursor()
        c.execute("SELECT merceologia FROM merceologie WHERE Id = %s", (merceologia_id,))
        row = c.fetchone()
        return row[0] if row else None


def trova_per_ean(codice, tenant_id=None):
    """Cerca un prodotto tramite codice EAN.

    Args:
        codice: codice EAN/EAN-13 del prodotto.
        tenant_id: se valorizzato scopa la ricerca per tenant (SaaS).

    Returns:
        Un dict ``{'prodotto', 'plu', 'codice', 'prezzo_kg'}`` oppure ``None``
        se non trovato.
    """
    with connection() as conn:
        c = conn.cursor()
        if tenant_id is not None:
            c.execute(
                "SELECT prodotto, plu, codice, prezzo_kg FROM prodotti "
                "WHERE codice = %s AND tenant_id = %s",
                (codice, tenant_id),
            )
        else:
            c.execute(
                "SELECT prodotto, plu, codice, prezzo_kg FROM prodotti "
                "WHERE codice = %s",
                (codice,),
            )
        row = c.fetchone()
        if not row:
            return None
        return {
            "prodotto": str(row[0]),
            "plu": str(row[1]) if row[1] is not None else "",
            "codice": str(row[2]) if row[2] is not None else "",
            "prezzo_kg": str(row[3]) if row[3] is not None else "",
        }
