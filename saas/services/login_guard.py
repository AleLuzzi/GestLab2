"""Limite ai tentativi di login falliti, per indirizzo email e per IP.

Il contatore vive nel processo: un riavvio lo azzera. Dieci errori sullo
stesso indirizzo, o cinquanta dallo stesso IP, bloccano i tentativi successivi
per la finestra configurata.
"""

import os
import threading
import time


class LimiteAccessoSuperato(Exception):
    """L'indirizzo o l'IP ha esaurito i tentativi consentiti."""

    def __init__(self, secondi: int):
        self.secondi = max(1, int(secondi))
        super().__init__(self.secondi)


class LoginGuard:
    """Finestra mobile di fallimenti, distinta per chiave."""

    def __init__(self, finestra_secondi: int = 900, clock=None):
        self.finestra_secondi = finestra_secondi
        self._clock = clock or time.monotonic
        self._fallimenti: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def controlla(self, chiave: str, massimo: int) -> None:
        """Solleva ``LimiteAccessoSuperato`` se la chiave è già al limite."""
        with self._lock:
            attivi = self._attivi(chiave)
            self._fallimenti[chiave] = attivi
            if len(attivi) >= massimo:
                attesa = self.finestra_secondi - (self._clock() - attivi[0])
                raise LimiteAccessoSuperato(attesa)

    def registra_fallimento(self, chiave: str) -> None:
        """Registra un tentativo rifiutato dentro la finestra corrente."""
        with self._lock:
            attivi = self._attivi(chiave)
            attivi.append(self._clock())
            self._fallimenti[chiave] = attivi

    def azzera(self, chiave: str) -> None:
        """Dimentica i fallimenti dopo un accesso riuscito."""
        with self._lock:
            self._fallimenti.pop(chiave, None)

    def _attivi(self, chiave: str) -> list[float]:
        ora = self._clock()
        return [
            istante
            for istante in self._fallimenti.get(chiave, [])
            if ora - istante < self.finestra_secondi
        ]


def _intero_env(nome: str, default: str) -> int:
    try:
        valore = int(os.environ.get(nome, default))
    except ValueError:
        valore = int(default)
    return valore if valore > 0 else int(default)


MAX_FALLIMENTI_EMAIL = _intero_env("GESTLAB_LOGIN_MAX_FALLIMENTI", "10")
MAX_FALLIMENTI_IP = _intero_env("GESTLAB_LOGIN_MAX_FALLIMENTI_IP", "50")
FINESTRA_SECONDI = _intero_env("GESTLAB_LOGIN_FINESTRA_SECONDI", "900")

guard = LoginGuard(finestra_secondi=FINESTRA_SECONDI)
