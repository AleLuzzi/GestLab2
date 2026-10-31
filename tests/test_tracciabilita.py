"""Test unitari per il modello nuovo di articoli e tracciabilita' lotti."""

import unittest
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from saas.repositories import tracciabilita_repo
from saas.main import (
    lista_lotti_tracciati,
    registra_ingresso_tracciato,
    registra_lavorazione_tracciata,
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
                (7, 3, "Mezzena", "A", 1, "1A", "2026-10-03", Decimal("10"),
                 Decimal("8"), "kg", None, None, "Suino")
            ]
        )

        @contextmanager
        def fake_connection():
            yield FakeConnection(cursor)

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            lotti = tracciabilita_repo.lista_lotti(42, solo_disponibili=True)

        self.assertEqual(lotti[0]["categoria"], "Suino")
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
                return [(7, Decimal("5.000"), True)]
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
            result = tracciabilita_repo.registra_lavorazione(
                tenant_id=42,
                data="2026-10-03",
                descrizione="Trasformazione",
                operatore_id=5,
                input_lavorazione=[
                    type("Input", (), {"lotto_id": 7, "quantita": Decimal("2")})()
                ],
                output=[
                    type("Output", (), {"articolo_id": 9, "quantita": Decimal("1.5")})()
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
                "operatore_id, operatore" in query and params[-2:] == (5, "Ada Lovelace")
                for query, params in cursor.statements
            )
        )
        self.assertTrue(
            any("VALUES (%s, %s, 'CONSUMO'" in query for query, _ in cursor.statements)
        )
        self.assertTrue(
            any("INSERT INTO lavorazione_scarto" in query for query, _ in cursor.statements)
        )
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

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
        self.assertFalse(any("INSERT INTO lavorazioni" in query for query, _ in cursor.statements))

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


if __name__ == "__main__":
    unittest.main()
