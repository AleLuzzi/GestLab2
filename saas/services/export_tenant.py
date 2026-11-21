"""Export dei dati di un solo tenant, senza segreti di autenticazione."""

import csv
import io
import json
import re
import zipfile
from datetime import date, datetime
from decimal import Decimal

from core.db import connection

_IDENTIFICATORE = re.compile(r"^[A-Za-z0-9_]+$")
TABELLE_ESCLUSE = frozenset({"password_reset", "refresh_token"})
COLONNE_ESCLUSE = {
    "utenti": frozenset({"password_hash"}),
    "dispositivi_stampa": frozenset({"token"}),
}
NOTA_ESCLUSIONI = (
    "L'archivio contiene i dati del solo laboratorio che ha eseguito l'export. "
    "Non include gli hash delle password, i token di reimpostazione, "
    "i refresh token e i token dei dispositivi di stampa."
)
NOME_JSON = "dati-laboratorio.json"
NOME_CSV = "dati-laboratorio-csv.zip"


def prepara(tenant_id, formato):
    """Restituisce contenuto, media type e nome file per json o csv."""
    if formato not in ("json", "csv"):
        raise ValueError("Formato non valido: indicare json oppure csv.")
    dati = raccogli(int(tenant_id))
    if formato == "json":
        return _json(int(tenant_id), dati), "application/json", NOME_JSON
    return _zip_csv(dati), "application/zip", NOME_CSV


def raccogli(tenant_id):
    """Legge le tabelle del tenant. Il valore arriva dal chiamante autenticato."""
    tenant_id = int(tenant_id)
    with connection() as conn:
        cursor = conn.cursor()
        schema = _colonne(cursor)
        dati = {}
        for tabella in _tabelle_da_esportare(schema):
            colonne = _colonne_esportate(tabella, schema[tabella])
            if not colonne:
                continue
            dati[tabella] = {
                "colonne": colonne,
                "righe": _righe(cursor, tabella, colonne, tenant_id),
            }
    return dati


def _colonne(cursor):
    cursor.execute(
        "SELECT c.TABLE_NAME, c.COLUMN_NAME "
        "FROM information_schema.COLUMNS c "
        "JOIN information_schema.TABLES t "
        "ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME "
        "WHERE c.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE = 'BASE TABLE' "
        "ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION"
    )
    tabelle = {}
    for nome, colonna in cursor.fetchall():
        nome = str(nome)
        colonna = str(colonna)
        if not _IDENTIFICATORE.match(nome) or not _IDENTIFICATORE.match(colonna):
            continue
        tabelle.setdefault(nome, []).append(colonna)
    return tabelle


def _tabelle_da_esportare(tabelle):
    scelte = ["tenant"] if "tenant" in tabelle else []
    for nome in sorted(tabelle):
        if nome == "tenant" or nome in TABELLE_ESCLUSE:
            continue
        if "tenant_id" not in tabelle[nome]:
            continue
        scelte.append(nome)
    return scelte


def _colonne_esportate(tabella, colonne):
    escluse = COLONNE_ESCLUSE.get(tabella, frozenset())
    return [colonna for colonna in colonne if colonna not in escluse]


def _righe(cursor, tabella, colonne, tenant_id):
    elenco = ", ".join(f"`{colonna}`" for colonna in colonne)
    if tabella == "tenant":
        query = f"SELECT {elenco} FROM `tenant` WHERE `id` = %s"
    else:
        ordine = _colonna_ordine(colonne)
        query = (
            f"SELECT {elenco} FROM `{tabella}` "
            f"WHERE `tenant_id` = %s ORDER BY {ordine}"
        )
    cursor.execute(query, (tenant_id,))
    return [
        {colonna: _valore(valore) for colonna, valore in zip(colonne, riga)}
        for riga in cursor.fetchall()
    ]


def _colonna_ordine(colonne):
    for candidata in ("id", "ID"):
        if candidata in colonne:
            return f"`{candidata}`"
    return f"`{colonne[0]}`"


def _valore(valore):
    if isinstance(valore, datetime):
        return valore.isoformat(sep=" ")
    if isinstance(valore, date):
        return valore.isoformat()
    if isinstance(valore, Decimal):
        return format(valore, "f")
    if isinstance(valore, (bytes, bytearray)):
        return valore.decode("utf-8", errors="replace")
    return valore


def _json(tenant_id, dati):
    corpo = {
        "versione": 1,
        "tenant_id": tenant_id,
        "esclusioni": NOTA_ESCLUSIONI,
        "tabelle": {nome: tabella["righe"] for nome, tabella in dati.items()},
    }
    return json.dumps(corpo, ensure_ascii=False, indent=2).encode("utf-8")


def _zip_csv(dati):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archivio:
        archivio.writestr("LEGGIMI.txt", NOTA_ESCLUSIONI + "\n")
        for nome, tabella in dati.items():
            archivio.writestr(f"{nome}.csv", _csv(tabella["colonne"], tabella["righe"]))
    return buffer.getvalue()


def _csv(colonne, righe):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=colonne, lineterminator="\n")
    writer.writeheader()
    writer.writerows(righe)
    return buffer.getvalue().encode("utf-8-sig")
