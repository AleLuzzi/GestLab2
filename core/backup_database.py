"""Crea un backup SQL di struttura e dati del database GestLab.

Uso:
    python -m core.backup_database [percorso_output.sql]

Senza percorso, salva il file in ``backups/gestlab_backup_<timestamp>.sql``
nella root del progetto. Il dump include tabelle, viste e righe; non include
utenti MySQL, trigger, routine o eventi.
"""

import argparse
import datetime
import os
import shutil
import tempfile
from decimal import Decimal

from .db import connection

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea un backup SQL del database GestLab.")
    parser.add_argument(
        "output",
        nargs="?",
        help="percorso del file .sql (default: cartella backups nella root)",
    )
    args = parser.parse_args()

    path, conteggi = esporta_backup(args.output)
    print(f"Backup creato: {path}")
    print("Righe esportate per tabella:")
    for tabella, conteggio in sorted(conteggi.items()):
        print(f"  {tabella}: {conteggio}")
    print(f"Totale righe: {sum(conteggi.values())}")


if __name__ == "__main__":
    main()
