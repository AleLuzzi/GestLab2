"""Repository SaaS per articoli, lotti d'ingresso e lavorazioni."""

from collections import defaultdict
from decimal import Decimal

from core.db import connection


class ArticoloNonTrovato(Exception):
    """Articolo inesistente o non appartenente al tenant."""


class LottoNonTrovato(Exception):
    """Lotto inesistente o non appartenente al tenant."""


class DipendenteNonTrovato(Exception):
    """Dipendente inesistente o non appartenente al tenant."""


class GiacenzaInsufficiente(Exception):
    """La quantità richiesta supera la giacenza disponibile."""


def lista_articoli(tenant_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, codice, nome, categoria, unita_misura, attivo "
            "FROM articoli WHERE tenant_id = %s ORDER BY nome, id",
            (tenant_id,),
        )
        return [
            {
                "id": row[0],
                "codice": row[1],
                "nome": row[2],
                "categoria": row[3],
                "unita_misura": row[4],
                "attivo": bool(row[5]),
            }
            for row in cursor.fetchall()
        ]


def crea_articolo(tenant_id, codice, nome, categoria, unita_misura):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO articoli "
            "(tenant_id, codice, nome, categoria, unita_misura) "
            "VALUES (%s, %s, %s, %s, %s)",
            (tenant_id, codice, nome, categoria, unita_misura),
        )
        articolo_id = cursor.lastrowid
        conn.commit()
    return {
        "id": articolo_id,
        "codice": codice,
        "nome": nome,
        "categoria": categoria,
        "unita_misura": unita_misura,
        "attivo": True,
    }


def aggiorna_articolo(tenant_id, articolo_id, codice, nome, categoria, unita_misura, attivo):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE articoli SET codice = %s, nome = %s, categoria = %s, "
            "unita_misura = %s, attivo = %s "
            "WHERE tenant_id = %s AND id = %s",
            (codice, nome, categoria, unita_misura, int(attivo), tenant_id, articolo_id),
        )
        cursor.execute(
            "SELECT id, codice, nome, categoria, unita_misura, attivo "
            "FROM articoli WHERE tenant_id = %s AND id = %s",
            (tenant_id, articolo_id),
        )
        row = cursor.fetchone()
        if row is None:
            conn.rollback()
            return None
        conn.commit()
    return {
        "id": row[0],
        "codice": row[1],
        "nome": row[2],
        "categoria": row[3],
        "unita_misura": row[4],
        "attivo": bool(row[5]),
    }


def disattiva_articolo(tenant_id, articolo_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE articoli SET attivo = 0 WHERE tenant_id = %s AND id = %s",
            (tenant_id, articolo_id),
        )
        cursor.execute(
            "SELECT id FROM articoli WHERE tenant_id = %s AND id = %s",
            (tenant_id, articolo_id),
        )
        esistente = cursor.fetchone() is not None
        if esistente:
            conn.commit()
        else:
            conn.rollback()
        return esistente


def lista_lotti(tenant_id, solo_disponibili=False):
    query = (
        "SELECT l.id, l.articolo_id, a.nome, l.tipo_lotto, l.progressivo, "
        "l.codice_lotto, l.data_creazione, l.quantita_iniziale, "
        "l.quantita_disponibile, l.unita_misura, l.documento_ingresso_id, "
        "l.lavorazione_id, a.categoria "
        "FROM lotti l JOIN articoli a "
        "ON a.tenant_id = l.tenant_id AND a.id = l.articolo_id "
        "WHERE l.tenant_id = %s"
    )
    params = [tenant_id]
    if solo_disponibili:
        query += " AND l.quantita_disponibile > 0"
    query += " ORDER BY l.data_creazione DESC, l.id DESC"

    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [
            {
                "id": row[0],
                "articolo_id": row[1],
                "articolo": row[2],
                "tipo_lotto": row[3],
                "progressivo": row[4],
                "codice_lotto": row[5],
                "data_creazione": row[6],
                "quantita_iniziale": str(row[7]),
                "quantita_disponibile": str(row[8]),
                "unita_misura": row[9],
                "documento_ingresso_id": row[10],
                "lavorazione_id": row[11],
                "categoria": row[12],
            }
            for row in cursor.fetchall()
        ]


