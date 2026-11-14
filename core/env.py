"""Gestione dei segreti tramite variabili d'ambiente e file ``.env``.

In vista della migrazione SaaS, i segreti (password DB, token Facebook,
chiavi API) NON devono restare in ``config.ini`` in chiaro. Questo modulo
carica un file ``.env`` (se presente) usando ``python-dotenv`` e offre
``get_secret`` per leggere i segreti con priorita':

1. Variabili d'ambiente di sistema (utile in cloud / container).
2. File ``.env`` nella root del progetto.
3. Fallback a ``config.ini`` solo fuori da produzione e staging, per
   compatibilita' desktop locale.
"""

import ipaddress
import os
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback senza python-dotenv
    load_dotenv = None

# Root del progetto (una cartella sopra `core/`).
_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def ambiente_corrente():
    """Restituisce ``production``, ``staging`` oppure il valore normalizzato."""
    return os.environ.get("GESTLAB_ENV", "").strip().lower()


def is_production_environment():
    """Indica se il processo è configurato per l'ambiente di produzione."""
    return ambiente_corrente() == "production"


def is_deployed_environment():
    """Produzione e staging pubblicato: niente segreti di sviluppo."""
    return ambiente_corrente() in {"production", "staging"}


def hosting_gestito():
    """True se questo processo è il profilo vendibile, non il Lightsail di test."""
    return os.environ.get("GESTLAB_HOSTING", "").strip().lower() == "managed"


def _host_loopback(host):
    nome = (host or "").strip().lower().rstrip(".")
    if nome == "localhost":
        return True
    try:
        return ipaddress.ip_address(nome).is_loopback
    except ValueError:
        return False


def valida_hosting_gestito():
    """Blocca l'avvio se produzione o staging gestiti non sono separati e pubblicati.

    Il Lightsail di test non imposta ``GESTLAB_HOSTING=managed`` e non entra qui.
    Il profilo gestito richiede URL HTTPS su dominio, database remoto con nome
    dedicato, segreti dichiarati come provenienti da Secret Manager, backup con
    point-in-time recovery e l'altro ambiente su un server database diverso.
    """
    if not hosting_gestito():
        return
    ambiente = ambiente_corrente()
    if ambiente not in {"production", "staging"}:
        raise RuntimeError(
            "GESTLAB_HOSTING=managed richiede GESTLAB_ENV production oppure staging."
        )

    url = os.environ.get("GESTLAB_PUBLIC_URL", "").strip()
    parsed = urlparse(url)
    dominio = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not dominio or _host_loopback(dominio):
        raise RuntimeError(
            "L'URL pubblico del hosting gestito deve essere HTTPS su un dominio."
        )
    try:
        ipaddress.ip_address(dominio)
        raise RuntimeError(
            "L'URL pubblico del hosting gestito deve essere un dominio, non un indirizzo IP."
        )
    except ValueError:
        pass
    if ambiente == "staging" and "staging" not in dominio:
        raise RuntimeError("L'URL di staging deve contenere staging nel dominio.")

    db_host = os.environ.get("DB_HOST", "").strip()
    db_name = os.environ.get("DB_NAME", "").strip()
    nome_atteso = f"gestlab_{ambiente}"
    if _host_loopback(db_host):
        raise RuntimeError("Il database gestito non può essere locale.")
    if not os.environ.get("DB_SSL_CA", "").strip():
        raise RuntimeError(
            "DB_SSL_CA è obbligatorio per il database gestito."
        )
    if db_name != nome_atteso:
        raise RuntimeError(
            f"Il database di {ambiente} deve chiamarsi {nome_atteso}."
        )
    if os.environ.get("GESTLAB_SECRET_SOURCE", "").strip().lower() != "secrets-manager":
        raise RuntimeError(
            "I segreti del hosting gestito devono arrivare da Secret Manager."
        )
    if os.environ.get("GESTLAB_DB_BACKUP", "").strip().lower() != "pitr":
        raise RuntimeError(
            "Impostare GESTLAB_DB_BACKUP=pitr solo con backup automatici "
            "e point-in-time recovery attivi."
        )

    peer_host = os.environ.get("GESTLAB_PEER_DB_HOST", "").strip().lower().rstrip(".")
    peer_name = os.environ.get("GESTLAB_PEER_DB_NAME", "").strip()
    altro = "staging" if ambiente == "production" else "production"
    if not peer_host or not peer_name:
        raise RuntimeError(
            "Indicare GESTLAB_PEER_DB_HOST e GESTLAB_PEER_DB_NAME dell'altro ambiente."
        )
    if peer_host == db_host.lower().rstrip("."):
        raise RuntimeError(
            "Staging e produzione non possono usare lo stesso server database."
        )
    if peer_name != f"gestlab_{altro}":
        raise RuntimeError(
            f"Il database dell'altro ambiente deve chiamarsi gestlab_{altro}."
        )


def load_env_file():
    """Carica il file ``.env`` nella root del progetto (best-effort)."""
    if load_dotenv is not None:
        load_dotenv(ENV_PATH)


def get_secret(name, default=""):
    """Legge un segreto da env/.env, poi da ``config.ini`` solo in sviluppo.

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

    if is_deployed_environment():
        return default

    # Fallback a config.ini (compatibilita' desktop locale)
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
