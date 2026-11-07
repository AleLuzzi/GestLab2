"""Accesso al database per il core applicativo (framework-agnostico).

Unifica il data layer dei due progetti (GestLab2 e Laboratorio) usando il
pattern *context manager* di ``Laboratorio/db.py``, eliminando la connessione
globale condivisa di ``controller_db.py``.

Le credenziali vengono lette da variabili d'ambiente / ``.env`` (priorita')
con fallback a ``config.ini``. In cloud (SaaS) vanno fornite via Secret
Manager o env del container.
"""

from contextlib import contextmanager
import ipaddress
import os
import threading

import mysql.connector

from .env import get_secret


_MAX_POOL_SIZE = 32
_connection_pool = None
_connection_pool_lock = threading.Lock()


def _database_tls_options(host):
    """Configura TLS verificato per i database remoti."""
    ca_file = get_secret("DB_SSL_CA", "").strip()
    if ca_file:
        return {
            "ssl_ca": ca_file,
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        }

    is_loopback = host.lower().rstrip(".") == "localhost"
    try:
        is_loopback = is_loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass

    if (
        os.environ.get("GESTLAB_ENV", "").lower() == "production"
        and not is_loopback
    ):
        raise RuntimeError(
            "DB_SSL_CA è obbligatorio per connessioni MySQL remote in produzione"
        )
    return {}


def _get_connection_pool():
    """Crea pigramente il pool condiviso dal processo."""
    global _connection_pool
    if _connection_pool is None:
        with _connection_pool_lock:
            if _connection_pool is None:
                host = get_secret("DB_HOST", "localhost")
                pool_size = int(get_secret("DB_POOL_SIZE", "10"))
                if not 1 <= pool_size <= _MAX_POOL_SIZE:
                    raise ValueError(
                        f"DB_POOL_SIZE deve essere compreso tra 1 e {_MAX_POOL_SIZE}"
                    )

                _connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                    pool_size=pool_size,
                    host=host,
                    port=int(get_secret("DB_PORT", "3306")),
                    database=get_secret("DB_NAME", "data"),
                    user=get_secret("DB_USER", "root"),
                    password=get_secret("DB_PWD", ""),
                    **_database_tls_options(host),
                )
    return _connection_pool


def get_connection():
    """Preleva una connessione riutilizzabile dal pool MySQL.

    Il chiamante deve chiudere la connessione quando non serve piu' (es.
    ``conn.close()`` in un ``finally`` o tramite il context manager
    :func:`connection`).
    """
    return _get_connection_pool().get_connection()


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
