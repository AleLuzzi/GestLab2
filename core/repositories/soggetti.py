"""Accesso ai soggetti condivisi da clienti e fornitori."""

from ..db import connection


class FornitoreConStoricoError(ValueError):
    """Impossibile rimuovere il ruolo fornitore usato da documenti esistenti."""


_CAMPI = (
    "denominazione",
    "tipo_soggetto",
    "nome",
    "cognome",
    "partita_iva",
    "codice_fiscale",
    "indirizzo",
    "numero_civico",
    "cap",
    "citta",
    "provincia",
    "paese",
    "email",
    "telefono",
    "codice_destinatario",
    "pec",
)

_SELECT = (
    "SELECT s.id, s.tenant_id, s.denominazione, s.tipo_soggetto, s.nome, "
    "s.cognome, s.partita_iva, s.codice_fiscale, s.indirizzo, s.numero_civico, "
    "s.cap, s.citta, s.provincia, s.paese, s.email, s.telefono, "
    "s.codice_destinatario, s.pec, s.attivo, "
    "EXISTS (SELECT 1 FROM soggetti_ruoli rc "
    "WHERE rc.tenant_id = s.tenant_id AND rc.soggetto_id = s.id "
    "AND rc.ruolo = 'cliente'), "
    "EXISTS (SELECT 1 FROM soggetti_ruoli rf "
    "WHERE rf.tenant_id = s.tenant_id AND rf.soggetto_id = s.id "
    "AND rf.ruolo = 'fornitore'), "
    "COALESCE(f.flag1_ing_merce, 0), COALESCE(f.flag2_inventario, 0), f.ID "
    "FROM soggetti s "
    "LEFT JOIN fornitori f ON f.tenant_id = s.tenant_id AND f.soggetto_id = s.id "
)


def _to_dict(row):
    return {
        "id": row[0],
        "tenant_id": row[1],
        "denominazione": row[2],
        "tipo_soggetto": row[3],
        "nome": row[4],
        "cognome": row[5],
        "partita_iva": row[6],
        "codice_fiscale": row[7],
        "indirizzo": row[8],
        "numero_civico": row[9],
        "cap": row[10],
        "citta": row[11],
        "provincia": row[12],
        "paese": row[13],
        "email": row[14],
        "telefono": row[15],
        "codice_destinatario": row[16],
        "pec": row[17],
        "attivo": bool(row[18]),
        "ruolo_cliente": bool(row[19]),
        "ruolo_fornitore": bool(row[20]),
        "flag1_ing_merce": int(row[21] or 0),
        "flag2_inventario": int(row[22] or 0),
        "fornitore_legacy_id": row[23],
    }


def _fetch_one(cursor, tenant_id, soggetto_id):
    cursor.execute(
        _SELECT
        + "WHERE s.tenant_id = %s AND s.id = %s",
        (tenant_id, soggetto_id),
    )
    row = cursor.fetchone()
    return _to_dict(row) if row else None


def lista(tenant_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _SELECT
            + "WHERE s.tenant_id = %s ORDER BY s.denominazione, s.id",
            (tenant_id,),
        )
        return [_to_dict(row) for row in cursor.fetchall()]


def trova(tenant_id, soggetto_id):
    with connection() as conn:
        return _fetch_one(conn.cursor(), tenant_id, soggetto_id)


def fornitore_abilitato(cursor, tenant_id, soggetto_id):
    """Legge il fornitore valido usando il cursore della transazione chiamante."""
    cursor.execute(
        "SELECT s.id, s.denominazione "
        "FROM soggetti s "
        "JOIN soggetti_ruoli r ON r.tenant_id = s.tenant_id "
        "AND r.soggetto_id = s.id AND r.ruolo = 'fornitore' "
        "JOIN fornitori f ON f.tenant_id = s.tenant_id AND f.soggetto_id = s.id "
        "WHERE s.tenant_id = %s AND s.id = %s AND s.attivo = 1 "
        "AND f.flag1_ing_merce = 1",
        (tenant_id, soggetto_id),
    )
    row = cursor.fetchone()
    return {"id": row[0], "denominazione": row[1]} if row else None


def _ruoli(payload):
    ruoli = []
    if payload.get("ruolo_cliente"):
        ruoli.append("cliente")
    if payload.get("ruolo_fornitore"):
        ruoli.append("fornitore")
    if not ruoli:
        raise ValueError("Selezionare almeno il ruolo cliente o fornitore.")
    return ruoli


