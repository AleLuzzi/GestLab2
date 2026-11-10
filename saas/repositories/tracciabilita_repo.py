"""Repository SaaS per articoli, lotti d'ingresso e lavorazioni."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from core.db import connection
from core.repositories import soggetti as soggetti_repo
from core.repositories.soggetti import FornitoreNonValido


def _row_value(row, index, default=None):
    """Legge un valore da una tupla anche quando la query mockata è più corta."""
    return row[index] if index < len(row) else default


class ArticoloNonTrovato(Exception):
    """Articolo inesistente o non appartenente al tenant."""


class LottoNonTrovato(Exception):
    """Lotto inesistente o non appartenente al tenant."""


class DipendenteNonTrovato(Exception):
    """Dipendente inesistente o non appartenente al tenant."""


class GiacenzaInsufficiente(Exception):
    """La quantità richiesta supera la giacenza disponibile."""


class ArticoloNonUtilizzabileComeInput(Exception):
    """L'articolo del lotto non è abilitato come input di lavorazione."""


class RicettaNonTrovata(Exception):
    """Ricetta assente, inattiva o non associata all'articolo prodotto."""


class TenantVenditaNonTrovato(Exception):
    """Tenant inesistente durante la creazione di un documento di vendita."""


class ClienteVenditaNonValido(Exception):
    """Cliente assente, inattivo o non associato al tenant."""


class LottoScaduto(Exception):
    """Un lotto con data di scadenza superata non può essere lavorato."""


class ConfermaTmcScadutoRichiesta(Exception):
    """Il TMC superato richiede una conferma esplicita dell'operatore."""


def _data_valore(value):
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value[:10])
    return None


def lista_articoli(tenant_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, codice, nome, categoria, unita_misura, ean, "
            "prezzo_unitario, attivo, "
            "utilizzabile_come_input "
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
                "ean": row[5],
                "prezzo_unitario": str(row[6]) if row[6] is not None else None,
                "attivo": bool(row[7]),
                "utilizzabile_come_input": bool(row[8]),
            }
            for row in cursor.fetchall()
        ]


def crea_articolo(
    tenant_id,
    codice,
    nome,
    categoria,
    unita_misura,
    utilizzabile_come_input=True,
    ean=None,
    prezzo_unitario=None,
):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO articoli "
            "(tenant_id, codice, nome, categoria, unita_misura, ean, "
            "prezzo_unitario, utilizzabile_come_input) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                tenant_id,
                codice,
                nome,
                categoria,
                unita_misura,
                ean,
                prezzo_unitario,
                int(utilizzabile_come_input),
            ),
        )
        articolo_id = cursor.lastrowid
        conn.commit()
    return {
        "id": articolo_id,
        "codice": codice,
        "nome": nome,
        "categoria": categoria,
        "unita_misura": unita_misura,
        "ean": ean,
        "prezzo_unitario": str(prezzo_unitario) if prezzo_unitario is not None else None,
        "attivo": True,
        "utilizzabile_come_input": utilizzabile_come_input,
    }


