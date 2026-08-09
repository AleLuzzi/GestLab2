"""Local Print Agent per GestLab SaaS.

Piccolo processo che gira sul PC del punto vendita (o in cucina) e:
1. Polling periodico della coda di stampa remota (``/agent/next-job``).
2. Per ogni job accodato, genera il documento (PDF/ESC-POS) con il service
   layer del core e lo invia alla stampante fisica locale.
3. Segnala al backend l'esito (done/error).

Autenticazione: il token del dispositivo viene fornito in fase di avvio
(da config.ini, sezione ``[Stampante]``, oppure da variabile d'ambiente).

Avvio::

    python -m saas.print_agent --token <TOKEN_DISPOSITIVO> [--interval 5]

Oppure leggendo il token da ``config.ini``:

    [Stampante]
    agent_token = <TOKEN_DISPOSITIVO>
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

# Import del service layer di stampa (reusa il core applicativo).
from core.services import printing as printing_service

DEFAULT_BASE_URL = os.environ.get("GESTLAB_API_URL", "http://localhost:8000")


def _leggi_token_config():
    """Legge il token dispositivo dalla sezione [Stampante] di config.ini."""
    try:
        from core.config import get_config
        cfg = get_config()
        if "Stampante" in cfg:
            return cfg["Stampante"].get("agent_token", "")
    except Exception:
        pass
    return os.environ.get("GESTLAB_AGENT_TOKEN", "")


class PrintAgent:
    """Polling loop che scarica ed esegue i job di stampa."""

    def __init__(self, base_url, token, interval=5.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.interval = interval

    # ------------------------------------------------------------------ #
    #  HTTP helpers
    # ------------------------------------------------------------------ #
    def _get(self, path):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"[agent] HTTP {e.code} su {path}", flush=True)
            return None
        except Exception as e:
            print(f"[agent] Errore rete su {path}: {e}", flush=True)
            return None

    def _post(self, path, data=None):
        url = f"{self.base_url}{path}"
        body = json.dumps(data or {}).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"[agent] HTTP {e.code} su {path}", flush=True)
            return None
        except Exception as e:
            print(f"[agent] Errore rete su {path}: {e}", flush=True)
            return None

    # ------------------------------------------------------------------ #
    #  Esecuzione dei job
    # ------------------------------------------------------------------ #
    def _esegui_job(self, job):
        """Genera e stampa il documento per il job dato. Ritorna True se ok."""
        tipo = job.get("tipo")
        payload = job.get("payload", "")

        try:
            if tipo == "ddt":
                data = json.loads(payload)
                pdf = printing_service.genera_ddt_pdf(
                    numero=data.get("numero", ""),
                    data=data.get("data"),
                    fornitore=data.get("fornitore", ""),
                    righe=data.get("righe", []),
                )
                return self._stampa_pdf(pdf, "ddt.pdf")

            if tipo == "etichetta":
                data = json.loads(payload)
                pdf = printing_service.genera_etichetta_dymo_pdf(
                    plu=data.get("plu", ""),
                    prodotto=data.get("prodotto", ""),
                    prezzo_kg=data.get("prezzo_kg", ""),
                    ingredienti=data.get("ingredienti", ""),
                    codice=data.get("codice", ""),
                )
                return self._stampa_pdf(pdf, "etichetta.pdf")

            if tipo == "scontrino":
                data = json.loads(payload)
                escpos = printing_service.genera_scontrino_escpos(
                    testata=data.get("testata", ""),
                    righe=data.get("righe", []),
                    totale=data.get("totale", "0.00"),
                    iva=data.get("iva", "0.00"),
                )
                return self._stampa_escpos(escpos)

            print(f"[agent] Tipo job sconosciuto: {tipo}", flush=True)
            return False
        except Exception as e:
            print(f"[agent] Errore esecuzione job {job.get('id')}: {e}", flush=True)
            return False

    def _stampa_pdf(self, pdf_bytes, filename):
        """Stampa un PDF via win32 (se disponibile), altrimenti fallback file."""
        if printing_service.stampa_pdf_via_win32(pdf_bytes):
            print(f"[agent] PDF stampato ({len(pdf_bytes)} bytes)", flush=True)
            return True
        # Fallback: salva su file temporaneo
        path = os.path.join(os.path.expanduser("~"), filename)
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        print(f"[agent] Fallback: PDF salvato in {path}", flush=True)
        return True

    def _stampa_escpos(self, escpos_bytes):
        """Stampa ESC/POS via win32 raw (se disponibile), altrimenti file."""
        try:
            import win32print
            handle = win32print.OpenPrinter(win32print.GetDefaultPrinter())
            try:
                win32print.StartDocPrinter(handle, 1, ("scontrino", None, "RAW"))
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, escpos_bytes)
                win32print.EndPagePrinter(handle)
                win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
            print(f"[agent] Scontrino stampato ({len(escpos_bytes)} bytes)", flush=True)
            return True
        except Exception:
            path = os.path.join(os.path.expanduser("~"), "scontrino.bin")
            with open(path, "wb") as f:
                f.write(escpos_bytes)
            print(f"[agent] Fallback: scontrino salvato in {path}", flush=True)
            return True

    # ------------------------------------------------------------------ #
    #  Loop principale
    # ------------------------------------------------------------------ #
    def run(self):
        """Avvia il loop di polling infinito."""
        print(f"[agent] Avvio Local Print Agent -> {self.base_url}", flush=True)
        print(f"[agent] Polling ogni {self.interval}s (Ctrl+C per fermare)", flush=True)

        while True:
            try:
                resp = self._get(f"/agent/next-job?token={self.token}")
                job = (resp or {}).get("job") if resp else None

                if job:
                    job_id = job["id"]
                    ok = self._esegui_job(job)
                    if ok:
                        self._post(f"/agent/{job_id}/done", {"token": self.token})
                        print(f"[agent] Job {job_id} completato", flush=True)
                    else:
                        self._post(f"/agent/{job_id}/error", {
                            "token": self.token, "detail": "stampa fallita"
                        })
                        print(f"[agent] Job {job_id} in errore", flush=True)
                # else: nessun job; attendi il prossimo ciclo
            except KeyboardInterrupt:
                print("\n[agent] Stop richiesto dall'utente", flush=True)
                break
            except Exception as e:
                print(f"[agent] Errore loop: {e}", flush=True)

            time.sleep(self.interval)


def main():
    parser = argparse.ArgumentParser(description="Local Print Agent GestLab")
    parser.add_argument("--token", default="", help="Token dispositivo di stampa")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="URL base del backend SaaS")
    parser.add_argument("--interval", type=float, default=5.0, help="Intervallo di polling (s)")
    args = parser.parse_args()

    token = args.token or _leggi_token_config()
    if not token:
        print("ERRORE: nessun token dispositivo fornito (--token o config.ini).", flush=True)
        sys.exit(1)

    agent = PrintAgent(args.url, token, args.interval)
    try:
        agent.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
