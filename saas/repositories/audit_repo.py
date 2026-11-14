"""Lettura tenant-scoped dell'audit log."""

from core.db import connection


def lista(tenant_id, limite=100):
    """Restituisce gli eventi più recenti del tenant, dal più nuovo."""
    limite = max(1, min(int(limite), 200))
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, utente_email, azione, entita, entita_id, dettaglio, creato_il "
            "FROM audit_log WHERE tenant_id = %s ORDER BY id DESC LIMIT %s",
            (tenant_id, limite),
        )
        return [
            {
                "id": row[0],
                "utente_email": row[1],
                "azione": row[2],
                "entita": row[3],
                "entita_id": row[4],
                "dettaglio": row[5],
                "creato_il": row[6],
            }
            for row in cursor.fetchall()
        ]
