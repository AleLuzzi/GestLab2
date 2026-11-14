"""Servizio Windows del Local Print Agent.

Il token e l'URL stanno in ``%ProgramData%\\GestLab\\print-agent.env``, non
nel repository. L'installazione è in ``deploy/installa-print-agent.ps1``.
Richiede ``pywin32`` sul PC di banco; non è una dipendenza del backend Linux.
"""

import os
import sys


def _traccia(messaggio):
    """Scrive l'avvio del servizio, senza il token."""
    if os.path.basename(sys.executable).lower() != "pythonservice.exe":
        return
    try:
        cartella = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "GestLab")
        os.makedirs(cartella, exist_ok=True)
        with open(os.path.join(cartella, "print-agent-servizio.log"), "a", encoding="utf-8") as file:
            file.write(messaggio + "\n")
    except OSError:
        pass


_traccia("import del modulo")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

PERCORSO_CONFIGURAZIONE = os.path.join(
    os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
    "GestLab",
    "print-agent.env",
)


def carica_configurazione(percorso):
    """Legge URL, token e intervallo. Non registra il token."""
    dati = {}
    with open(percorso, encoding="utf-8-sig") as file:
        for riga in file:
            testo = riga.strip()
            if not testo or testo.startswith("#") or "=" not in testo:
                continue
            chiave, valore = testo.split("=", 1)
            dati[chiave.strip()] = valore.strip()
    url = dati.get("GESTLAB_API_URL", "")
    token = dati.get("GESTLAB_AGENT_TOKEN", "")
    if not url or not token:
        raise RuntimeError(
            "Il file di servizio deve contenere GESTLAB_API_URL e GESTLAB_AGENT_TOKEN."
        )
    intervallo = float(dati.get("GESTLAB_AGENT_INTERVAL", "5"))
    if intervallo <= 0:
        raise RuntimeError("GESTLAB_AGENT_INTERVAL deve essere maggiore di zero.")
    return url, token, intervallo


_traccia("prima dei moduli pywin32")
try:
    import servicemanager
    _traccia("servicemanager importato")
    import win32event
    import win32service
    import win32serviceutil
    _traccia("pywin32 importato")
except ImportError:  # il backend Linux non installa pywin32
    servicemanager = None
    win32event = None
    win32service = None
    win32serviceutil = None
    _traccia("pywin32 assente")


if win32serviceutil is not None:
    class GestLabPrintAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = "GestLabPrintAgent"
        _svc_display_name_ = "GestLab Local Print Agent"
        _svc_description_ = (
            "Preleva i job di stampa di GestLab e li invia alla stampante del banco."
        )

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.agent = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.agent is not None:
                self.agent.ferma()

        def SvcDoRun(self):
            _traccia("servizio in esecuzione")
            try:
                from saas.print_agent import PrintAgent

                url, token, intervallo = carica_configurazione(PERCORSO_CONFIGURAZIONE)
                self.agent = PrintAgent(url, token, intervallo)
                self.agent.run()
                _traccia("servizio fermato")
            except Exception as errore:
                _traccia(f"errore servizio: {errore}")
                raise


def avviato_dal_gestore_servizi():
    """Il gestore esegue questo file: non va reinterpretato come comando di installazione."""
    return os.path.basename(sys.executable).lower() == "pythonservice.exe"


def main():
    if avviato_dal_gestore_servizi():
        return 0
    if win32serviceutil is None:
        print("pywin32 è necessario per il servizio Windows.", file=sys.stderr)
        return 1
    win32serviceutil.HandleCommandLine(GestLabPrintAgentService)
    return 0


if __name__ == "__main__":
    sys.exit(main())
