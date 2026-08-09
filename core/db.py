"""Accesso al database per il core applicativo (framework-agnostico).

Unifica il data layer dei due progetti (GestLab2 e Laboratorio) usando il
pattern *context manager* di ``Laboratorio/db.py``, eliminando la connessione
globale condivisa di ``controller_db.py``.

Le credenziali vengono lette da variabili d'ambiente / ``.env`` (priorita')
con fallback a ``config.ini``. In cloud (SaaS) vanno fornite via Secret
Manager o env del container.
"""

from contextlib import contextmanager

import mysql.connector

from .env import get_secret


def get_connection():
    """Crea e restituisce una nuova connessione MySQL.

    Il chiamante deve chiudere la connessione quando non serve piu' (es.
    ``conn.close()`` in un ``finally`` o tramite il context manager
    :func:`connection`).
    """
    host = get_secret("DB_HOST", "localhost")
    port = int(get_secret("DB_PORT", "3306"))
    database = get_secret("DB_NAME", "data")
    user = get_secret("DB_USER", "root")
    password = get_secret("DB_PWD", "")
    return mysql.connector.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )


def close_connection(conn):
    """Chiude la connessione in modo sicuro (ignora gli errori)."""
    if conn is None:
        return
    try:
        conn.close()
    except Exception:
        pass


@contextmanager
def connection():
    """Context manager per usare una connessione MySQL con ``with``.

    La connessione viene chiusa automaticamente all'uscita dal blocco.

    Esempio::

        with connection() as conn:
            c = conn.cursor()
            c.execute("SELECT ...")
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