def aggiorna_articolo(
    tenant_id,
    articolo_id,
    codice,
    nome,
    categoria,
    unita_misura,
    attivo,
    utilizzabile_come_input=None,
    ean=None,
    prezzo_unitario=None,
    ean_impostato=True,
    prezzo_impostato=True,
):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE articoli SET codice = %s, nome = %s, categoria = %s, "
            "unita_misura = %s, "
            "ean = CASE WHEN %s THEN %s ELSE ean END, "
            "prezzo_unitario = CASE WHEN %s THEN %s ELSE prezzo_unitario END, "
            "attivo = %s, "
            "utilizzabile_come_input = COALESCE(%s, utilizzabile_come_input) "
            "WHERE tenant_id = %s AND id = %s",
            (
                codice,
                nome,
                categoria,
                unita_misura,
                int(ean_impostato),
                ean,
                int(prezzo_impostato),
                prezzo_unitario,
                int(attivo),
                None if utilizzabile_come_input is None else int(utilizzabile_come_input),
                tenant_id,
                articolo_id,
            ),
        )
        cursor.execute(
            "SELECT id, codice, nome, categoria, unita_misura, ean, "
            "prezzo_unitario, attivo, "
            "utilizzabile_come_input "
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
        "ean": row[5],
        "prezzo_unitario": str(row[6]) if row[6] is not None else None,
        "attivo": bool(row[7]),
        "utilizzabile_come_input": bool(row[8]),
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


def _ricetta_da_riga(row):
    return {
        "id": row[0],
        "nome": row[1],
        "articolo_id": row[2],
        "articolo_nome": row[3],
        "unita_misura": row[4],
        "resa_attesa": str(row[5]),
        "scarto_atteso": str(row[6]),
        "attiva": bool(row[7]),
        "ingredienti": [],
        "allergeni": [],
        "giorni_vita": row[8] if len(row) > 8 else None,
        "istruzioni_conservazione": row[9] if len(row) > 9 else None,
        "istruzioni_cottura": row[10] if len(row) > 10 else None,
    }


def _ingredienti_da_righe(rows):
    return [
        {
            "articolo_id": row[1],
            "articolo_nome": row[2],
            "unita_misura": row[3],
            "tipo_quantita": row[4],
            "valore": str(row[5]),
            "obbligatorio": bool(row[6]),
        }
        for row in rows
    ]


def _carica_ingredienti_ricetta(cursor, tenant_id, ricetta_id):
    cursor.execute(
        "SELECT ri.ricetta_id, ri.articolo_id, a.nome, a.unita_misura, "
        "ri.tipo_quantita, ri.valore, ri.obbligatorio "
        "FROM ricetta_ingredienti ri JOIN articoli a "
        "ON a.tenant_id = ri.tenant_id AND a.id = ri.articolo_id "
        "WHERE ri.tenant_id = %s AND ri.ricetta_id = %s "
        "ORDER BY ri.posizione",
        (tenant_id, ricetta_id),
    )
    return _ingredienti_da_righe(cursor.fetchall())


def _carica_allergeni_ricetta(cursor, tenant_id, ricetta_id):
    cursor.execute(
        "SELECT codice FROM ricetta_allergeni "
        "WHERE tenant_id = %s AND ricetta_id = %s ORDER BY codice",
        (tenant_id, ricetta_id),
    )
    return sorted(row[0] for row in cursor.fetchall())


def _salva_allergeni_ricetta(cursor, tenant_id, ricetta_id, allergeni):
    cursor.execute(
        "DELETE FROM ricetta_allergeni WHERE tenant_id = %s AND ricetta_id = %s",
        (tenant_id, ricetta_id),
    )
    for allergene in sorted(allergeni or []):
        cursor.execute(
            "INSERT INTO ricetta_allergeni (tenant_id, ricetta_id, codice) "
            "VALUES (%s, %s, %s)",
            (tenant_id, ricetta_id, allergene),
        )


def _salva_ingredienti_ricetta(cursor, tenant_id, ricetta_id, ingredienti):
    ingredienti = list(ingredienti or [])
    articolo_ids = [
        ingrediente["articolo_id"]
        if isinstance(ingrediente, dict)
        else ingrediente.articolo_id
        for ingrediente in ingredienti
    ]
    if len(articolo_ids) != len(set(articolo_ids)):
        raise ValueError("Ogni articolo puo' comparire una sola volta nella ricetta")

    if articolo_ids:
        placeholders = ", ".join(["%s"] * len(articolo_ids))
        cursor.execute(
            "SELECT id FROM articoli WHERE tenant_id = %s AND attivo = 1 "
            "AND utilizzabile_come_input = 1 "
            f"AND id IN ({placeholders}) FOR UPDATE",
            (tenant_id, *articolo_ids),
        )
        articoli_validi = {row[0] for row in cursor.fetchall()}
        if articoli_validi != set(articolo_ids):
            return False

    cursor.execute(
        "DELETE FROM ricetta_ingredienti WHERE tenant_id = %s AND ricetta_id = %s",
        (tenant_id, ricetta_id),
    )
    for posizione, ingrediente in enumerate(ingredienti, start=1):
        valore = ingrediente if isinstance(ingrediente, dict) else ingrediente.model_dump()
        cursor.execute(
            "INSERT INTO ricetta_ingredienti "
            "(tenant_id, ricetta_id, articolo_id, posizione, tipo_quantita, "
            "valore, obbligatorio) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                tenant_id,
                ricetta_id,
                valore["articolo_id"],
                posizione,
                valore["tipo_quantita"],
                valore["valore"],
                int(valore["obbligatorio"]),
            ),
        )
    return True


