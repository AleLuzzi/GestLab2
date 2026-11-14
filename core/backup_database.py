"""Crea un backup SQL di struttura e dati del database GestLab.

Uso:
    python -m core.backup_database [percorso_output.sql]
    python -m core.backup_database --ripristina backup.sql --database gestlab_restore

Senza percorso, salva il file in ``backups/gestlab_backup_<timestamp>.sql``
nella root del progetto. Il dump include tabelle, viste e righe; non include
utenti MySQL, trigger, routine o eventi. Il ripristino crea o riusa solo un
database vuoto, diverso da quello configurato per l'applicazione.
"""

import argparse
import datetime
import os
import re
import shutil
import tempfile
from decimal import Decimal

import mysql.connector

from .db import _database_tls_options, connection
from .env import get_secret

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
_NOME_DATABASE = re.compile(r"^[A-Za-z0-9_]+$")


def _quote_identifier(identifier: str) -> str:
    """Quota un identificatore MySQL."""
    return "`" + identifier.replace("`", "``") + "`"


def _sql_value(value) -> str:
    """Serializza un valore restituito da MySQL in un'espressione SQL."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "X'" + bytes(value).hex() + "'"
    if isinstance(value, datetime.datetime):
        value = value.isoformat(sep=" ")
    elif isinstance(value, datetime.timedelta):
        microsecondi_totali = (
            (value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds
        )
        segno = "-" if microsecondi_totali < 0 else ""
        secondi, frazione = divmod(abs(microsecondi_totali), 1_000_000)
        ore, resto = divmod(secondi, 3600)
        minuti, secondi = divmod(resto, 60)
        testo = f"{segno}{ore:02d}:{minuti:02d}:{secondi:02d}"
        if frazione:
            testo += f".{frazione:06d}"
        value = testo
    elif isinstance(value, (datetime.date, datetime.time)):
        value = value.isoformat()
    if isinstance(value, str):
        encoded = value.encode("utf-8").hex()
        return "CONVERT(X'" + encoded + "' USING utf8mb4)"
    raise TypeError(f"Tipo di dato MySQL non supportato nel backup: {type(value).__name__}")


def _scrivi_backup(cursor, output) -> dict[str, int]:
    """Scrive schema e righe; restituisce il numero di righe per tabella."""
    cursor.execute("SHOW FULL TABLES")
    oggetti = cursor.fetchall()
    tabelle = [(riga[0], riga[1]) for riga in oggetti if riga[1] == "BASE TABLE"]
    viste = [(riga[0], riga[1]) for riga in oggetti if riga[1] == "VIEW"]
    if len(tabelle) + len(viste) != len(oggetti):
        raise RuntimeError("Il database contiene oggetti non supportati dal backup.")

    conteggi = {}
    output.write("-- Backup GestLab: schema e dati\n")
    output.write(
        f"-- Generato il {datetime.datetime.now().astimezone().isoformat()}\n"
    )
    output.write("-- Ripristinare in un database vuoto; gli oggetti esistenti non vengono eliminati.\n")
    output.write("SET NAMES utf8mb4;\n")
    output.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

    for nome, _ in tabelle:
        identificatore = _quote_identifier(nome)
        cursor.execute(f"SHOW CREATE TABLE {identificatore}")
        definizione = cursor.fetchone()
        if not definizione:
            raise RuntimeError(f"Impossibile leggere lo schema della tabella {nome}.")
        output.write(f"-- Tabella: {nome}\n{definizione[1]};\n\n")

        cursor.execute(f"SELECT * FROM {identificatore}")
        colonne = [descrizione[0] for descrizione in cursor.description]
        colonne_sql = ", ".join(_quote_identifier(colonna) for colonna in colonne)
        inserimento = f"INSERT INTO {identificatore} ({colonne_sql}) VALUES "
        conteggio = 0

        while True:
            righe = cursor.fetchmany(200)
            if not righe:
                break
            valori = [
                "(" + ", ".join(_sql_value(valore) for valore in riga) + ")"
                for riga in righe
            ]
            output.write(inserimento + ",\n".join(valori) + ";\n")
            conteggio += len(righe)

        conteggi[nome] = conteggio
        output.write(f"-- Righe esportate: {conteggio}\n\n")

    for nome, _ in viste:
        cursor.execute(f"SHOW CREATE VIEW {_quote_identifier(nome)}")
        definizione = cursor.fetchone()
        if not definizione:
            raise RuntimeError(f"Impossibile leggere lo schema della vista {nome}.")
        output.write(f"-- Vista: {nome}\n{definizione[1]};\n\n")

    output.write("SET FOREIGN_KEY_CHECKS=1;\n")
    return conteggi


def esporta_backup(output_path: str | None = None) -> tuple[str, dict[str, int]]:
    """Crea un dump SQL senza sovrascrivere un file di backup esistente."""
    if output_path is None:
        os.makedirs(DEFAULT_BACKUP_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            DEFAULT_BACKUP_DIR, f"gestlab_backup_{timestamp}.sql"
        )

    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    temp_path = None
    output_created = False

    try:
        with connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=output_dir,
                prefix=".gestlab-backup-",
                suffix=".tmp",
                delete=False,
            ) as output:
                temp_path = output.name
                conteggi = _scrivi_backup(cursor, output)

        with open(temp_path, "rb") as sorgente:
            with open(output_path, "xb") as destinazione:
                output_created = True
                shutil.copyfileobj(sorgente, destinazione)
    except Exception:
        if output_created and os.path.exists(output_path):
            os.remove(output_path)
        raise
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.remove(temp_path)

    return output_path, conteggi


def _istruzioni_sql(script: str):
    """Separa le istruzioni del dump. I valori testuali sono esadecimali."""
    for pezzo in script.split(";\n"):
        righe = [
            riga for riga in pezzo.split("\n")
            if riga.strip() and not riga.startswith("--")
        ]
        istruzione = "\n".join(righe).strip()
        if istruzione:
            yield istruzione


def _connessione_server(database=None):
    """Apre una connessione fuori dal pool, verso un database scelto."""
    host = get_secret("DB_HOST", "localhost")
    parametri = {
        "host": host,
        "port": int(get_secret("DB_PORT", "3306")),
        "user": get_secret("DB_USER", "root"),
        "password": get_secret("DB_PWD", ""),
        **_database_tls_options(host),
    }
    if database is not None:
        parametri["database"] = database
    return mysql.connector.connect(**parametri)


def ripristina_backup(percorso_sql: str, database_destinazione: str) -> None:
    """Carica un dump GestLab in un database vuoto, diverso da quello in uso.

    Non elimina oggetti già presenti. Se la destinazione contiene tabelle,
    il ripristino si interrompe prima di scrivere.
    """
    if not _NOME_DATABASE.fullmatch(database_destinazione or ""):
        raise ValueError(
            "Il database di destinazione può contenere solo lettere, cifre e underscore."
        )
    database_in_uso = get_secret("DB_NAME", "data")
    if database_destinazione == database_in_uso:
        raise RuntimeError(
            "Il ripristino non può usare il database configurato. "
            "Indicare un database vuoto diverso."
        )

    percorso = os.path.abspath(percorso_sql)
    with open(percorso, encoding="utf-8") as sorgente:
        prima_riga = sorgente.readline()
        if "Backup GestLab" not in prima_riga:
            raise RuntimeError("Il file non è un backup GestLab.")
        script = prima_riga + sorgente.read()

    server = _connessione_server()
    try:
        cursor = server.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s",
            (database_destinazione,),
        )
        tabelle_presenti = cursor.fetchone()[0]
        if tabelle_presenti:
            raise RuntimeError(
                f"Il database {database_destinazione} contiene già "
                f"{tabelle_presenti} tabelle."
            )
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {_quote_identifier(database_destinazione)} "
            "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_general_ci"
        )
        server.commit()
    finally:
        server.close()

    destinazione = _connessione_server(database_destinazione)
    try:
        cursor = destinazione.cursor()
        for istruzione in _istruzioni_sql(script):
            cursor.execute(istruzione)
        destinazione.commit()
    except Exception:
        destinazione.rollback()
        raise
    finally:
        destinazione.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea o ripristina un backup SQL di GestLab.")
    parser.add_argument(
        "output",
        nargs="?",
        help="percorso del file .sql da creare (default: cartella backups nella root)",
    )
    parser.add_argument(
        "--ripristina",
        metavar="FILE",
        help="dump GestLab da caricare in un database vuoto",
    )
    parser.add_argument(
        "--database",
        help="database di destinazione, diverso da quello configurato",
    )
    args = parser.parse_args()

    if args.ripristina:
        if not args.database:
            parser.error("--ripristina richiede --database")
        ripristina_backup(args.ripristina, args.database)
        print(f"Backup ripristinato in {args.database}")
        return

    path, conteggi = esporta_backup(args.output)
    print(f"Backup creato: {path}")
    print("Righe esportate per tabella:")
    for tabella, conteggio in sorted(conteggi.items()):
        print(f"  {tabella}: {conteggio}")
    print(f"Totale righe: {sum(conteggi.values())}")


if __name__ == "__main__":
    main()
