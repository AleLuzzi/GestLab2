"""Test unitari per il modello nuovo di articoli e tracciabilita' lotti."""

import unittest
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from core.services import printing as printing_service
from saas.repositories import tracciabilita_repo
from saas.main import (
    lista_lotti_tracciati,
    registra_ingresso_tracciato,
    registra_lavorazione_tracciata,
    scheda_lotto_tracciato,
)
from saas.schemas import IngressoTracciatoCreate, LavorazioneCreate


class FakeCursor:
    def __init__(self, handler):
        self.handler = handler
        self.rowcount = 1
        self.lastrowid = 100
        self.result = []
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        self.result = self.handler(query, params)
        self.lastrowid += 1

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return self.result


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class TracciabilitaTests(unittest.TestCase):
    def test_unexpected_ingress_error_is_logged_and_returns_reference(self):
        payload = IngressoTracciatoCreate(
            data="2026-10-03",
            fornitore_id=1,
            righe=[{"articolo_id": 3, "quantita": "8.250"}],
        )

        with (
            patch(
                "saas.main.tracciabilita_repo.registra_ingresso",
                side_effect=RuntimeError("database failure"),
            ),
            patch("saas.main.logger.exception") as log_exception,
        ):
            with self.assertRaises(HTTPException) as raised:
                registra_ingresso_tracciato(payload, {"tenant_id": 42})

        self.assertEqual(raised.exception.status_code, 500)
        self.assertRegex(raised.exception.detail, r"Riferimento assistenza: [0-9a-f]{32}")
        log_exception.assert_called_once()
        self.assertIn("tenant_id=%s", log_exception.call_args.args[0])
        self.assertEqual(log_exception.call_args.args[2:], (42, 1))

    def test_progressivo_uses_separate_counter_and_returns_next_number(self):
        cursor = FakeCursor(
            lambda query, params: [(8,)] if query.startswith("SELECT prog_ven") else []
        )

        numero = tracciabilita_repo._prossimo_progressivo(cursor, 42, "V")

        self.assertEqual(numero, 9)
        self.assertTrue(
            any("UPDATE progressivi SET prog_ven" in query for query, _ in cursor.statements)
        )

    def test_lista_lotti_includes_article_category(self):
        cursor = FakeCursor(
            lambda query, params: [
                (
                    7,
                    3,
                    "Mezzena",
                    "A",
                    1,
                    "1A",
                    "2026-10-03",
                    date(2026, 12, 15),
                    "LF-8842",
                    "Italia, suino",
                    Decimal("2.50"),
                    Decimal("10"),
                    Decimal("8"),
                    "kg",
                    None,
                    None,
                    "Suino",
                    "Bio; razza: esempio",
                )
            ]
        )

        @contextmanager
        def fake_connection():
            yield FakeConnection(cursor)

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            lotti = tracciabilita_repo.lista_lotti(42, solo_disponibili=True)

        self.assertEqual(lotti[0]["categoria"], "Suino")
        self.assertEqual(lotti[0]["note_lotto"], "Bio; razza: esempio")
        query, params = cursor.statements[0]
        self.assertIn("a.categoria", query)
        self.assertIn("AND l.quantita_disponibile > 0", query)
        self.assertEqual(params, (42,))

    def test_lista_lotti_filters_by_inclusive_date_range(self):
        cursor = FakeCursor(lambda query, params: [])

        @contextmanager
        def fake_connection():
            yield FakeConnection(cursor)

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            tracciabilita_repo.lista_lotti(
                42,
                data_dal="2026-10-01",
                data_al="2026-10-31",
            )

        query, params = cursor.statements[0]
        self.assertIn("AND l.data_creazione >= %s", query)
        self.assertIn("AND l.data_creazione <= %s", query)
        self.assertEqual(params, (42, "2026-10-01", "2026-10-31"))

    def test_lista_lotti_endpoint_rejects_reversed_date_range(self):
        with self.assertRaises(HTTPException) as raised:
            lista_lotti_tracciati(
                data_dal=date(2026, 10, 31),
                data_al=date(2026, 10, 1),
                user={"tenant_id": 42},
            )

        self.assertEqual(raised.exception.status_code, 422)

    def test_scheda_lotto_pdf_includes_tenant_scoped_source_lot(self):
        lotto_prodotto = {
            "id": 8,
            "codice_lotto": "8V",
            "articolo": "Preparato",
            "tipo_lotto": "V",
            "data_creazione": "2026-10-05",
            "quantita_iniziale": "4.000",
            "quantita_disponibile": "3.000",
            "unita_misura": "kg",
            "lavorazione": {
                "data": "2026-10-05",
                "descrizione": "Preparazione",
                "operatore": "Operatore",
                "input": [{"lotto_id": 3, "quantita": "2.500"}],
            },
        }
        lotto_ingresso = {
            "id": 3,
            "codice_lotto": "3A",
            "articolo": "Carne",
            "tipo_lotto": "A",
            "data_creazione": "2026-10-01",
            "quantita_iniziale": "10.000",
            "quantita_disponibile": "7.500",
            "unita_misura": "kg",
            "origine": "Italia",
            "lotto_fornitore": "FORN-42",
            "documento_ingresso": {
                "data": "2026-10-01",
                "numero_ddt": "DDT-42",
                "fornitore": "Fornitore di prova",
            },
            "lavorazione": None,
        }

        with (
            patch(
                "saas.main.tracciabilita_repo.dettaglio_lotto",
                side_effect=[lotto_prodotto, lotto_ingresso],
            ) as dettaglio_lotto,
            patch(
                "saas.main.printing_service.genera_scheda_lotto_pdf",
                wraps=printing_service.genera_scheda_lotto_pdf,
            ) as genera_pdf,
        ):
            response = scheda_lotto_tracciato(8, {"tenant_id": 42})

        self.assertEqual(response.media_type, "application/pdf")
        self.assertTrue(response.body.startswith(b"%PDF"))
        self.assertEqual(
            [call.args for call in dettaglio_lotto.call_args_list],
            [(42, 8), (42, 3)],
        )
        genealogy = genera_pdf.call_args.args[1]
        self.assertEqual(
            genealogy[1]["dettaglio"]["documento_ingresso"]["numero_ddt"],
            "DDT-42",
        )
        self.assertIn('filename="scheda_lotto_8.pdf"', response.headers["content-disposition"])

    def test_ingress_rejects_lot_notes_longer_than_500_characters(self):
        with self.assertRaises(ValidationError):
            IngressoTracciatoCreate(
                data="2026-10-03",
                fornitore_id=1,
                righe=[
                    {
                        "articolo_id": 3,
                        "quantita": "8.250",
                        "note_lotto": "x" * 501,
                    }
                ],
            )

    def test_lot_detail_includes_descriptive_notes(self):
        row = (
            7,
            3,
            "Mezzena",
            "A",
            1,
            "1A",
            date(2026, 10, 3),
            date(2026, 12, 15),
            "LF-8842",
            "Italia, suino",
            Decimal("2.50"),
            Decimal("10"),
            Decimal("8"),
            "kg",
            55,
            None,
            date(2026, 10, 3),
            "DDT-2026-42",
            "Fornitore Esempio",
            12,
            None,
            None,
            None,
            "Bio; razza: esempio",
        )
        cursor = FakeCursor(
            lambda query, params: [row] if query.startswith("SELECT l.id, l.articolo_id") else []
        )

        @contextmanager
        def fake_connection():
            yield FakeConnection(cursor)

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            dettaglio = tracciabilita_repo.dettaglio_lotto(42, 7)

        self.assertEqual(dettaglio["note_lotto"], "Bio; razza: esempio")
        self.assertEqual(dettaglio["data_scadenza"], date(2026, 12, 15))
        self.assertEqual(dettaglio["lotto_fornitore"], "LF-8842")
        self.assertEqual(dettaglio["origine"], "Italia, suino")
        self.assertEqual(dettaglio["temperatura_ingresso"], "2.50")
        self.assertEqual(
            dettaglio["documento_ingresso"],
            {
                "id": 55,
                "data": date(2026, 10, 3),
                "numero_ddt": "DDT-2026-42",
                "fornitore": "Fornitore Esempio",
                "fornitore_id": 12,
            },
        )
        self.assertIn("l.note_lotto", cursor.statements[0][0])

    def test_ingress_rejects_both_expiration_and_best_before_dates(self):
        with self.assertRaises(ValidationError):
            IngressoTracciatoCreate(
                data="2026-10-03",
                fornitore_id=1,
                righe=[
                    {
                        "articolo_id": 3,
                        "quantita": "8.250",
                        "data_scadenza": "2026-12-15",
                        "data_tmc": "2026-12-20",
                    }
                ],
            )

    def test_lot_detail_includes_forward_work_genealogy(self):
        lotto_row = [None] * 25
        lotto_row[0] = 7
        lotto_row[1] = 3
        lotto_row[2] = "Mezzena"
        lotto_row[3] = "A"
        lotto_row[4] = 1
        lotto_row[5] = "1A"
        lotto_row[6] = date(2026, 10, 3)
        lotto_row[11] = Decimal("10")
        lotto_row[12] = Decimal("8")
        lotto_row[13] = "kg"
        cursor = FakeCursor(
            lambda query, params: (
                [tuple(lotto_row)]
                if query.startswith("SELECT l.id, l.articolo_id")
                else [
                    (
                        20,
                        date(2026, 10, 4),
                        "Preparazione",
                        "Mario Rossi",
                        9,
                        "1V",
                        "Salsiccia",
                        Decimal("7.500"),
                        "kg",
                    )
                ]
                if query.startswith("SELECT w.id, w.data_lavorazione")
                else []
            )
        )

        @contextmanager
        def fake_connection():
            yield FakeConnection(cursor)

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            dettaglio = tracciabilita_repo.dettaglio_lotto(42, 7)

        self.assertEqual(
            dettaglio["lavorazioni_successive"],
            [
                {
                    "id": 20,
                    "data": date(2026, 10, 4),
                    "descrizione": "Preparazione",
                    "operatore": "Mario Rossi",
                    "output": [
                        {
                            "lotto_id": 9,
                            "codice_lotto": "1V",
                            "articolo": "Salsiccia",
                            "quantita": "7.500",
                            "unita_misura": "kg",
                        }
                    ],
                }
            ],
        )
        forward_query, params = cursor.statements[2]
        self.assertIn("li.tenant_id = %s AND li.lotto_id = %s", forward_query)
        self.assertEqual(params, (42, 7))

    def test_work_output_rejects_both_expiration_and_best_before_dates(self):
        with self.assertRaises(ValidationError):
            LavorazioneCreate(
                data="2026-10-03",
                operatore_id=5,
                input=[{"lotto_id": 1, "quantita": "2.500"}],
                output=[
                    {
                        "articolo_id": 2,
                        "quantita": "1.250",
                        "data_scadenza": "2026-12-15",
                        "data_tmc": "2026-12-20",
                    }
                ],
            )

    def test_lot_detail_exposes_recipe_ingredients_and_allergens_for_label(self):
            lotto_row = [None] * 27
            lotto_row[0] = 9
            lotto_row[1] = 3
            lotto_row[2] = "Salsiccia"
            lotto_row[15] = 20
            lotto_row[26] = 17

            def handle(query, params):
                if query.startswith("SELECT l.id, l.articolo_id"):
                    return [tuple(lotto_row)]
                if query.startswith("SELECT nome, istruzioni_conservazione FROM ricette"):
                    return [("Salsiccia fresca", "Conservare al freddo")]
                if query.startswith("SELECT a.nome FROM ricetta_ingredienti"):
                    return [("Carne",), ("Sale",)]
                if query.startswith("SELECT codice FROM ricetta_allergeni"):
                    return [("latte",)]
                return []

            cursor = FakeCursor(handle)

            @contextmanager
            def fake_connection():
                yield FakeConnection(cursor)

            with patch.object(tracciabilita_repo, "connection", fake_connection):
                dettaglio = tracciabilita_repo.dettaglio_lotto(42, 9)

            self.assertEqual(
                dettaglio["dati_etichetta"],
                {
                    "ricetta_id": 17,
                    "ricetta_nome": "Salsiccia fresca",
                    "ingredienti": "Carne, Sale",
                    "allergeni": ["latte"],
                    "conservazione": "Conservare al freddo",
                },
            )

    def test_progressivo_drains_locked_select_before_updating(self):
        class FetchAllCursor(FakeCursor):
            def fetchone(self):
                raise AssertionError(
                    "Il result set del progressivo deve essere letto interamente."
                )

        cursor = FetchAllCursor(
            lambda query, params: [(8,)] if query.startswith("SELECT prog_acq") else []
        )

        numero = tracciabilita_repo._prossimo_progressivo(cursor, 42, "A")

        self.assertEqual(numero, 9)
        self.assertTrue(
            any("UPDATE progressivi SET prog_acq" in query for query, _ in cursor.statements)
        )

    def test_input_schema_requires_at_least_one_input_and_output(self):
        payload = LavorazioneCreate(
            data="2026-10-03",
            operatore_id=5,
            input=[{"lotto_id": 1, "quantita": "2.500"}],
            output=[{"articolo_id": 2, "quantita": "1.250"}],
        )
        self.assertEqual(payload.input[0].quantita, Decimal("2.500"))

        with self.assertRaises(ValueError):
            LavorazioneCreate(
                data="2026-10-03",
                input=[{"lotto_id": 1, "quantita": "2.500"}],
                output=[{"articolo_id": 2, "quantita": "1.250"}],
            )

        with self.assertRaises(ValueError):
            LavorazioneCreate(
                data="2026-10-03",
                input=[],
                output=[{"articolo_id": 2, "quantita": "1"}],
            )

    def test_ingress_schema_rejects_non_positive_quantities(self):
        with self.assertRaises(ValueError):
            IngressoTracciatoCreate(
                data="2026-10-03",
                fornitore_id=1,
                righe=[{"articolo_id": 1, "quantita": "0"}],
            )

    def test_incoming_creates_A_lot_and_stock_movement_atomically(self):
        def handle(query, params):
            if query.startswith("SELECT s.id, s.denominazione FROM soggetti s"):
                return [(1, "Fornitore")]
            if query.startswith("SELECT id, unita_misura FROM articoli"):
                return [(3, "kg")]
            if query.startswith("SELECT prog_acq"):
                return [(6,)]
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.registra_ingresso(
                tenant_id=42,
                data="2026-10-03",
                numero_ddt="DDT-1",
                fornitore_id=1,
                righe=[
                    type(
                        "Riga",
                        (),
                        {"articolo_id": 3, "quantita": Decimal("8.250")},
                    )()
                ],
            )

        self.assertEqual(result["lotti"][0]["codice_lotto"], "7A")
        lotto_insert = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("INSERT INTO lotti")
        )
        self.assertEqual(lotto_insert[0].count("%s"), len(lotto_insert[1]))
        self.assertEqual(lotto_insert[1][-1], result["documento_ingresso_id"])
        self.assertTrue(
            any("VALUES (%s, %s, 'INGRESSO'" in query for query, _ in cursor.statements)
        )
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)
        document_insert = next(
            (params for query, params in cursor.statements
             if query.startswith("INSERT INTO documenti_ingresso")),
            None,
        )
        self.assertEqual(document_insert[3:], ("Fornitore", 1))

    def test_incoming_rejects_supplier_outside_tenant_or_without_permission(self):
        cursor = FakeCursor(lambda _query, _params: [])
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.FornitoreNonValido):
                tracciabilita_repo.registra_ingresso(
                    tenant_id=42,
                    data="2026-10-03",
                    numero_ddt="DDT-1",
                    fornitore_id=1,
                    righe=[
                        type(
                            "Riga",
                            (),
                            {"articolo_id": 3, "quantita": Decimal("8.250")},
                        )()
                    ],
                )

        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_work_creates_V_lots_and_consumption_ledger(self):
        def handle(query, params):
            if query.startswith("SELECT nome, cognome FROM dipendenti"):
                return [("Ada", "Lovelace")]
            if query.startswith(
                "SELECT l.id, l.quantita_disponibile, a.utilizzabile_come_input"
            ):
                return [(7, Decimal("5.000"), True, date(2026, 12, 1), None, date(2026, 11, 7))]
            if query.startswith("SELECT id, unita_misura FROM articoli"):
                return [(9, "kg")]
            if query.startswith("SELECT articolo_id FROM ricette"):
                return [(9,)]
            if query.startswith("SELECT prog_ven"):
                return [(10,)]
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.registra_lavorazione(
                tenant_id=42,
                data="2026-10-03",
                descrizione="Trasformazione",
                operatore_id=5,
                ricetta_id=17,
                input_lavorazione=[
                    type("Input", (), {"lotto_id": 7, "quantita": Decimal("2")})()
                ],
                output=[
                    type(
                        "Output",
                        (),
                        {
                            "articolo_id": 9,
                            "quantita": Decimal("1.5"),
                            "origine": "Italia, suino",
                            "data_scadenza": date(2026, 12, 20),
                            "data_tmc": None,
                        },
                    )()
                ],
                scarti=[
                    type(
                        "Scarto",
                        (),
                        {
                            "descrizione": "Rifilatura",
                            "quantita": Decimal("0.1"),
                            "unita_misura": "kg",
                        },
                    )()
                ],
            )

        self.assertEqual(result["lotti"][0]["codice_lotto"], "11V")
        self.assertTrue(
            any(
                "operatore_id, operatore" in query
                and params[-3:] == (5, "Ada Lovelace", 17)
                for query, params in cursor.statements
            )
        )
        self.assertTrue(
            any("VALUES (%s, %s, 'CONSUMO'" in query for query, _ in cursor.statements)
        )
        self.assertTrue(
            any("INSERT INTO lavorazione_scarto" in query for query, _ in cursor.statements)
        )
        output_insert = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("INSERT INTO lotti")
        )
        self.assertIn("data_scadenza, data_tmc, origine", output_insert[0])
        self.assertEqual(
            output_insert[1][5:8],
            (date(2026, 12, 20), None, "Italia, suino"),
        )
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_work_rolls_back_stock_update_if_movement_insert_fails(self):
        def handle(query, params):
            if query.startswith("SELECT nome, cognome FROM dipendenti"):
                return [("Ada", "Lovelace")]
            if query.startswith(
                "SELECT l.id, l.quantita_disponibile, a.utilizzabile_come_input"
            ):
                return [(7, Decimal("5.000"), True)]
            if query.startswith("SELECT id, unita_misura FROM articoli"):
                return [(9, "kg")]
            if query.startswith("INSERT INTO movimenti_lotto"):
                raise RuntimeError("movement insert failed")
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaisesRegex(RuntimeError, "movement insert failed"):
                tracciabilita_repo.registra_lavorazione(
                    tenant_id=42,
                    data="2026-10-03",
                    descrizione="Trasformazione",
                    operatore_id=5,
                    input_lavorazione=[
                        type("Input", (), {"lotto_id": 7, "quantita": Decimal("2")})()
                    ],
                    output=[
                        type("Output", (), {"articolo_id": 9, "quantita": Decimal("1")})()
                    ],
                    scarti=[],
                )

        self.assertTrue(
            any("UPDATE lotti SET quantita_disponibile" in query for query, _ in cursor.statements)
        )
        self.assertTrue(
            any("INSERT INTO movimenti_lotto" in query for query, _ in cursor.statements)
        )
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_work_rejects_operator_outside_tenant(self):
        cursor = FakeCursor(lambda query, params: [])
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.DipendenteNonTrovato):
                tracciabilita_repo.registra_lavorazione(
                    tenant_id=42,
                    data="2026-10-03",
                    descrizione="Trasformazione",
                    operatore_id=5,
                    input_lavorazione=[
                        type("Input", (), {"lotto_id": 7, "quantita": Decimal("2")})()
                    ],
                    output=[
                        type("Output", (), {"articolo_id": 9, "quantita": Decimal("1")})()
                    ],
                    scarti=[],
                )

        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)
        self.assertFalse(any("INSERT INTO lavorazioni" in query for query, _ in cursor.statements))

    def test_work_rolls_back_if_requested_quantity_exceeds_stock(self):
        def handle(query, params):
            if query.startswith("SELECT nome, cognome FROM dipendenti"):
                return [("Ada", "Lovelace")]
            if query.startswith(
                "SELECT l.id, l.quantita_disponibile, a.utilizzabile_come_input"
            ):
                return [(7, Decimal("1.500"), True)]
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.GiacenzaInsufficiente):
                tracciabilita_repo.registra_lavorazione(
                    tenant_id=42,
                    data="2026-10-03",
                    descrizione="Trasformazione",
                    operatore_id=5,
                    input_lavorazione=[
                        type("Input", (), {"lotto_id": 7, "quantita": Decimal("2")})()
                    ],
                    output=[
                        type("Output", (), {"articolo_id": 4, "quantita": Decimal("1")})()
                    ],
                    scarti=[],
                )

        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)
        self.assertFalse(any("INSERT INTO lavorazioni" in query for query, _ in cursor.statements))

    def test_work_rejects_input_article_not_enabled_for_processing(self):
        def handle(query, params):
            if query.startswith("SELECT nome, cognome FROM dipendenti"):
                return [("Ada", "Lovelace")]
            if query.startswith(
                "SELECT l.id, l.quantita_disponibile, a.utilizzabile_come_input"
            ):
                return [(7, Decimal("5.000"), False)]
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.ArticoloNonUtilizzabileComeInput):
                tracciabilita_repo.registra_lavorazione(
                    tenant_id=42,
                    data="2026-10-03",
                    descrizione="Trasformazione",
                    operatore_id=5,
                    input_lavorazione=[
                        type("Input", (), {"lotto_id": 7, "quantita": Decimal("2")})()
                    ],
                    output=[
                        type("Output", (), {"articolo_id": 9, "quantita": Decimal("1")})()
                    ],
                    scarti=[],
                )

        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_work_rejects_lot_after_expiration(self):
        oggi = date(2026, 11, 7)

        def handle(query, params):
            if query.startswith("SELECT nome, cognome FROM dipendenti"):
                return [("Ada", "Lovelace")]
            if query.startswith(
                "SELECT l.id, l.quantita_disponibile, a.utilizzabile_come_input"
            ):
                return [(7, Decimal("5.000"), True, date(2026, 11, 6), None, oggi)]
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.LottoScaduto):
                tracciabilita_repo.registra_lavorazione(
                    tenant_id=42,
                    data=oggi,
                    descrizione="Trasformazione",
                    operatore_id=5,
                    input_lavorazione=[
                        type("Input", (), {"lotto_id": 7, "quantita": Decimal("2")})()
                    ],
                    output=[
                        type(
                            "Output",
                            (),
                            {"articolo_id": 9, "quantita": Decimal("1")},
                        )()
                    ],
                    scarti=[],
                )

        self.assertEqual(conn.rollbacks, 1)
        self.assertFalse(
            any(query.startswith("INSERT INTO lavorazioni") for query, _ in cursor.statements)
        )

    def test_work_requires_confirmation_for_expired_best_before(self):
        oggi = date(2026, 11, 7)

        def handle(query, params):
            if query.startswith("SELECT nome, cognome FROM dipendenti"):
                return [("Ada", "Lovelace")]
            if query.startswith(
                "SELECT l.id, l.quantita_disponibile, a.utilizzabile_come_input"
            ):
                return [(7, Decimal("5.000"), True, None, date(2026, 11, 6), oggi)]
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.ConfermaTmcScadutoRichiesta):
                tracciabilita_repo.registra_lavorazione(
                    tenant_id=42,
                    data=oggi,
                    descrizione="Trasformazione",
                    operatore_id=5,
                    input_lavorazione=[
                        type("Input", (), {"lotto_id": 7, "quantita": Decimal("2")})()
                    ],
                    output=[
                        type(
                            "Output",
                            (),
                            {"articolo_id": 9, "quantita": Decimal("1")},
                        )()
                    ],
                    scarti=[],
                )

        self.assertEqual(conn.rollbacks, 1)
        self.assertFalse(
            any(query.startswith("INSERT INTO lavorazioni") for query, _ in cursor.statements)
        )

    def test_work_uses_expired_best_before_only_after_confirmation(self):
        oggi = date(2026, 11, 7)

        def handle(query, params):
            if query.startswith("SELECT nome, cognome FROM dipendenti"):
                return [("Ada", "Lovelace")]
            if query.startswith(
                "SELECT l.id, l.quantita_disponibile, a.utilizzabile_come_input"
            ):
                return [(7, Decimal("5.000"), True, None, date(2026, 11, 6), oggi)]
            if query.startswith("SELECT id, unita_misura FROM articoli"):
                return [(9, "kg")]
            if query.startswith("SELECT prog_ven"):
                return [(10,)]
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            tracciabilita_repo.registra_lavorazione(
                tenant_id=42,
                data=oggi,
                descrizione="Trasformazione",
                operatore_id=5,
                input_lavorazione=[
                    type(
                        "Input",
                        (),
                        {
                            "lotto_id": 7,
                            "quantita": Decimal("2"),
                            "conferma_tmc_scaduto": True,
                        },
                    )()
                ],
                output=[
                    type(
                        "Output",
                        (),
                        {
                            "articolo_id": 9,
                            "quantita": Decimal("1"),
                            "data_tmc": date(2026, 12, 1),
                            "data_scadenza": None,
                            "origine": None,
                        },
                    )()
                ],
                scarti=[],
            )

        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)
        output_insert = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("INSERT INTO lotti")
        )
        self.assertEqual(output_insert[0].count("%s"), len(output_insert[1]))
        self.assertEqual(output_insert[1][6], date(2026, 12, 1))
        work_output_insert = next(
            params
            for query, params in cursor.statements
            if query.startswith("INSERT INTO lavorazione_output")
        )
        self.assertEqual(output_insert[1][-1], work_output_insert[1])

    def test_work_endpoint_maps_expiration_rules_to_conflict(self):
        payload = LavorazioneCreate(
            data="2026-10-03",
            operatore_id=5,
            input=[{"lotto_id": 7, "quantita": "2"}],
            output=[{"articolo_id": 9, "quantita": "1"}],
        )

        with patch.object(
            tracciabilita_repo,
            "registra_lavorazione",
            side_effect=tracciabilita_repo.LottoScaduto(
                "Il lotto 7 ha una data di scadenza superata."
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                registra_lavorazione_tracciata(payload, {"tenant_id": 42})

        self.assertEqual(raised.exception.status_code, 409)
    def test_work_endpoint_returns_validation_error_for_disabled_input_article(self):
        payload = LavorazioneCreate(
            data="2026-10-03",
            operatore_id=5,
            input=[{"lotto_id": 7, "quantita": "2"}],
            output=[{"articolo_id": 9, "quantita": "1"}],
        )

        with patch.object(
            tracciabilita_repo,
            "registra_lavorazione",
            side_effect=tracciabilita_repo.ArticoloNonUtilizzabileComeInput(
                "Articolo non abilitato come input."
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                registra_lavorazione_tracciata(payload, {"tenant_id": 42})

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "Articolo non abilitato come input.")

    def test_ingress_keeps_lotto_metadata_for_scadenza_and_origin(self):
        def handle(query, params):
            if query.startswith("SELECT s.id, s.denominazione FROM soggetti s"):
                return [(1, "Fornitore Beta")]
            if query.startswith("SELECT id, unita_misura FROM articoli"):
                return [(3, "kg")]
            if query.startswith("SELECT prog_acq"):
                return [(6,)]
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            tracciabilita_repo.registra_ingresso(
                tenant_id=42,
                data="2026-10-03",
                numero_ddt="DDT-42",
                fornitore_id=1,
                righe=[
                    type(
                        "Riga",
                        (),
                        {
                            "articolo_id": 3,
                            "quantita": Decimal("8.250"),
                            "lotto_fornitore": "LF-8842",
                            "origine": "Italia, suino",
                            "data_scadenza": None,
                            "data_tmc": date(2026, 12, 15),
                            "temperatura_ingresso": Decimal("2.50"),
                            "note_lotto": "Bio; razza: esempio",
                        },
                    )()
                ],
            )

        insert_query = next(
            query for query, _ in cursor.statements if "INSERT INTO lotti" in query
        )
        insert_params = next(
            params for query, params in cursor.statements if "INSERT INTO lotti" in query
        )
        self.assertIn("data_scadenza", insert_query)
        self.assertIn("data_tmc", insert_query)
        self.assertIn("lotto_fornitore", insert_query)
        self.assertIn("origine", insert_query)
        self.assertIn("temperatura_ingresso", insert_query)
        self.assertIn("note_lotto", insert_query)
        self.assertEqual(
            insert_params[5:11],
            (
                None,
                date(2026, 12, 15),
                "LF-8842",
                "Italia, suino",
                Decimal("2.50"),
                "Bio; razza: esempio",
            ),
        )


if __name__ == "__main__":
    unittest.main()