def lista_ricette(tenant_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT r.id, r.nome, r.articolo_id, a.nome, a.unita_misura, "
            "r.resa_attesa, r.scarto_atteso, r.attiva, r.giorni_vita, "
            "r.istruzioni_conservazione, r.istruzioni_cottura "
            "FROM ricette r JOIN articoli a "
            "ON a.tenant_id = r.tenant_id AND a.id = r.articolo_id "
            "WHERE r.tenant_id = %s ORDER BY r.nome, r.id",
            (tenant_id,),
        )
        ricette = [_ricetta_da_riga(row) for row in cursor.fetchall()]
        if not ricette:
            return ricette

        cursor.execute(
            "SELECT ri.ricetta_id, ri.articolo_id, a.nome, a.unita_misura, "
            "ri.tipo_quantita, ri.valore, ri.obbligatorio "
            "FROM ricetta_ingredienti ri JOIN articoli a "
            "ON a.tenant_id = ri.tenant_id AND a.id = ri.articolo_id "
            "JOIN ricette r "
            "ON r.tenant_id = ri.tenant_id AND r.id = ri.ricetta_id "
            "WHERE ri.tenant_id = %s "
            "ORDER BY ri.ricetta_id, ri.posizione",
            (tenant_id,),
        )
        ingredienti_per_ricetta = {}
        for row in cursor.fetchall():
            ingredienti_per_ricetta.setdefault(row[0], []).append(row)
        cursor.execute(
            "SELECT ricetta_id, codice FROM ricetta_allergeni "
            "WHERE tenant_id = %s ORDER BY ricetta_id, codice",
            (tenant_id,),
        )
        allergeni_per_ricetta = {}
        for ricetta_id, codice in cursor.fetchall():
            allergeni_per_ricetta.setdefault(ricetta_id, []).append(codice)
        for ricetta in ricette:
            ricetta["ingredienti"] = _ingredienti_da_righe(
                ingredienti_per_ricetta.get(ricetta["id"], [])
            )
            ricetta["allergeni"] = allergeni_per_ricetta.get(ricetta["id"], [])
        return ricette


