import re
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from core.services import printing
from saas.main import aggiorna_dati_osa, genera_etichetta, leggi_dati_osa
from saas.schemas import EtichettaCreate, TenantOsaUpdate


class EtichetteTests(unittest.TestCase):
    def test_label_payload_validates_allergens_and_weight(self):
        payload = EtichettaCreate(
            lotto_id=8,
            allergeni=["latte", "glutine"],
            peso="0.250",
        )

        self.assertEqual(payload.allergeni, ["latte", "glutine"])
        self.assertEqual(str(payload.peso), "0.250")
        with self.assertRaises(ValidationError):
            EtichettaCreate(lotto_id=8, allergeni=["latte", "non_valido"])

    def test_tenant_label_uses_lot_canonical_price_and_osa_profile(self):
        lotto = {
            "id": 8,
            "articolo_id": 3,
            "articolo": "Salsiccia fresca",
            "codice_lotto": "12V",
            "data_scadenza": None,
            "data_tmc": "2026-11-18",
            "origine": "Italia",
            "unita_misura": "kg",
            "prezzo_unitario": "14.50",
        }
        profilo = {
            "ragione_sociale": "Macelleria Esempio",
            "indirizzo": "Via Roma 1, Torino",
            "laboratorio": "Laboratorio interno",
            "partita_iva": "01234567890",
        }
        payload = EtichettaCreate(
            lotto_id=8,
            prezzo_kg="999.00",
            ingredienti="carne, sale",
            allergeni=["latte"],
            conservazione="Conservare a 0-4 °C",
            peso="0.250",
        )

        with (
            patch("saas.main.tracciabilita_repo.dettaglio_lotto", return_value=lotto),
            patch("saas.main.tenant_repo.dati_osa", return_value=profilo),
            patch(
                "saas.main.printing_service.genera_etichetta_dymo_pdf",
                return_value=b"%PDF-label",
            ) as genera_pdf,
        ):
            response = genera_etichetta(
                payload, {"tenant_id": 42, "ruolo": "admin"}
            )

        self.assertEqual(response.body, b"%PDF-label")
        kwargs = genera_pdf.call_args.kwargs
        self.assertEqual(kwargs["prodotto"], "Salsiccia fresca")
        self.assertEqual(kwargs["lotto"], "12V")
        self.assertEqual(kwargs["scadenza"], "TMC: 2026-11-18")
        self.assertEqual(kwargs["prezzo_kg"], "14.50 €/kg")
        self.assertEqual(kwargs["peso"], "0.250 kg")
        self.assertEqual(kwargs["allergeni"], ["latte"])
        self.assertIn("Macelleria Esempio", kwargs["osa"])
        self.assertIn("P.IVA 01234567890", kwargs["osa"])

    def test_operator_label_uses_recipe_ingredients_and_allergens(self):
        lotto = {
            "id": 8,
            "articolo_id": 3,
            "articolo": "Salsiccia fresca",
            "codice_lotto": "12V",
            "data_scadenza": None,
            "data_tmc": None,
            "origine": "Italia",
            "unita_misura": "kg",
            "prezzo_unitario": "14.50",
            "dati_etichetta": {
                "ricetta_nome": "Salsiccia",
                "ingredienti": "Carne, Sale",
                "allergeni": ["latte"],
            },
        }
        profilo = {
            "ragione_sociale": "Macelleria Esempio",
            "indirizzo": "Via Roma 1, Torino",
            "laboratorio": "",
            "partita_iva": "",
        }
        with (
            patch("saas.main.tracciabilita_repo.dettaglio_lotto", return_value=lotto),
            patch("saas.main.tenant_repo.dati_osa", return_value=profilo),
            patch(
                "saas.main.printing_service.genera_etichetta_dymo_pdf",
                return_value=b"%PDF-label",
            ) as genera_pdf,
        ):
            genera_etichetta(
                EtichettaCreate(lotto_id=8),
                {"tenant_id": 42, "ruolo": "operatore"},
            )

        kwargs = genera_pdf.call_args.kwargs
        self.assertEqual(kwargs["ingredienti"], "Carne, Sale")
        self.assertEqual(kwargs["allergeni"], ["latte"])

    def test_operator_cannot_override_recipe_label_data(self):
        payload = EtichettaCreate(lotto_id=8, ingredienti="Override")
        with self.assertRaises(HTTPException) as raised:
            genera_etichetta(payload, {"tenant_id": 42, "ruolo": "operatore"})
        self.assertEqual(raised.exception.status_code, 403)

    def test_lot_label_requires_osa_business_name_and_site(self):
        payload = EtichettaCreate(lotto_id=8)
        with (
            patch(
                "saas.main.tracciabilita_repo.dettaglio_lotto",
                return_value={"id": 8},
            ),
            patch(
                "saas.main.tenant_repo.dati_osa",
                return_value={
                    "ragione_sociale": "",
                    "indirizzo": "",
                    "laboratorio": "",
                    "partita_iva": "",
                },
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                genera_etichetta(payload, {"tenant_id": 42})
        self.assertEqual(raised.exception.status_code, 409)

    def test_osa_profile_endpoints_are_tenant_scoped(self):
        profile = {
            "ragione_sociale": "Macelleria Esempio",
            "indirizzo": "Via Roma 1",
            "laboratorio": "Laboratorio interno",
            "partita_iva": "01234567890",
        }
        with patch("saas.main.tenant_repo.dati_osa", return_value=profile) as read:
            self.assertEqual(leggi_dati_osa({"tenant_id": 42}), profile)
        read.assert_called_once_with(42)

        payload = TenantOsaUpdate(**profile)
        with patch(
            "saas.main.tenant_repo.aggiorna_dati_osa", return_value=True
        ) as update:
            self.assertEqual(aggiorna_dati_osa(payload, {"tenant_id": 42}), profile)
        update.assert_called_once_with(42, profile)

    def test_label_pdf_contains_a_single_label_page(self):
        pdf = printing.genera_etichetta_dymo_pdf(
            plu="3",
            prodotto="Salsiccia fresca",
            prezzo_kg="14.50 €/kg",
            ingredienti="carne, sale",
            lotto="12V",
            scadenza="SCADENZA: 2026-11-18",
            allergeni=["latte"],
            conservazione="Conservare a 0-4 °C",
            osa="Macelleria Esempio\nVia Roma 1",
            peso="0.250 kg",
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), 1)
        for testo in (
            "SALSICCIA FRESCA",
            "INGREDIENTI:",
            "ALLERGENI:",
            "LATTE",
            "12V",
            "SCADENZA:",
            "CONSERVAZIONE:",
            "Macelleria Esempio",
        ):
            with self.subTest(testo=testo):
                self.assertIn(testo.encode(), pdf)


if __name__ == "__main__":
    unittest.main()
