"""Gestione dei segreti tramite variabili d'ambiente e file ``.env``.

In vista della migrazione SaaS, i segreti (password DB, token Facebook,
chiavi API) NON devono restare in ``config.ini`` in chiaro. Questo modulo
carica un file ``.env`` (se presente) usando ``python-dotenv`` e offre
``get_secret`` per leggere i segreti con priorita':

1. Variabili d'ambiente di sistema (utile in cloud / container).
2. File ``.env`` nella root del progetto.
3. Fallback a ``config.ini`` (solo per compatibilita' desktop locale).
"""

import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback senza python-dotenv
    load_dotenv = None

# Root del progetto (una cartella sopra `core/`).
_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def load_env_file():
    """Carica il file ``.env`` nella root del progetto (best-effort)."""
    if load_dotenv is not None:
        load_dotenv(ENV_PATH)


def get_secret(name, default=""):
    """Legge un segreto da env/.env, poi fallback a ``config.ini``.

    Args:
        name: nome della variabile d'ambiente (es. ``DB_PWD``).
        default: valore di default se non trovato.

    Returns:
        str: il valore del segreto o ``default``.
    """
    # 1) Variabile d'ambiente di sistema o .env
    value = os.environ.get(name)
    if value is not None and value != "":
        return value

    # 2) Fallback a config.ini (compatibilita' desktop)
    try:
        from .config import get_config

        cfg = get_config()
        mapping = {
            "DB_HOST": ("DataBase", "host"),
            "DB_PORT": ("DataBase", "port"),
            "DB_NAME": ("DataBase", "db"),
            "DB_USER": ("DataBase", "user"),
            "DB_PWD": ("DataBase", "pwd"),
            "JWT_SECRET": ("Auth", "jwt_secret"),
            "FB_TOKEN": ("Facebook", "token"),
        }
        if name in mapping and mapping[name][0] in cfg:
            return cfg[mapping[name][0]].get(mapping[name][1], default)
    except Exception:
        pass

    return default


# Carica il file .env all'import del modulo.
load_env_file()