def crea_ricetta(
    tenant_id,
    nome,
    articolo_id,
    resa_attesa,
    scarto_atteso,
    ingredienti=None,
    allergeni=None,
    giorni_vita=None,
    istruzioni_conservazione=None,
    istruzioni_cottura=None,
):
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM articoli "
                "WHERE tenant_id = %s AND id = %s AND attivo = 1 FOR UPDATE",
                (tenant_id, articolo_id),
            )
            if cursor.fetchone() is None:
                conn.rollback()
                return None

            cursor.execute(
                "INSERT INTO ricette "
                "(tenant_id, nome, articolo_id, resa_attesa, scarto_atteso, "
                "giorni_vita, istruzioni_conservazione, istruzioni_cottura) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    tenant_id,
                    nome.strip(),
                    articolo_id,
                    resa_attesa,
                    scarto_atteso,
                    giorni_vita,
                    istruzioni_conservazione,
                    istruzioni_cottura,
                ),
            )
            ricetta_id = cursor.lastrowid
            if not _salva_ingredienti_ricetta(
                cursor, tenant_id, ricetta_id, ingredienti
            ):
                conn.rollback()
                return None
            _salva_allergeni_ricetta(cursor, tenant_id, ricetta_id, allergeni)
            cursor.execute(
                "SELECT r.id, r.nome, r.articolo_id, a.nome, a.unita_misura, "
                "r.resa_attesa, r.scarto_atteso, r.attiva, r.giorni_vita, "
                "r.istruzioni_conservazione, r.istruzioni_cottura "
                "FROM ricette r JOIN articoli a "
                "ON a.tenant_id = r.tenant_id AND a.id = r.articolo_id "
                "WHERE r.tenant_id = %s AND r.id = %s",
                (tenant_id, ricetta_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Ricetta creata ma non rileggibile")
            ricetta = _ricetta_da_riga(row)
            ricetta["ingredienti"] = _carica_ingredienti_ricetta(
                cursor, tenant_id, ricetta_id
            )
            ricetta["allergeni"] = _carica_allergeni_ricetta(
                cursor, tenant_id, ricetta_id
            )
            conn.commit()
            return ricetta
        except Exception:
            conn.rollback()
            raise


def aggiorna_ricetta(
    tenant_id,
    ricetta_id,
    nome,
    articolo_id,
    resa_attesa,
    scarto_atteso,
    attiva,
    ingredienti=None,
    allergeni=None,
    giorni_vita=None,
    istruzioni_conservazione=None,
    istruzioni_cottura=None,
):
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM articoli "
                "WHERE tenant_id = %s AND id = %s AND attivo = 1 FOR UPDATE",
                (tenant_id, articolo_id),
            )
            if cursor.fetchone() is None:
                conn.rollback()
                return None

            cursor.execute(
                "SELECT id FROM ricette WHERE tenant_id = %s AND id = %s FOR UPDATE",
                (tenant_id, ricetta_id),
            )
            if cursor.fetchone() is None:
                conn.rollback()
                return None

            cursor.execute(
                "UPDATE ricette SET nome = %s, articolo_id = %s, resa_attesa = %s, "
                "scarto_atteso = %s, attiva = %s, giorni_vita = %s, "
                "istruzioni_conservazione = %s, istruzioni_cottura = %s "
                "WHERE tenant_id = %s AND id = %s",
                (
                    nome.strip(),
                    articolo_id,
                    resa_attesa,
                    scarto_atteso,
                    int(attiva),
                    giorni_vita,
                    istruzioni_conservazione,
                    istruzioni_cottura,
                    tenant_id,
                    ricetta_id,
                ),
            )
            if not _salva_ingredienti_ricetta(
                cursor, tenant_id, ricetta_id, ingredienti
            ):
                conn.rollback()
                return None
            _salva_allergeni_ricetta(cursor, tenant_id, ricetta_id, allergeni)
            cursor.execute(
                "SELECT r.id, r.nome, r.articolo_id, a.nome, a.unita_misura, "
                "r.resa_attesa, r.scarto_atteso, r.attiva, r.giorni_vita, "
                "r.istruzioni_conservazione, r.istruzioni_cottura "
                "FROM ricette r JOIN articoli a "
                "ON a.tenant_id = r.tenant_id AND a.id = r.articolo_id "
                "WHERE r.tenant_id = %s AND r.id = %s",
                (tenant_id, ricetta_id),
            )
            row = cursor.fetchone()
            if row is None:
                conn.rollback()
                return None
            ricetta = _ricetta_da_riga(row)
            ricetta["ingredienti"] = _carica_ingredienti_ricetta(
                cursor, tenant_id, ricetta_id
            )
            ricetta["allergeni"] = _carica_allergeni_ricetta(
                cursor, tenant_id, ricetta_id
            )
            conn.commit()
            return ricetta
        except Exception:
            conn.rollback()
            raise


def disattiva_ricetta(tenant_id, ricetta_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ricette SET attiva = 0 WHERE tenant_id = %s AND id = %s",
            (tenant_id, ricetta_id),
        )
        cursor.execute(
            "SELECT id FROM ricette WHERE tenant_id = %s AND id = %s",
            (tenant_id, ricetta_id),
        )
        esistente = cursor.fetchone() is not None
        if esistente:
            conn.commit()
        else:
            conn.rollback()
        return esistente


def lista_lotti(tenant_id, solo_disponibili=False, data_dal=None, data_al=None):
    query = (
        "SELECT l.id, l.articolo_id, a.nome, l.tipo_lotto, l.progressivo, "
        "l.codice_lotto, l.data_creazione, l.data_scadenza, l.lotto_fornitore, "
        "l.origine, l.temperatura_ingresso, l.quantita_iniziale, "
        "l.quantita_disponibile, l.unita_misura, l.documento_ingresso_id, "
        "l.lavorazione_id, a.categoria, l.note_lotto, l.data_tmc "
        "FROM lotti l JOIN articoli a "
        "ON a.tenant_id = l.tenant_id AND a.id = l.articolo_id "
        "WHERE l.tenant_id = %s"
    )
    params = [tenant_id]
    if data_dal is not None:
        query += " AND l.data_creazione >= %s"
        params.append(data_dal)
    if data_al is not None:
        query += " AND l.data_creazione <= %s"
        params.append(data_al)
    if solo_disponibili:
        query += " AND l.quantita_disponibile > 0"
    query += " ORDER BY l.data_creazione DESC, l.id DESC"

    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = []
        for row in cursor.fetchall():
            row_len = len(row)
            if row_len >= 18:
                quantita_iniziale = _row_value(row, 11)
                quantita_disponibile = _row_value(row, 12)
                unita_misura = _row_value(row, 13)
                documento_ingresso_id = _row_value(row, 14)
                lavorazione_id = _row_value(row, 15)
                categoria = _row_value(row, 16)
                data_scadenza = _row_value(row, 7)
                lotto_fornitore = _row_value(row, 8)
                origine = _row_value(row, 9)
                temperatura = _row_value(row, 10)
                note_lotto = _row_value(row, 17)
                data_tmc = _row_value(row, 18)
            elif row_len >= 17:
                quantita_iniziale = _row_value(row, 11)
                quantita_disponibile = _row_value(row, 12)
                unita_misura = _row_value(row, 13)
                documento_ingresso_id = _row_value(row, 14)
                lavorazione_id = _row_value(row, 15)
                categoria = _row_value(row, 16)
                data_scadenza = _row_value(row, 7)
                lotto_fornitore = _row_value(row, 8)
                origine = _row_value(row, 9)
                temperatura = _row_value(row, 10)
                note_lotto = None
                data_tmc = None
            else:
                quantita_iniziale = _row_value(row, 7)
                quantita_disponibile = _row_value(row, 8)
                unita_misura = _row_value(row, 9)
                documento_ingresso_id = _row_value(row, 10)
                lavorazione_id = _row_value(row, 11)
                categoria = _row_value(row, 12)
                data_scadenza = None
                lotto_fornitore = None
                origine = None
                temperatura = None
                note_lotto = None
                data_tmc = None

            rows.append(
                {
                    "id": _row_value(row, 0),
                    "articolo_id": _row_value(row, 1),
                    "articolo": _row_value(row, 2),
                    "tipo_lotto": _row_value(row, 3),
                    "progressivo": _row_value(row, 4),
                    "codice_lotto": _row_value(row, 5),
                    "data_creazione": _row_value(row, 6),
                    "quantita_iniziale": str(quantita_iniziale) if quantita_iniziale is not None else None,
                    "quantita_disponibile": str(quantita_disponibile) if quantita_disponibile is not None else None,
                    "unita_misura": unita_misura,
                    "documento_ingresso_id": documento_ingresso_id,
                    "lavorazione_id": lavorazione_id,
                    "categoria": categoria,
                    "data_scadenza": data_scadenza,
                    "data_tmc": data_tmc,
                    "lotto_fornitore": lotto_fornitore,
                    "origine": origine,
                    "temperatura_ingresso": str(temperatura) if temperatura is not None else None,
                    "note_lotto": note_lotto,
                }
            )
        return rows


def riepilogo_inventario(tenant_id):
    """Somma la giacenza teorica di tutti i lotti per articolo del tenant."""
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT a.id, a.codice, a.nome, a.unita_misura, "
            "COALESCE(SUM(l.quantita_disponibile), 0) "
            "FROM articoli a LEFT JOIN lotti l "
            "ON l.tenant_id = a.tenant_id AND l.articolo_id = a.id "
            "WHERE a.tenant_id = %s "
            "GROUP BY a.id, a.codice, a.nome, a.unita_misura "
            "ORDER BY a.nome, a.id",
            (tenant_id,),
        )
        return [
            {
                "articolo_id": row[0],
                "codice": row[1],
                "articolo": row[2],
                "unita_misura": row[3],
                "quantita_teorica": str(row[4]),
            }
            for row in cursor.fetchall()
        ]