def dettaglio_lotto(tenant_id, lotto_id):
    """Restituisce lotto, origine e input/output della sua lavorazione."""
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT l.id, l.articolo_id, a.nome, l.tipo_lotto, l.progressivo, "
            "l.codice_lotto, l.data_creazione, l.quantita_iniziale, "
            "l.quantita_disponibile, l.unita_misura, l.documento_ingresso_id, "
            "l.lavorazione_id, d.data_ingresso, d.numero_ddt, d.fornitore, "
            "w.data_lavorazione, w.descrizione, "
            "COALESCE(NULLIF(TRIM(CONCAT_WS(' ', dp.nome, dp.cognome)), ''), w.operatore) "
            "FROM lotti l "
            "JOIN articoli a ON a.tenant_id = l.tenant_id AND a.id = l.articolo_id "
            "LEFT JOIN documenti_ingresso d "
            "ON d.tenant_id = l.tenant_id AND d.id = l.documento_ingresso_id "
            "LEFT JOIN lavorazioni w "
            "ON w.tenant_id = l.tenant_id AND w.id = l.lavorazione_id "
            "LEFT JOIN dipendenti dp "
            "ON dp.tenant_id = w.tenant_id AND dp.ID = w.operatore_id "
            "WHERE l.tenant_id = %s AND l.id = %s",
            (tenant_id, lotto_id),
        )
        row = cursor.fetchone()
        if not row:
            return None

        risultato = {
            "id": row[0],
            "articolo_id": row[1],
            "articolo": row[2],
            "tipo_lotto": row[3],
            "progressivo": row[4],
            "codice_lotto": row[5],
            "data_creazione": row[6],
            "quantita_iniziale": str(row[7]),
            "quantita_disponibile": str(row[8]),
            "unita_misura": row[9],
            "documento_ingresso_id": row[10],
            "lavorazione_id": row[11],
            "documento_ingresso": None,
            "lavorazione": None,
        }
        if row[10] is not None:
            risultato["documento_ingresso"] = {
                "id": row[10],
                "data": row[12],
                "numero_ddt": row[13],
                "fornitore": row[14],
            }
        cursor.execute(
            "SELECT tipo, quantita_delta, creato_il FROM movimenti_lotto "
            "WHERE tenant_id = %s AND lotto_id = %s ORDER BY id",
            (tenant_id, lotto_id),
        )
        risultato["movimenti"] = [
            {
                "tipo": item[0],
                "quantita_delta": str(item[1]),
                "creato_il": item[2],
            }
            for item in cursor.fetchall()
        ]
        if row[11] is not None:
            cursor.execute(
                "SELECT li.lotto_id, lp.codice_lotto, ap.nome, li.quantita "
                "FROM lavorazione_input li "
                "JOIN lotti lp ON lp.tenant_id = li.tenant_id AND lp.id = li.lotto_id "
                "JOIN articoli ap ON ap.tenant_id = lp.tenant_id AND ap.id = lp.articolo_id "
                "WHERE li.tenant_id = %s AND li.lavorazione_id = %s "
                "ORDER BY li.id",
                (tenant_id, row[11]),
            )
            input_rows = [
                {
                    "lotto_id": item[0],
                    "codice_lotto": item[1],
                    "articolo": item[2],
                    "quantita": str(item[3]),
                }
                for item in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT lo.lotto_id, lp.codice_lotto, a.nome, lo.quantita "
                "FROM lavorazione_output lo "
                "JOIN lotti lp ON lp.tenant_id = lo.tenant_id AND lp.id = lo.lotto_id "
                "JOIN articoli a ON a.tenant_id = lo.tenant_id AND a.id = lo.articolo_id "
                "WHERE lo.tenant_id = %s AND lo.lavorazione_id = %s "
                "ORDER BY lo.id",
                (tenant_id, row[11]),
            )
            output_rows = [
                {
                    "lotto_id": item[0],
                    "codice_lotto": item[1],
                    "articolo": item[2],
                    "quantita": str(item[3]),
                }
                for item in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT descrizione, quantita, unita_misura "
                "FROM lavorazione_scarto "
                "WHERE tenant_id = %s AND lavorazione_id = %s ORDER BY id",
                (tenant_id, row[11]),
            )
            scarti = [
                {
                    "descrizione": item[0],
                    "quantita": str(item[1]),
                    "unita_misura": item[2],
                }
                for item in cursor.fetchall()
            ]
            risultato["lavorazione"] = {
                "id": row[11],
                "data": row[15],
                "descrizione": row[16],
                "operatore": row[17],
                "input": input_rows,
                "output": output_rows,
                "scarti": scarti,
            }
        return risultato


