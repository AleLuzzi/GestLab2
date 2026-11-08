"""Repository per tenant e utenti del backend SaaS.

Questi accessi usano direttamente ``core.db.connection``. In produzione
(cloud) andranno migrati a SQLAlchemy/Alembic con pool di connessioni.
Il modulo appartiene al package ``saas.repositories``.
"""

from core.db import connection


def crea_tenant(nome, piano="basic"):
    """Crea un nuovo tenant e restituisce il suo id."""
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO tenant (nome, piano) VALUES (%s, %s)",
            (nome, piano),
        )
        conn.commit()
        return c.lastrowid


def trova_tenant(tenant_id):
    """Recupera un tenant per id."""
    with connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, nome, piano, attivo FROM tenant WHERE id = %s", (tenant_id,))
        row = c.fetchone()
        if not row:
            return None
        return {"id": row[0], "nome": row[1], "piano": row[2], "attivo": row[3]}


def dati_osa(tenant_id):
    """Recupera i dati OSA associati al tenant."""
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT osa_ragione_sociale, osa_indirizzo, osa_laboratorio, "
            "osa_partita_iva FROM tenant WHERE id = %s",
            (tenant_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "ragione_sociale": row[0] or "",
            "indirizzo": row[1] or "",
            "laboratorio": row[2] or "",
            "partita_iva": row[3] or "",
        }


def aggiorna_dati_osa(tenant_id, dati):
    """Aggiorna i dati OSA senza consentire modifiche al tenant."""
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tenant SET osa_ragione_sociale = %s, osa_indirizzo = %s, "
            "osa_laboratorio = %s, osa_partita_iva = %s WHERE id = %s",
            (
                dati["ragione_sociale"],
                dati["indirizzo"],
                dati["laboratorio"],
                dati["partita_iva"],
                tenant_id,
            ),
        )
        if cursor.rowcount == 0:
            cursor.execute("SELECT id FROM tenant WHERE id = %s", (tenant_id,))
            if cursor.fetchone() is None:
                conn.rollback()
                return False
        conn.commit()
        return True


def trova_utente_by_email(email):
    """Recupera un utente (con tenant) tramite email."""
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT u.id, u.tenant_id, u.email, u.password_hash, u.ruolo, u.attivo,
                   t.nome AS tenant_nome
            FROM utenti u
            JOIN tenant t ON t.id = u.tenant_id
            WHERE u.email = %s
            """,
            (email,),
        )
        row = c.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "tenant_id": row[1],
            "email": row[2],
            "password_hash": row[3],
            "ruolo": row[4],
            "attivo": row[5],
            "tenant_nome": row[6],
        }


def crea_utente(tenant_id, email, password_hash, ruolo="operatore", attivo=True):
    """Crea un nuovo utente associato a un tenant."""
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO utenti (tenant_id, email, password_hash, ruolo, attivo) "
            "VALUES (%s, %s, %s, %s, %s)",
            (tenant_id, email, password_hash, ruolo, int(attivo)),
        )
        conn.commit()
        return c.lastrowid