def crea(tenant_id, payload):
    payload = dict(payload)
    ruoli = _ruoli(payload)
    denominazione = payload.get("denominazione", "").strip()
    if not denominazione:
        raise ValueError("La denominazione è obbligatoria.")
    payload["denominazione"] = denominazione

    with connection() as conn:
        cursor = conn.cursor()
        try:
            campi = ", ".join(_CAMPI)
            placeholders = ", ".join(["%s"] * (len(_CAMPI) + 2))
            cursor.execute(
                f"INSERT INTO soggetti (tenant_id, {campi}, attivo) "
                f"VALUES ({placeholders})",
                (
                    tenant_id,
                    *(payload.get(campo) for campo in _CAMPI),
                    int(bool(payload.get("attivo", True))),
                ),
            )
            soggetto_id = cursor.lastrowid
            for ruolo in ruoli:
                cursor.execute(
                    "INSERT INTO soggetti_ruoli (tenant_id, soggetto_id, ruolo) "
                    "VALUES (%s, %s, %s)",
                    (tenant_id, soggetto_id, ruolo),
                )
            if "fornitore" in ruoli:
                cursor.execute(
                    "INSERT INTO fornitori "
                    "(azienda, flag1_ing_merce, flag2_inventario, tenant_id, soggetto_id) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        payload["denominazione"][:50],
                        int(bool(payload.get("flag1_ing_merce"))),
                        int(bool(payload.get("flag2_inventario"))),
                        tenant_id,
                        soggetto_id,
                    ),
                )
            result = _fetch_one(cursor, tenant_id, soggetto_id)
            if not result:
                raise RuntimeError("Impossibile rileggere l'anagrafica appena creata.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return result


def aggiorna(tenant_id, soggetto_id, payload):
    payload = dict(payload)
    ruoli = _ruoli(payload)
    denominazione = payload.get("denominazione", "").strip()
    if not denominazione:
        raise ValueError("La denominazione è obbligatoria.")
    payload["denominazione"] = denominazione
    with connection() as conn:
        cursor = conn.cursor()
        try:
            esistente = _fetch_one(cursor, tenant_id, soggetto_id)
            if not esistente:
                return None

            campi = ", ".join(f"{campo} = %s" for campo in _CAMPI)
            cursor.execute(
                f"UPDATE soggetti SET {campi}, attivo = %s "
                "WHERE tenant_id = %s AND id = %s",
                (
                    *(payload.get(campo) for campo in _CAMPI),
                    int(bool(payload.get("attivo", True))),
                    tenant_id,
                    soggetto_id,
                ),
            )

            era_fornitore = esistente["ruolo_fornitore"]
            e_fornitore = "fornitore" in ruoli
            if era_fornitore and not e_fornitore:
                cursor.execute(
                    "SELECT "
                    "(SELECT COUNT(*) FROM ingresso_merce "
                    " WHERE tenant_id = %s AND fornitore_id = %s) + "
                    "(SELECT COUNT(*) FROM documenti_ingresso "
                    " WHERE tenant_id = %s AND fornitore_id = %s)",
                    (tenant_id, soggetto_id, tenant_id, soggetto_id),
                )
                if cursor.fetchone()[0]:
                    raise FornitoreConStoricoError(
                        "Non è possibile rimuovere il ruolo fornitore: "
                        "il soggetto è presente nello storico degli ingressi."
                    )
                cursor.execute(
                    "DELETE FROM fornitori WHERE tenant_id = %s AND soggetto_id = %s",
                    (tenant_id, soggetto_id),
                )
            elif e_fornitore and era_fornitore:
                cursor.execute(
                    "UPDATE fornitori SET azienda = %s, flag1_ing_merce = %s, "
                    "flag2_inventario = %s WHERE tenant_id = %s AND soggetto_id = %s",
                    (
                        payload["denominazione"][:50],
                        int(bool(payload.get("flag1_ing_merce"))),
                        int(bool(payload.get("flag2_inventario"))),
                        tenant_id,
                        soggetto_id,
                    ),
                )
            elif e_fornitore:
                cursor.execute(
                    "INSERT INTO fornitori "
                    "(azienda, flag1_ing_merce, flag2_inventario, tenant_id, soggetto_id) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        payload["denominazione"][:50],
                        int(bool(payload.get("flag1_ing_merce"))),
                        int(bool(payload.get("flag2_inventario"))),
                        tenant_id,
                        soggetto_id,
                    ),
                )

            cursor.execute(
                "DELETE FROM soggetti_ruoli WHERE tenant_id = %s AND soggetto_id = %s",
                (tenant_id, soggetto_id),
            )
            for ruolo in ruoli:
                cursor.execute(
                    "INSERT INTO soggetti_ruoli (tenant_id, soggetto_id, ruolo) "
                    "VALUES (%s, %s, %s)",
                    (tenant_id, soggetto_id, ruolo),
                )
            result = _fetch_one(cursor, tenant_id, soggetto_id)
            if not result:
                raise RuntimeError("Impossibile rileggere l'anagrafica aggiornata.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return result


def disattiva(tenant_id, soggetto_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE soggetti SET attivo = 0 WHERE tenant_id = %s AND id = %s",
            (tenant_id, soggetto_id),
        )
        conn.commit()
        return cursor.rowcount > 0
