"""Esporta la struttura del database in un file .sql.

Genera un dump dello SCHEMA (CREATE TABLE / CREATE DATABASE, senza dati)
del database GestLab, utile per versioning, backup dello schema o per
importarlo in MySQL Workbench.

Uso:
    python -m core.export_schema [percorso_output.sql]

Di default scrive in `gestlab_schema.sql` nella root del progetto.
"""

import os
import sys

from .db import connection

# Root del progetto.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "gestlab_schema.sql")


def ottieni_nome_db():
    """Legge il nome del database dalle stesse config usate dal core."""
    from .env import get_secret
    return get_secret("DB_NAME", "data")


def esporta_schema(output_path: str) -> str:
    """Scrive lo schema del database (solo struttura) nel file indicato.

    Returns:
        str: il percorso del file scritto.
    """
    db_name = ottieni_nome_db()
    statements = [
        f"-- ------------------------------------------------",
        f"-- GestLab - Struttura del database '{db_name}'",
        f"-- Generato automaticamente il {__import__('datetime').datetime.now().isoformat()}",
        f"-- Contiene SOLO lo schema (CREATE TABLE), nessun dato.",
        f"-- ------------------------------------------------",
        "",
    ]

    with connection() as conn:
        c = conn.cursor()

        # Elenco tabelle (ordine alfabetico per leggibilità).
        c.execute("SHOW TABLES")
        tabelle = [r[0] for r in c.fetchall()]

        for tabella in tabelle:
            c.execute("SHOW CREATE TABLE `%s`" % tabella)
            row = c.fetchone()
            if row:
                statements.append(f"-- Tabella: {tabella}")
                statements.append(row[1] + ";")
                statements.append("")

    # Scrive il file.
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(statements))

    return output_path


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    path = esporta_schema(output)
    print(f"Schema esportato in: {path}")
    print(f"{len(open(path, encoding='utf-8').read().splitlines())} righe")


if __name__ == "__main__":
    main()