def lotti_disponibili_vendita(tenant_id):
    """Restituisce i lotti vendibili ordinati per FEFO."""
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT l.id, l.articolo_id, a.nome, l.tipo_lotto, "
            "l.codice_lotto, l.data_scadenza, l.quantita_disponibile, "
            "l.unita_misura, l.data_tmc "
            "FROM lotti l JOIN articoli a "
            "ON a.tenant_id = l.tenant_id AND a.id = l.articolo_id "
            "WHERE l.tenant_id = %s AND a.attivo = 1 AND l.attivo = 1 "
            "AND l.quantita_disponibile > 0 "
            "AND (l.data_scadenza IS NULL OR l.data_scadenza >= CURRENT_DATE) "
            "ORDER BY CASE WHEN COALESCE(l.data_scadenza, l.data_tmc) IS NULL "
            "THEN 1 ELSE 0 END, COALESCE(l.data_scadenza, l.data_tmc) ASC, "
            "l.data_creazione ASC, l.id ASC",
            (tenant_id,),
        )
        return [
            {
                "id": row[0],
                "articolo_id": row[1],
                "articolo": row[2],
                "tipo_lotto": row[3],
                "codice_lotto": row[4],
                "data_scadenza": row[5],
                "quantita_disponibile": str(row[6]),
                "unita_misura": row[7],
                "data_tmc": _row_value(row, 8),
            }
            for row in cursor.fetchall()
        ]


