"""Collaudo del flusso pilota descritto in MANUALE_UTENTE.md (§ 3–7).

- Allinea i testi del manuale con la console web.
- Su database sacrificabile, un utente operatore completa ingresso → lavorazione
  → etichetta → vendita DDT → genealogia/PDF (stessi endpoint della UI).
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MANUALE = ROOT / "docs_migrazione" / "MANUALE_UTENTE.md"

# Pulsanti e voci citate nel percorso pilota (manuale § 3–7).
PERCORSO_UI = (
    "Ingresso merce",
    "Conferma ingresso",
    "Continua agli articoli",
    "Aggiungi al riepilogo",
    "Vai al riepilogo",
    "Tracciabilità",
    "Lavorazione",
    "Precompila input FEFO",
    "Registra lavorazione",
    "Stampa",
    "Etichetta",
    "Genera etichetta (PDF)",
    "Vendite",
    "Registra vendita",
    "Traccia",
    "Scarica scheda PDF",
)

DICITURA_NON_FISCALE_CONSOLE = (
    "Documento non fiscale — non sostituisce lo scontrino del registratore telematico"
)


class ManualeConsoleAllineamentoTests(unittest.TestCase):
    def test_i_testi_del_percorso_pilota_compaiono_in_console(self):
        manuale = MANUALE.read_text(encoding="utf-8")
        pagina = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        js_blob = " ".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "web" / "js").rglob("*.js")
        )
        console = pagina + js_blob
        for voce in PERCORSO_UI:
            with self.subTest(voce=voce):
                self.assertIn(voce, manuale, "Voce attesa nel manuale")
                self.assertIn(voce, console, f"Testo «{voce}» assente dalla console")
        self.assertIn(
            "non sostituisce lo scontrino del registratore telematico",
            manuale,
        )
        self.assertIn(DICITURA_NON_FISCALE_CONSOLE, console)

    def test_il_manuale_non_rimanda_a_istruzioni_sviluppo_nel_percorso_operativo(self):
        manuale = MANUALE.read_text(encoding="utf-8")
        sezioni_operative = manuale.split("## 3. Ingresso merce", 1)[1]
        self.assertNotIn("python -m", sezioni_operative.lower())
        self.assertNotIn("config.ini", sezioni_operative.lower())
        self.assertNotIn("POST /api", sezioni_operative)


def _prepara_laboratorio(tenant_id: int):
    """Configurazione § 2 (admin) prima dell'operatore di collaudo."""
    from core.repositories import soggetti as soggetti_repo
    from core.services.dipendenti import crea_dipendente
    from saas import auth
    from saas.repositories import tenant_repo, tracciabilita_repo
    from saas.schemas import RicettaIngredienteCreate

    arts = {a["codice"]: a for a in tracciabilita_repo.lista_articoli(tenant_id)}
    pancia = arts["SUI-PANCIA"]["id"]
    salsiccia = arts["PREP-SALSICCIA"]["id"]
    art_sal = arts["PREP-SALSICCIA"]
    tracciabilita_repo.aggiorna_articolo(
        tenant_id,
        salsiccia,
        art_sal["codice"],
        art_sal["nome"],
        art_sal["categoria"],
        art_sal["unita_misura"],
        True,
        utilizzabile_come_input=False,
        prezzo_unitario=Decimal("10.90"),
        prezzo_impostato=True,
    )

    fornitore = soggetti_repo.crea(
        tenant_id,
        {
            "denominazione": "Fornitore collaudo manuale",
            "tipo_soggetto": "azienda",
            "ruolo_fornitore": True,
            "flag1_ing_merce": True,
            "attivo": True,
        },
    )
    cliente = soggetti_repo.crea(
        tenant_id,
        {
            "denominazione": "Cliente collaudo manuale",
            "tipo_soggetto": "azienda",
            "ruolo_cliente": True,
            "attivo": True,
        },
    )
    dip = crea_dipendente("Operatore", tenant_id=tenant_id, cognome="Collaudo")
    ing = RicettaIngredienteCreate(
        articolo_id=pancia,
        tipo_quantita="quantita",
        valore=Decimal("0.800"),
        obbligatorio=True,
    )
    ricetta = tracciabilita_repo.crea_ricetta(
        tenant_id,
        "Salsicce fresche collaudo",
        salsiccia,
        Decimal("1.000"),
        Decimal("0"),
        ingredienti=[ing],
        allergeni=["sedano", "solfiti"],
        giorni_vita=4,
        istruzioni_conservazione="conservare in frigo a 4 gradi",
    )
    operatore_email = "operatore.collaudo.manuale@example.com"
    tenant_repo.crea_utente(
        tenant_id,
        operatore_email,
        auth.hash_password("OperatoreCollaudo1"),
        "operatore",
    )
    return {
        "pancia_id": pancia,
        "salsiccia_id": salsiccia,
        "fornitore_id": fornitore["id"],
        "cliente_id": cliente["id"],
        "operatore_id": dip.id,
        "ricetta_id": ricetta["id"],
        "operatore_email": operatore_email,
        "prezzo": Decimal("10.90"),
    }