def _prossimo_progressivo(cursor, tenant_id, tipo_lotto):
    column = {"A": "prog_acq", "V": "prog_ven"}[tipo_lotto]
    cursor.execute(
        "INSERT INTO progressivi (tenant_id, prog_acq, prog_ven) "
        "VALUES (%s, 0, 0) ON DUPLICATE KEY UPDATE tenant_id = VALUES(tenant_id)",
        (tenant_id,),
    )
    cursor.execute(
        f"SELECT {column} FROM progressivi WHERE tenant_id = %s FOR UPDATE",
        (tenant_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        raise RuntimeError("Impossibile leggere il progressivo del tenant.")
    row = rows[0]
    numero = int(row[0] or 0) + 1
    cursor.execute(
        f"UPDATE progressivi SET {column} = %s WHERE tenant_id = %s",
        (numero, tenant_id),
    )
    return numero


def registra_ingresso(tenant_id, data, numero_ddt, fornitore, righe):
    """Registra un documento e crea un lotto A distinto per ogni sua riga."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            articolo_ids = sorted({riga.articolo_id for riga in righe})
            placeholders = ", ".join(["%s"] * len(articolo_ids))
            cursor.execute(
                "SELECT id, unita_misura FROM articoli "
                f"WHERE tenant_id = %s AND attivo = 1 AND id IN ({placeholders})",
                (tenant_id, *articolo_ids),
            )
            articoli = {row[0]: row[1] for row in cursor.fetchall()}
            if len(articoli) != len(articolo_ids):
                raise ArticoloNonTrovato

            cursor.execute(
                "INSERT INTO documenti_ingresso "
                "(tenant_id, data_ingresso, numero_ddt, fornitore) "
                "VALUES (%s, %s, %s, %s)",
                (tenant_id, data, numero_ddt, fornitore),
            )
            documento_id = cursor.lastrowid
            lotti_creati = []

            for riga in righe:
                numero = _prossimo_progressivo(cursor, tenant_id, "A")
                codice = f"{numero}A"
                cursor.execute(
                    "INSERT INTO lotti "
                    "(tenant_id, articolo_id, tipo_lotto, progressivo, codice_lotto, "
                    "data_creazione, quantita_iniziale, quantita_disponibile, "
                    "unita_misura, documento_ingresso_id) "
                    "VALUES (%s, %s, 'A', %s, %s, %s, %s, %s, %s, %s)",
                    (
                        tenant_id,
                        riga.articolo_id,
                        numero,
                        codice,
                        data,
                        riga.quantita,
                        riga.quantita,
                        articoli[riga.articolo_id],
                        documento_id,
                    ),
                )
                lotto_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO righe_ingresso_tracciato "
                    "(tenant_id, documento_ingresso_id, lotto_id, quantita) "
                    "VALUES (%s, %s, %s, %s)",
                    (tenant_id, documento_id, lotto_id, riga.quantita),
                )
                cursor.execute(
                    "INSERT INTO movimenti_lotto "
                    "(tenant_id, lotto_id, tipo, quantita_delta, documento_ingresso_id) "
                    "VALUES (%s, %s, 'INGRESSO', %s, %s)",
                    (tenant_id, lotto_id, riga.quantita, documento_id),
                )
                lotti_creati.append(
                    {
                        "id": lotto_id,
                        "articolo_id": riga.articolo_id,
                        "tipo_lotto": "A",
                        "progressivo": numero,
                        "codice_lotto": codice,
                        "quantita": str(riga.quantita),
                        "unita_misura": articoli[riga.articolo_id],
                        "documento_ingresso_id": documento_id,
                    }
                )
            conn.commit()
            return {"documento_ingresso_id": documento_id, "lotti": lotti_creati}
        except Exception:
            conn.rollback()
            raise


def registra_lavorazione(
    tenant_id, data, descrizione, operatore_id, input_lavorazione, output, scarti
):
    """Consuma i lotti di input e crea un lotto V per ogni prodotto ottenuto."""
    quantita_input = defaultdict(Decimal)
    for riga in input_lavorazione:
        quantita_input[riga.lotto_id] += riga.quantita

    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT nome, cognome FROM dipendenti "
                "WHERE ID = %s AND tenant_id = %s",
                (operatore_id, tenant_id),
            )
            dipendente = cursor.fetchone()
            if dipendente is None:
                raise DipendenteNonTrovato
            operatore = " ".join(
                parte for parte in dipendente if parte
            )

            lotto_ids = sorted(quantita_input)
            placeholders = ", ".join(["%s"] * len(lotto_ids))
            cursor.execute(
                "SELECT id, quantita_disponibile FROM lotti "
                f"WHERE tenant_id = %s AND id IN ({placeholders}) "
                "ORDER BY id FOR UPDATE",
                (tenant_id, *lotto_ids),
            )
            lotti = {row[0]: Decimal(str(row[1])) for row in cursor.fetchall()}
            if len(lotti) != len(lotto_ids):
                raise LottoNonTrovato
            for lotto_id, quantita in quantita_input.items():
                if lotti[lotto_id] < quantita:
                    raise GiacenzaInsufficiente(
                        f"Giacenza insufficiente per il lotto {lotto_id}."
                    )

            articolo_ids = sorted({riga.articolo_id for riga in output})
            placeholders = ", ".join(["%s"] * len(articolo_ids))
            cursor.execute(
                "SELECT id, unita_misura FROM articoli "
                f"WHERE tenant_id = %s AND attivo = 1 AND id IN ({placeholders})",
                (tenant_id, *articolo_ids),
            )
            articoli = {row[0]: row[1] for row in cursor.fetchall()}
            if len(articoli) != len(articolo_ids):
                raise ArticoloNonTrovato

            cursor.execute(
                "INSERT INTO lavorazioni "
                "(tenant_id, data_lavorazione, descrizione, operatore_id, operatore) "
                "VALUES (%s, %s, %s, %s, %s)",
                (tenant_id, data, descrizione, operatore_id, operatore),
            )
            lavorazione_id = cursor.lastrowid

            for lotto_id, quantita in quantita_input.items():
                cursor.execute(
                    "UPDATE lotti SET quantita_disponibile = quantita_disponibile - %s "
                    "WHERE tenant_id = %s AND id = %s",
                    (quantita, tenant_id, lotto_id),
                )
                cursor.execute(
                    "INSERT INTO lavorazione_input "
                    "(tenant_id, lavorazione_id, lotto_id, quantita) "
                    "VALUES (%s, %s, %s, %s)",
                    (tenant_id, lavorazione_id, lotto_id, quantita),
                )
                cursor.execute(
                    "INSERT INTO movimenti_lotto "
                    "(tenant_id, lotto_id, tipo, quantita_delta, lavorazione_id) "
                    "VALUES (%s, %s, 'CONSUMO', %s, %s)",
                    (tenant_id, lotto_id, -quantita, lavorazione_id),
                )

            lotti_creati = []
            for riga in output:
                numero = _prossimo_progressivo(cursor, tenant_id, "V")
                codice = f"{numero}V"
                cursor.execute(
                    "INSERT INTO lotti "
                    "(tenant_id, articolo_id, tipo_lotto, progressivo, codice_lotto, "
                    "data_creazione, quantita_iniziale, quantita_disponibile, "
                    "unita_misura, lavorazione_id) "
                    "VALUES (%s, %s, 'V', %s, %s, %s, %s, %s, %s, %s)",
                    (
                        tenant_id,
                        riga.articolo_id,
                        numero,
                        codice,
                        data,
                        riga.quantita,
                        riga.quantita,
                        articoli[riga.articolo_id],
                        lavorazione_id,
                    ),
                )
                lotto_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO lavorazione_output "
                    "(tenant_id, lavorazione_id, articolo_id, lotto_id, quantita) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        tenant_id,
                        lavorazione_id,
                        riga.articolo_id,
                        lotto_id,
                        riga.quantita,
                    ),
                )
                cursor.execute(
                    "INSERT INTO movimenti_lotto "
                    "(tenant_id, lotto_id, tipo, quantita_delta, lavorazione_id) "
                    "VALUES (%s, %s, 'PRODUZIONE', %s, %s)",
                    (tenant_id, lotto_id, riga.quantita, lavorazione_id),
                )
                lotti_creati.append(
                    {
                        "id": lotto_id,
                        "articolo_id": riga.articolo_id,
                        "tipo_lotto": "V",
                        "progressivo": numero,
                        "codice_lotto": codice,
                        "quantita": str(riga.quantita),
                        "unita_misura": articoli[riga.articolo_id],
                        "lavorazione_id": lavorazione_id,
                    }
                )
            for scarto in scarti:
                cursor.execute(
                    "INSERT INTO lavorazione_scarto "
                    "(tenant_id, lavorazione_id, descrizione, quantita, unita_misura) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        tenant_id,
                        lavorazione_id,
                        scarto.descrizione,
                        scarto.quantita,
                        scarto.unita_misura,
                    ),
                )
            conn.commit()
            return {"lavorazione_id": lavorazione_id, "lotti": lotti_creati}
        except Exception:
            conn.rollback()
            raise
