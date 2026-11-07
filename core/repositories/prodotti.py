"""Repository per le query legacy di merceologia e le viste del catalogo.

Migra le funzioni ``_recupera_primi``, ``_recupera_secondi``,
``_recupera_contorni`` e ``_lista_tagli`` da ``controller_db.py`` usando il
pattern context manager di ``core.db`` (niente connessione globale).

Il catalogo operativo è ``articoli``; ``articoli_bilancia`` contiene solo
parametri specifici del tracciato Bizerba.
"""

from ..db import connection


def prodotti_per_merceologia(merceologia, tenant_id=None):
    """Restituisce articoli e PLU Bizerba di una data categoria.

    Args:
        merceologia: nome della merceologia.
        tenant_id: se valorizzato filtra ``tenant_id = %s`` (SaaS).
    """
    query = (
        "SELECT a.nome, b.plu FROM articoli a "
        "LEFT JOIN articoli_bilancia b "
        "ON b.tenant_id = a.tenant_id AND b.articolo_id = a.id "
        "WHERE a.categoria = %s AND a.attivo = 1"
    )
    params = [merceologia]
    if tenant_id is not None:
        query += " AND a.tenant_id = %s"
        params.append(tenant_id)
    query += " ORDER BY a.nome, a.id"

    with connection() as conn:
        c = conn.cursor()
        c.execute(query, tuple(params))
        return [
            {"prodotto": str(row[0]), "plu": str(row[1] or "")}
            for row in c.fetchall()
        ]


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
    """Cerca un articolo tramite EAN o codice articolo.

    Args:
        codice: codice EAN/EAN-13 o codice interno dell'articolo.
        tenant_id: se valorizzato scopa la ricerca per tenant (SaaS).

    Returns:
        I dati dell'articolo trovato, oppure ``None``.
    """
    with connection() as conn:
        c = conn.cursor()
        query = (
            "SELECT a.id, a.nome, b.plu, a.codice, a.ean, "
            "a.prezzo_unitario, a.unita_misura "
            "FROM articoli a LEFT JOIN articoli_bilancia b "
            "ON b.tenant_id = a.tenant_id AND b.articolo_id = a.id "
            "WHERE a.attivo = 1 AND (a.ean = %s OR a.codice = %s)"
        )
        params = [codice, codice]
        if tenant_id is not None:
            query += " AND a.tenant_id = %s"
            params.append(tenant_id)
        query += " ORDER BY (a.ean = %s) DESC LIMIT 1"
        params.append(codice)
        c.execute(query, tuple(params))
        row = c.fetchone()
        if not row:
            return None
        return {
            "articolo_id": row[0],
            "nome": str(row[1]),
            "prodotto": str(row[1]),
            "plu": str(row[2]) if row[2] is not None else "",
            "codice": str(row[3]) if row[3] is not None else "",
            "ean": str(row[4]) if row[4] is not None else "",
            "prezzo_unitario": str(row[5]) if row[5] is not None else "",
            "prezzo_kg": str(row[5]) if row[5] is not None else "",
            "unita_misura": row[6],
        }
