"""Repository per la coda di stampa (print_jobs) e dispositivi_stampa.

Gestisce l'accodamento dei job di stampa e il loro ciclo di vita
(pending -> printing -> done/error). Usa ``core.db.connection`` ed e' parte di ``saas.repositories``.
"""

from core.db import connection


# ------------------------------------------------------------------------- #
#  Dispositivi di stampa (Local Print Agent)
# ------------------------------------------------------------------------- #

def registra_dispositivo(tenant_id, nome, token, stampante_dymo=None,
                         stampante_termica=None):
    """Registra un dispositivo di stampa (agent) per un tenant."""
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO dispositivi_stampa "
            "(tenant_id, nome, token, stampante_dymo, stampante_termica) "
            "VALUES (%s, %s, %s, %s, %s)",
            (tenant_id, nome, token, stampante_dymo, stampante_termica),
        )
        conn.commit()
        return c.lastrowid


def trova_dispositivo(tenant_id, dispositivo_id):
    """Legge un dispositivo del tenant senza esporre il token dell'agent."""
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, nome, stampante_dymo, stampante_termica "
            "FROM dispositivi_stampa WHERE tenant_id = %s AND id = %s",
            (tenant_id, dispositivo_id),
        )
        row = c.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "nome": row[1],
            "stampante_dymo": row[2],
            "stampante_termica": row[3],
        }


def trova_dispositivo_by_token(token):
    """Recupera un dispositivo di stampa tramite token (per l'agent)."""
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, tenant_id, nome, token, stampante_dymo, stampante_termica "
            "FROM dispositivi_stampa WHERE token = %s",
            (token,),
        )
        row = c.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "tenant_id": row[1],
            "nome": row[2],
            "token": row[3],
            "stampante_dymo": row[4],
            "stampante_termica": row[5],
        }


def aggiorna_heartbeat(dispositivo_id, tenant_id):
    """Aggiorna l'heartbeat del dispositivo autenticato."""
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE dispositivi_stampa SET ultimo_heartbeat = NOW() "
            "WHERE id = %s AND tenant_id = %s",
            (dispositivo_id, tenant_id),
        )
        conn.commit()


# ------------------------------------------------------------------------- #
#  Coda di stampa (print_jobs)
# ------------------------------------------------------------------------- #

def accoda_job(tenant_id, dispositivo_id, tipo, payload):
    """Inserisce un nuovo job di stampa in coda (stato 'pending')."""
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO print_jobs (tenant_id, dispositivo_id, tipo, payload) "
            "VALUES (%s, %s, %s, %s)",
            (tenant_id, dispositivo_id, tipo, payload),
        )
        conn.commit()
        return c.lastrowid


def elenca_job(tenant_id, stato=None, limite=100):
    """Elenco dei job di stampa di un tenant (opzionale filtro per stato)."""
    with connection() as conn:
        c = conn.cursor()
        if stato:
            c.execute(
                "SELECT id, tenant_id, dispositivo_id, tipo, stato, payload, "
                "creato_il, stampato_il FROM print_jobs "
                "WHERE tenant_id = %s AND stato = %s ORDER BY id ASC LIMIT %s",
                (tenant_id, stato, limite),
            )
        else:
            c.execute(
                "SELECT id, tenant_id, dispositivo_id, tipo, stato, payload, "
                "creato_il, stampato_il FROM print_jobs "
                "WHERE tenant_id = %s ORDER BY id ASC LIMIT %s",
                (tenant_id, limite),
            )
        return [
            {
                "id": r[0],
                "tenant_id": r[1],
                "dispositivo_id": r[2],
                "tipo": r[3],
                "stato": r[4],
                "payload": r[5],
                "creato_il": str(r[6]) if r[6] else None,
                "stampato_il": str(r[7]) if r[7] else None,
            }
            for r in c.fetchall()
        ]


def prendi_prossimo_job(dispositivo_id, tenant_id):
    """Preleva il prossimo job 'pending' del tenant del dispositivo (FIFO).

    Imposta lo stato a 'printing' nella stessa transazione. I job di un
    altro tenant non sono visibili, anche se non hanno un dispositivo assegnato.
    """
    with connection() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, tenant_id, dispositivo_id, tipo, payload "
            "FROM print_jobs WHERE stato = 'pending' AND tenant_id = %s "
            "AND (dispositivo_id IS NULL OR dispositivo_id = %s) "
            "ORDER BY id ASC LIMIT 1 FOR UPDATE",
            (tenant_id, dispositivo_id),
        )
        row = c.fetchone()
        if not row:
            return None
        job_id = row[0]
        c.execute(
            "UPDATE print_jobs SET stato = 'printing' "
            "WHERE id = %s AND tenant_id = %s",
            (job_id, tenant_id),
        )
        conn.commit()
        return {
            "id": row[0],
            "tenant_id": row[1],
            "dispositivo_id": row[2],
            "tipo": row[3],
            "payload": row[4],
        }


def aggiorna_stato_job(job_id, stato, tenant_id):
    """Aggiorna lo stato di un job del tenant e il timestamp di stampa."""
    with connection() as conn:
        c = conn.cursor()
        if stato == "done":
            c.execute(
                "UPDATE print_jobs SET stato = %s, stampato_il = NOW() "
                "WHERE id = %s AND tenant_id = %s",
                (stato, job_id, tenant_id),
            )
        else:
            c.execute(
                "UPDATE print_jobs SET stato = %s WHERE id = %s AND tenant_id = %s",
                (stato, job_id, tenant_id),
            )
        aggiornato = c.rowcount > 0
        conn.commit()
        return aggiornato
