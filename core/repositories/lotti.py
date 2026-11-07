"""Repository per la consultazione dei lotti."""

from ..db import connection


def lotti_aperti(tenant_id=None):
    """Restituisce i lotti di ingresso con giacenza disponibile."""
    with connection() as conn:
        c = conn.cursor()
        query = (
            "SELECT l.codice_lotto, d.fornitore, a.nome, l.quantita_disponibile "
            "FROM lotti l "
            "JOIN articoli a ON a.tenant_id = l.tenant_id AND a.id = l.articolo_id "
            "LEFT JOIN documenti_ingresso d "
            "ON d.tenant_id = l.tenant_id AND d.id = l.documento_ingresso_id "
            "WHERE l.tipo_lotto = 'A' AND l.attivo = 1 "
            "AND l.quantita_disponibile > 0"
        )
        if tenant_id is not None:
            query += " AND l.tenant_id = %s"
            c.execute(query + " ORDER BY l.data_creazione DESC, l.id DESC", (tenant_id,))
        else:
            c.execute(query + " ORDER BY l.data_creazione DESC, l.id DESC")
        return [
            {
                "number": str(row[0]),
                "fornit": str(row[1] or ""),
                "name": str(row[2]),
                "peso": str(row[3]),
            }
            for row in c
        ]