def esegui_flusso_operatore(utente: dict, setup: dict) -> dict:
    """Percorso manuale § 3–7 tramite handler FastAPI (stessi endpoint della console)."""
    from saas.main import (
        crea_vendita_completa,
        dettaglio_lotto_tracciato,
        genera_ddt_vendita,
        genera_etichetta,
        registra_ingresso_tracciato,
        registra_lavorazione_tracciata,
        scheda_lotto_tracciato,
    )
    from saas.schemas import (
        EtichettaCreate,
        IngressoTracciatoCreate,
        IngressoTracciatoRigaCreate,
        LavorazioneCreate,
        LavorazioneInputCreate,
        LavorazioneOutputCreate,
        LavorazioneScartoCreate,
        VenditaCompletaCreate,
        VenditaRigaCreate,
    )

    oggi = date.today()
    scadenza_ingresso = oggi + timedelta(days=30)
    scadenza_prodotto = oggi + timedelta(days=3)

    # § 3 Ingresso
    ing = registra_ingresso_tracciato(
        IngressoTracciatoCreate(
            data=oggi,
            numero_ddt="MANUALE-COLLAUDO",
            fornitore_id=setup["fornitore_id"],
            righe=[
                IngressoTracciatoRigaCreate(
                    articolo_id=setup["pancia_id"],
                    quantita=Decimal("0.500"),
                    origine="Italia",
                    data_scadenza=scadenza_ingresso,
                    temperatura_ingresso=Decimal("2.00"),
                )
            ],
        ),
        utente,
    )
    lotto_a_id = ing["lotti"][0]["id"]

    # § 4 Lavorazione
    lav = registra_lavorazione_tracciata(
        LavorazioneCreate(
            data=oggi,
            descrizione="Collaudo manuale",
            operatore_id=setup["operatore_id"],
            ricetta_id=setup["ricetta_id"],
            input=[
                LavorazioneInputCreate(lotto_id=lotto_a_id, quantita=Decimal("0.100"))
            ],
            output=[
                LavorazioneOutputCreate(
                    articolo_id=setup["salsiccia_id"],
                    quantita=Decimal("0.050"),
                    origine="Italia",
                    data_scadenza=scadenza_prodotto,
                )
            ],
            scarti=[
                LavorazioneScartoCreate(
                    descrizione="Calo di lavorazione",
                    quantita=Decimal("0.050"),
                    unita_misura="kg",
                )
            ],
        ),
        utente,
    )
    lotto_v_id = lav["lotti"][0]["id"]

    # § 5 Etichetta PDF
    etic = genera_etichetta(
        EtichettaCreate(lotto_id=lotto_v_id, peso="0.050"),
        utente,
    )
    assert etic.body.startswith(b"%PDF")

    # § 6 Vendita DDT
    vend = crea_vendita_completa(
        VenditaCompletaCreate(
            data=oggi,
            cliente_id=setup["cliente_id"],
            tipo_documento="DDT",
            righe=[
                VenditaRigaCreate(
                    lotto_id=lotto_v_id,
                    articolo_id=setup["salsiccia_id"],
                    quantita=Decimal("0.020"),
                    unita_misura="kg",
                    prezzo_unitario=setup["prezzo"],
                )
            ],
        ),
        utente,
    )
    vendita_id = vend["id"]
    ddt = genera_ddt_vendita(vendita_id, utente)
    assert ddt.body.startswith(b"%PDF")

    # § 7 Genealogia + scheda PDF
    t0 = time.perf_counter()
    dettaglio = dettaglio_lotto_tracciato(lotto_v_id, utente)
    input_lotti = (dettaglio.get("lavorazione") or {}).get("input") or []
    assert input_lotti, "Mancano i lotti input nella lavorazione"
    lotto_a_id_gene = input_lotti[0]["lotto_id"]
    origine = dettaglio_lotto_tracciato(lotto_a_id_gene, utente)
    doc = origine.get("documento_ingresso") or {}
    assert doc.get("numero_ddt") == "MANUALE-COLLAUDO"
    assert doc.get("fornitore") == "Fornitore collaudo manuale"
    scheda = scheda_lotto_tracciato(lotto_v_id, utente)
    assert scheda.body.startswith(b"%PDF")
    durata = time.perf_counter() - t0
    assert durata < 60.0, "Genealogia oltre 60 secondi"

    return {
        "lotto_v_id": lotto_v_id,
        "vendita_id": vendita_id,
        "genealogia_secondi": round(durata, 2),
    }


class CollaudoOperatoreLiveTests(unittest.TestCase):
    def test_operatore_completa_il_flusso_pilota(self):
        if not os.environ.get("GESTLAB_COLLAUDO_LIVE"):
            self.skipTest("Impostare GESTLAB_COLLAUDO_LIVE=1 su DB sacrificabile")

        from saas import auth
        from saas.schemas import OnboardingRichiesta
        from saas.services.onboarding import crea_laboratorio

        dati = OnboardingRichiesta(
            nome="Collaudo manuale operatore",
            piano="basic",
            ragione_sociale="OSA Collaudo",
            indirizzo="Via Collaudo 1",
            laboratorio="Lab collaudo",
            partita_iva="12345678903",
            email="admin.collaudo.manuale@example.com",
            password="AdminCollaudo1",
            catalogo="macelleria",
        )
        esito = crea_laboratorio(dati)
        tenant_id = esito["tenant_id"]
        setup = _prepara_laboratorio(tenant_id)

        auth.verify_password(
            "OperatoreCollaudo1",
            auth.hash_password("OperatoreCollaudo1"),
        )
        utente = {
            "tenant_id": tenant_id,
            "ruolo": "operatore",
            "email": setup["operatore_email"],
        }

        risultato = esegui_flusso_operatore(utente, setup)
        self.assertLess(risultato["genealogia_secondi"], 60.0)


if __name__ == "__main__":
    unittest.main()