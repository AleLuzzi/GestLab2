"""Repository per tenant e utenti del backend SaaS.

Questi accessi usano direttamente ``core.db.connection``. In produzione
(cloud) andranno migrati a SQLAlchemy/Alembic con pool di connessioni.
Il modulo appartiene al package ``saas.repositories``.
"""

import mysql.connector

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


def esegui_onboarding(
    nome,
    piano,
    ragione_sociale,
    indirizzo,
    laboratorio,
    partita_iva,
    email,
    password_hash,
    articoli,
):
    """Crea tenant, dati OSA, admin e catalogo nella stessa transazione.

    ``articoli`` è una sequenza di tuple
    (codice, nome, categoria, unita_misura, utilizzabile_come_input).
    Non crea lotti né giacenze. In caso di errore non resta un tenant parziale.
    """
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO tenant (nome, piano, osa_ragione_sociale, "
                "osa_indirizzo, osa_laboratorio, osa_partita_iva) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    nome,
                    piano,
                    ragione_sociale,
                    indirizzo,
                    laboratorio,
                    partita_iva,
                ),
            )
            tenant_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO utenti "
                "(tenant_id, email, password_hash, ruolo, attivo) "
                "VALUES (%s, %s, %s, 'admin', 1)",
                (tenant_id, email, password_hash),
            )
            utente_id = cursor.lastrowid
            for codice, nome_articolo, categoria, unita, come_input in articoli:
                cursor.execute(
                    "INSERT INTO articoli "
                    "(tenant_id, codice, nome, categoria, unita_misura, "
                    "utilizzabile_come_input) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        tenant_id,
                        codice,
                        nome_articolo,
                        categoria,
                        unita,
                        int(come_input),
                    ),
                )
            conn.commit()
        except mysql.connector.Error:
            conn.rollback()
            raise
    return {
        "tenant_id": tenant_id,
        "utente_id": utente_id,
        "articoli": len(articoli),
    }


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


def salva_token_reset(utente_id, token_hash, scade_il):
    """Invalida i reset aperti dell'utente e registra un nuovo token (solo hash)."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE password_reset SET usato_il = UTC_TIMESTAMP() "
                "WHERE utente_id = %s AND usato_il IS NULL",
                (utente_id,),
            )
            cursor.execute(
                "INSERT INTO password_reset (utente_id, token_hash, scade_il) "
                "VALUES (%s, %s, %s)",
                (utente_id, token_hash, scade_il),
            )
            conn.commit()
        except mysql.connector.Error:
            conn.rollback()
            raise


def annulla_token_reset(token_hash):
    """Elimina un token non ancora usato, per esempio se l'invio email fallisce."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM password_reset "
                "WHERE token_hash = %s AND usato_il IS NULL",
                (token_hash,),
            )
            conn.commit()
        except mysql.connector.Error:
            conn.rollback()
            raise


def consuma_token_reset(token_hash, password_hash):
    """Aggiorna la password e marca il token come usato nella stessa transazione."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, utente_id FROM password_reset "
                "WHERE token_hash = %s AND usato_il IS NULL "
                "AND scade_il > UTC_TIMESTAMP() "
                "FOR UPDATE",
                (token_hash,),
            )
            row = cursor.fetchone()
            if row is None:
                conn.rollback()
                return False
            cursor.execute(
                "UPDATE utenti SET password_hash = %s WHERE id = %s AND attivo = 1",
                (password_hash, row[1]),
            )
            if cursor.rowcount != 1:
                conn.rollback()
                return False
            cursor.execute(
                "UPDATE password_reset SET usato_il = UTC_TIMESTAMP() WHERE id = %s",
                (row[0],),
            )
            cursor.execute(
                "UPDATE refresh_token SET revocato_il = UTC_TIMESTAMP() "
                "WHERE utente_id = %s AND revocato_il IS NULL",
                (row[1],),
            )
            conn.commit()
            return True
        except mysql.connector.Error:
            conn.rollback()
            raise


def salva_refresh_token(utente_id, token_hash, famiglia, scade_il):
    """Registra l'hash di un refresh token. Il valore in chiaro non viene salvato."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO refresh_token "
                "(utente_id, token_hash, famiglia, scade_il) "
                "VALUES (%s, %s, %s, %s)",
                (utente_id, token_hash, famiglia, scade_il),
            )
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error:
            conn.rollback()
            raise


def ruota_refresh_token(token_hash, nuovo_hash, scade_il):
    """Sostituisce un refresh attivo con uno nuovo della stessa famiglia.

    Ritorna ``ruotato`` con l'utente corrente, ``riuso`` se il token era già
    stato ruotato o revocato (e in quel caso chiude la famiglia), oppure
    ``non_valido`` se è assente o scaduto.
    """
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, utente_id, famiglia, "
                "revocato_il IS NOT NULL, scade_il <= UTC_TIMESTAMP() "
                "FROM refresh_token WHERE token_hash = %s FOR UPDATE",
                (token_hash,),
            )
            row = cursor.fetchone()
            if row is None:
                conn.rollback()
                return {"stato": "non_valido"}

            token_id, utente_id, famiglia, revocato, scaduto = row
            if revocato:
                cursor.execute(
                    "UPDATE refresh_token SET revocato_il = UTC_TIMESTAMP() "
                    "WHERE famiglia = %s AND revocato_il IS NULL",
                    (famiglia,),
                )
                conn.commit()
                return {"stato": "riuso"}
            if scaduto:
                conn.rollback()
                return {"stato": "non_valido"}

            cursor.execute(
                "SELECT id, tenant_id, email, ruolo, attivo FROM utenti "
                "WHERE id = %s FOR UPDATE",
                (utente_id,),
            )
            utente = cursor.fetchone()
            if utente is None or not utente[4]:
                cursor.execute(
                    "UPDATE refresh_token SET revocato_il = UTC_TIMESTAMP() "
                    "WHERE famiglia = %s AND revocato_il IS NULL",
                    (famiglia,),
                )
                conn.commit()
                return {"stato": "non_valido"}

            cursor.execute(
                "INSERT INTO refresh_token "
                "(utente_id, token_hash, famiglia, scade_il) "
                "VALUES (%s, %s, %s, %s)",
                (utente_id, nuovo_hash, famiglia, scade_il),
            )
            cursor.execute(
                "UPDATE refresh_token SET revocato_il = UTC_TIMESTAMP() "
                "WHERE id = %s",
                (token_id,),
            )
            conn.commit()
            return {
                "stato": "ruotato",
                "utente": {
                    "id": utente[0],
                    "tenant_id": utente[1],
                    "email": utente[2],
                    "ruolo": utente[3],
                },
            }
        except mysql.connector.Error:
            conn.rollback()
            raise


def revoca_refresh_token(token_hash):
    """Revoca tutti i refresh ancora aperti della famiglia indicata dal token."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT famiglia FROM refresh_token WHERE token_hash = %s "
                "FOR UPDATE",
                (token_hash,),
            )
            row = cursor.fetchone()
            if row is None:
                conn.rollback()
                return
            cursor.execute(
                "UPDATE refresh_token SET revocato_il = UTC_TIMESTAMP() "
                "WHERE famiglia = %s AND revocato_il IS NULL",
                (row[0],),
            )
            conn.commit()
        except mysql.connector.Error:
            conn.rollback()
            raise