def crea_vendita(tenant_id, data_vendita, cliente_id, tipo_documento):
    """Crea una testata con progressivo serializzato per tenant."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM tenant WHERE id = %s FOR UPDATE",
                (tenant_id,),
            )
            if cursor.fetchone() is None:
                raise TenantVenditaNonTrovato()

            if cliente_id is not None:
                cursor.execute(
                    "SELECT s.id FROM soggetti s "
                    "JOIN soggetti_ruoli r ON r.tenant_id = s.tenant_id "
                    "AND r.soggetto_id = s.id AND r.ruolo = 'cliente' "
                    "WHERE s.tenant_id = %s AND s.id = %s AND s.attivo = 1 "
                    "FOR UPDATE",
                    (tenant_id, cliente_id),
                )
                if cursor.fetchone() is None:
                    raise ClienteVenditaNonValido()

            cursor.execute(
                "SELECT COALESCE(MAX(numero), 0) FROM vendite WHERE tenant_id = %s",
                (tenant_id,),
            )
            numero = int(cursor.fetchone()[0]) + 1
            cursor.execute(
                "INSERT INTO vendite "
                "(tenant_id, numero, data_vendita, cliente_id, tipo_documento) "
                "VALUES (%s, %s, %s, %s, %s)",
                (tenant_id, numero, data_vendita, cliente_id, tipo_documento),
            )
            vendita_id = cursor.lastrowid
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "id": vendita_id,
        "tenant_id": tenant_id,
        "numero": numero,
        "data_vendita": data_vendita,
        "cliente_id": cliente_id,
        "tipo_documento": tipo_documento,
    }


def dettaglio_lotto(tenant_id, lotto_id):
    """Restituisce lotto, origine e input/output della sua lavorazione."""
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT l.id, l.articolo_id, a.nome, l.tipo_lotto, l.progressivo, "
            "l.codice_lotto, l.data_creazione, l.data_scadenza, l.lotto_fornitore, "
            "l.origine, l.temperatura_ingresso, l.quantita_iniziale, "
            "l.quantita_disponibile, l.unita_misura, l.documento_ingresso_id, "
            "l.lavorazione_id, d.data_ingresso, d.numero_ddt, d.fornitore, "
            "d.fornitore_id, "
            "w.data_lavorazione, w.descrizione, "
            "COALESCE(NULLIF(TRIM(CONCAT_WS(' ', dp.nome, dp.cognome)), ''), w.operatore), "
            "l.note_lotto, l.data_tmc, a.prezzo_unitario, w.ricetta_id "
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
            "data_scadenza": row[7],
            "data_tmc": _row_value(row, 24),
            "prezzo_unitario": _row_value(row, 25),
            "lotto_fornitore": row[8],
            "origine": row[9],
            "temperatura_ingresso": str(row[10]) if row[10] is not None else None,
            "quantita_iniziale": str(row[11]),
            "quantita_disponibile": str(row[12]),
            "unita_misura": row[13],
            "documento_ingresso_id": row[14],
            "lavorazione_id": row[15],
            "note_lotto": _row_value(row, 23),
            "documento_ingresso": None,
            "lavorazione": None,
            "dati_etichetta": {"ingredienti": "", "allergeni": []},
        }
        if row[14] is not None:
            risultato["documento_ingresso"] = {
                "id": row[14],
                "data": row[16],
                "numero_ddt": row[17],
                "fornitore": row[18],
                "fornitore_id": row[19],
            }
        cursor.execute(
            "SELECT tipo, quantita_delta, creato_il, motivo FROM movimenti_lotto "
            "WHERE tenant_id = %s AND lotto_id = %s ORDER BY id",
            (tenant_id, lotto_id),
        )
        risultato["movimenti"] = [
            {
                "tipo": item[0],
                "quantita_delta": str(item[1]),
                "creato_il": item[2],
                "motivo": _row_value(item, 3),
            }
            for item in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT w.id, w.data_lavorazione, w.descrizione, "
            "COALESCE(NULLIF(TRIM(CONCAT_WS(' ', dp.nome, dp.cognome)), ''), w.operatore), "
            "lo.lotto_id, lp.codice_lotto, a.nome, lo.quantita, lp.unita_misura "
            "FROM lavorazione_input li "
            "JOIN lavorazioni w "
            "ON w.tenant_id = li.tenant_id AND w.id = li.lavorazione_id "
            "LEFT JOIN dipendenti dp "
            "ON dp.tenant_id = w.tenant_id AND dp.ID = w.operatore_id "
            "LEFT JOIN lavorazione_output lo "
            "ON lo.tenant_id = w.tenant_id AND lo.lavorazione_id = w.id "
            "LEFT JOIN lotti lp "
            "ON lp.tenant_id = lo.tenant_id AND lp.id = lo.lotto_id "
            "LEFT JOIN articoli a "
            "ON a.tenant_id = lo.tenant_id AND a.id = lo.articolo_id "
            "WHERE li.tenant_id = %s AND li.lotto_id = %s "
            "ORDER BY w.data_lavorazione, w.id, lo.id",
            (tenant_id, lotto_id),
        )
        lavorazioni_successive = {}
        for item in cursor.fetchall():
            lavorazione = lavorazioni_successive.setdefault(
                item[0],
                {
                    "id": item[0],
                    "data": item[1],
                    "descrizione": item[2],
                    "operatore": item[3],
                    "output": [],
                },
            )
            if item[4] is not None:
                lavorazione["output"].append(
                    {
                        "lotto_id": item[4],
                        "codice_lotto": item[5],
                        "articolo": item[6],
                        "quantita": str(item[7]),
                        "unita_misura": item[8],
                    }
                )
        risultato["lavorazioni_successive"] = list(lavorazioni_successive.values())
        if row[15] is not None:
            ricetta_id = _row_value(row, 26)
            if ricetta_id is not None:
                cursor.execute(
                    "SELECT nome, istruzioni_conservazione FROM ricette "
                    "WHERE tenant_id = %s AND id = %s",
                    (tenant_id, ricetta_id),
                )
                ricetta = cursor.fetchone()
                if ricetta is not None:
                    cursor.execute(
                        "SELECT a.nome FROM ricetta_ingredienti ri "
                        "JOIN articoli a "
                        "ON a.tenant_id = ri.tenant_id AND a.id = ri.articolo_id "
                        "WHERE ri.tenant_id = %s AND ri.ricetta_id = %s "
                        "ORDER BY ri.posizione",
                        (tenant_id, ricetta_id),
                    )
                    ingredienti = ", ".join(item[0] for item in cursor.fetchall())
                    cursor.execute(
                        "SELECT codice FROM ricetta_allergeni "
                        "WHERE tenant_id = %s AND ricetta_id = %s ORDER BY codice",
                        (tenant_id, ricetta_id),
                    )
                    risultato["dati_etichetta"] = {
                        "ricetta_id": ricetta_id,
                        "ricetta_nome": ricetta[0],
                        "ingredienti": ingredienti,
                        "allergeni": [item[0] for item in cursor.fetchall()],
                        "conservazione": ricetta[1] or "",
                    }
            cursor.execute(
                "SELECT li.lotto_id, lp.codice_lotto, ap.nome, li.quantita "
                "FROM lavorazione_input li "
                "JOIN lotti lp ON lp.tenant_id = li.tenant_id AND lp.id = li.lotto_id "
                "JOIN articoli ap ON ap.tenant_id = lp.tenant_id AND ap.id = lp.articolo_id "
                "WHERE li.tenant_id = %s AND li.lavorazione_id = %s "
                "ORDER BY li.id",
                (tenant_id, row[15]),
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
                (tenant_id, row[15]),
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
                (tenant_id, row[15]),
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
                "id": row[15],
                "data": row[20],
                "descrizione": row[21],
                "operatore": row[22],
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


def rettifica_lotto(tenant_id, lotto_id, delta, motivo):
    """Applica una rettifica tracciata e aggiorna la giacenza atomicamente."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT quantita_disponibile FROM lotti "
                "WHERE tenant_id = %s AND id = %s FOR UPDATE",
                (tenant_id, lotto_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise LottoNonTrovato

            nuova_giacenza = Decimal(str(row[0])) + Decimal(str(delta))
            if nuova_giacenza < 0:
                raise GiacenzaInsufficiente(
                    "La rettifica non può portare la giacenza sotto zero."
                )

            cursor.execute(
                "UPDATE lotti SET quantita_disponibile = %s "
                "WHERE tenant_id = %s AND id = %s",
                (nuova_giacenza, tenant_id, lotto_id),
            )
            cursor.execute(
                "INSERT INTO movimenti_lotto "
                "(tenant_id, lotto_id, tipo, quantita_delta, motivo) "
                "VALUES (%s, %s, 'RETTIFICA', %s, %s)",
                (tenant_id, lotto_id, delta, motivo),
            )
            conn.commit()
            return {
                "lotto_id": lotto_id,
                "quantita_disponibile": str(nuova_giacenza),
                "delta": str(delta),
                "motivo": motivo,
            }
        except Exception:
            conn.rollback()
            raise


def registra_ingresso(tenant_id, data, numero_ddt, fornitore_id, righe):
    """Registra un documento e crea un lotto A distinto per ogni sua riga."""
    with connection() as conn:
        cursor = conn.cursor()
        try:
            fornitore = soggetti_repo.fornitore_abilitato(
                cursor, tenant_id, fornitore_id
            )
            if not fornitore:
                raise FornitoreNonValido

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
                "(tenant_id, data_ingresso, numero_ddt, fornitore, fornitore_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    tenant_id,
                    data,
                    numero_ddt,
                    fornitore["denominazione"],
                    fornitore_id,
                ),
            )
            documento_id = cursor.lastrowid
            lotti_creati = []

            for riga in righe:
                numero = _prossimo_progressivo(cursor, tenant_id, "A")
                codice = f"{numero}A"
                data_scadenza = getattr(riga, "data_scadenza", None)
                data_tmc = getattr(riga, "data_tmc", None)
                lotto_fornitore = getattr(riga, "lotto_fornitore", None)
                origine = getattr(riga, "origine", None)
                temperatura_ingresso = getattr(riga, "temperatura_ingresso", None)
                note_lotto = getattr(riga, "note_lotto", None)
                cursor.execute(
                    "INSERT INTO lotti "
                    "(tenant_id, articolo_id, tipo_lotto, progressivo, codice_lotto, "
                    "data_creazione, data_scadenza, data_tmc, lotto_fornitore, origine, "
                    "temperatura_ingresso, note_lotto, quantita_iniziale, quantita_disponibile, "
                    "unita_misura, documento_ingresso_id) "
                    "VALUES (%s, %s, 'A', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        tenant_id,
                        riga.articolo_id,
                        numero,
                        codice,
                        data,
                        data_scadenza,
                        data_tmc,
                        lotto_fornitore,
                        origine,
                        temperatura_ingresso,
                        note_lotto,
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
    tenant_id,
    data,
    descrizione,
    operatore_id,
    input_lavorazione,
    output,
    scarti,
    ricetta_id=None,
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
            input_senza_conferma_tmc = {
                riga.lotto_id
                for riga in input_lavorazione
                if not getattr(riga, "conferma_tmc_scaduto", False)
            }
            placeholders = ", ".join(["%s"] * len(lotto_ids))
            cursor.execute(
                "SELECT l.id, l.quantita_disponibile, a.utilizzabile_come_input, "
                "l.data_scadenza, l.data_tmc, CURRENT_DATE "
                "FROM lotti l JOIN articoli a "
                "ON a.tenant_id = l.tenant_id AND a.id = l.articolo_id "
                f"WHERE l.tenant_id = %s AND l.id IN ({placeholders}) "
                "ORDER BY l.id FOR UPDATE",
                (tenant_id, *lotto_ids),
            )
            righe_lotti = cursor.fetchall()
            lotti = {row[0]: Decimal(str(row[1])) for row in righe_lotti}
            if len(lotti) != len(lotto_ids):
                raise LottoNonTrovato
            for row in righe_lotti:
                if not row[2]:
                    raise ArticoloNonUtilizzabileComeInput(
                        f"L'articolo del lotto {row[0]} non è abilitato come input di lavorazione."
                    )
                oggi = _data_valore(_row_value(row, 5))
                data_scadenza = _data_valore(_row_value(row, 3))
                data_tmc = _data_valore(_row_value(row, 4))
                if oggi is not None and data_scadenza is not None and data_scadenza < oggi:
                    raise LottoScaduto(
                        f"Il lotto {row[0]} ha una data di scadenza superata."
                    )
                if (
                    oggi is not None
                    and data_tmc is not None
                    and data_tmc < oggi
                    and row[0] in input_senza_conferma_tmc
                ):
                    raise ConfermaTmcScadutoRichiesta(
                        f"Il lotto {row[0]} ha il TMC superato: confermare esplicitamente l'utilizzo."
                    )
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

            if ricetta_id is not None:
                cursor.execute(
                    "SELECT articolo_id FROM ricette "
                    "WHERE tenant_id = %s AND id = %s AND attiva = 1 "
                    "FOR UPDATE",
                    (tenant_id, ricetta_id),
                )
                ricetta = cursor.fetchone()
                if (
                    ricetta is None
                    or ricetta[0] not in {riga.articolo_id for riga in output}
                ):
                    raise RicettaNonTrovata

            cursor.execute(
                "INSERT INTO lavorazioni "
                "(tenant_id, data_lavorazione, descrizione, operatore_id, operatore, "
                "ricetta_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    tenant_id,
                    data,
                    descrizione,
                    operatore_id,
                    operatore,
                    ricetta_id,
                ),
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
                    "data_creazione, data_scadenza, data_tmc, origine, "
                    "quantita_iniziale, quantita_disponibile, "
                    "unita_misura, lavorazione_id) "
                    "VALUES (%s, %s, 'V', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        tenant_id,
                        riga.articolo_id,
                        numero,
                        codice,
                        data,
                        getattr(riga, "data_scadenza", None),
                        getattr(riga, "data_tmc", None),
                        getattr(riga, "origine", None),
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
