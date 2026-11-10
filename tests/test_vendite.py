"""Test per la chiusura operativa dei lotti."""

import unittest
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from core.services import printing as printing_service
from core.services import vendite
from saas.main import (
    aggiungi_righe_vendita,
    crea_vendita,
    crea_vendita_completa,
    elenco_ddt_vendita,
    genera_ddt_vendita,
    lotti_disponibili_vendita,
)
from saas.repositories import tracciabilita_repo
from saas.services import vendite as vendite_service
from saas.schemas import (
    VenditaCompletaCreate,
    VenditaCreate,
    VenditaRigaCreate,
    VenditaRigheCreate,
)


class FakeCursor:
    def __init__(self, giacenza):
        self.giacenza = giacenza
        self.rowcount = 1
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith("SELECT quantita_disponibile"):
            self.result = (self.giacenza,) if self.giacenza is not None else None

    def fetchone(self):
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


class ChiusuraLottoTests(unittest.TestCase):
    def invoke_with_stock(self, giacenza, lotto_id=7, tenant_id=42):
        cursor = FakeCursor(giacenza)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(vendite, "connection", fake_connection):
            result = vendite.chiudi_lotto(lotto_id, tenant_id)
        return result, cursor, conn

    def test_closing_nonempty_lot_does_not_change_stock(self):
        cursor = FakeCursor(Decimal("1.250"))
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(vendite, "connection", fake_connection):
            with self.assertRaises(vendite.LottoNonEsaurito):
                vendite.chiudi_lotto(7, 42)

        self.assertFalse(any(query.startswith("UPDATE lotti") for query, _ in cursor.statements))
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_closing_depleted_lot_only_marks_it_inactive(self):
        result, cursor, conn = self.invoke_with_stock(Decimal("0.000"))

        self.assertTrue(result)
        update, params = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("UPDATE lotti")
        )
        self.assertIn("SET attivo = 0", update)
        self.assertNotIn("SET quantita_disponibile", update)
        self.assertEqual(params, (7, 42))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_closing_unknown_lot_returns_false_without_updating(self):
        result, cursor, conn = self.invoke_with_stock(None)

        self.assertFalse(result)
        self.assertFalse(any(query.startswith("UPDATE lotti") for query, _ in cursor.statements))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)


class LottiDisponibiliVenditaTests(unittest.TestCase):
    def test_repository_returns_available_lots_in_fefo_order(self):
        rows = [
            (7, 3, "Costata", "A", "A-7", "2026-12-15", Decimal("8.500"), "kg", None, Decimal("12.50")),
            (8, 3, "Costata", "V", "V-8", None, Decimal("2.000"), "kg", "2026-12-10", Decimal("12.50")),
        ]

        class FakeCursor:
            def __init__(self):
                self.query = None
                self.params = None

            def execute(self, query, params=None):
                self.query = query
                self.params = params

            def fetchall(self):
                return rows

        class FakeConnection:
            def __init__(self):
                self._cursor = FakeCursor()

            def cursor(self):
                return self._cursor

        conn = FakeConnection()

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            lotti = tracciabilita_repo.lotti_disponibili_vendita(42)

        self.assertEqual(conn._cursor.params, (42,))
        self.assertIn("a.attivo = 1", conn._cursor.query)
        self.assertIn("l.attivo = 1", conn._cursor.query)
        self.assertIn("l.quantita_disponibile > 0", conn._cursor.query)
        self.assertIn("l.data_scadenza >= CURRENT_DATE", conn._cursor.query)
        self.assertIn("COALESCE(l.data_scadenza, l.data_tmc) ASC", conn._cursor.query)
        self.assertIn("THEN 1 ELSE 0 END", conn._cursor.query)
        self.assertEqual(lotti[0]["id"], 7)
        self.assertEqual(lotti[0]["quantita_disponibile"], "8.500")
        self.assertEqual(lotti[0]["prezzo_unitario"], "12.50")
        self.assertIsNone(lotti[1]["data_scadenza"])
        self.assertEqual(lotti[1]["data_tmc"], "2026-12-10")

    def test_endpoint_uses_tenant_from_authenticated_user(self):
        expected = [{"id": 7, "codice_lotto": "A-7"}]

        with patch.object(
            vendite_service, "lotti_disponibili_vendita", return_value=expected
        ) as list_lots:
            result = lotti_disponibili_vendita({"tenant_id": 42})

        self.assertEqual(result, expected)
        list_lots.assert_called_once_with(42)


class StoricoDdtVenditaTests(unittest.TestCase):
    def test_repository_returns_tenant_scoped_ddt_history(self):
        rows = [(81, 5, date(2026, 11, 10), "Cliente Test", 2)]

        class FakeCursor:
            def execute(self, query, params=None):
                self.query = query
                self.params = params

            def fetchall(self):
                return rows

        class FakeConnection:
            def __init__(self):
                self._cursor = FakeCursor()

            def cursor(self):
                return self._cursor

        conn = FakeConnection()

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            history = tracciabilita_repo.elenco_ddt_vendita(42)

        self.assertEqual(conn._cursor.params, (42,))
        self.assertIn("v.tenant_id = %s AND v.tipo_documento = 'DDT'", conn._cursor.query)
        self.assertIn("LIMIT 100", conn._cursor.query)
        self.assertEqual(
            history,
            [{
                "id": 81,
                "numero": 5,
                "data_vendita": date(2026, 11, 10),
                "cliente": "Cliente Test",
                "numero_righe": 2,
            }],
        )

    def test_repository_loads_ddt_header_and_rows_from_persisted_sale(self):
        header = (
            81, 5, date(2026, 11, 10), "DDT",
            "Macelleria Test", "Via Roma 1", "Laboratorio", "IT123",
            "Cliente Test", "Via Verdi", "2", "00100", "Roma", "RM", "Italia", "IT456",
        )
        rows = [("Salsiccia fresca", "V-25", Decimal("1.250"), "kg")]

        class FakeCursor:
            def __init__(self):
                self.queries = []

            def execute(self, query, params=None):
                self.queries.append((query, params))

            def fetchone(self):
                return header

            def fetchall(self):
                return rows

        class FakeConnection:
            def __init__(self):
                self._cursor = FakeCursor()

            def cursor(self):
                return self._cursor

        conn = FakeConnection()

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            document = tracciabilita_repo.dettaglio_ddt_vendita(42, 81)

        self.assertIn("WHERE v.tenant_id = %s AND v.id = %s", conn._cursor.queries[0][0])
        self.assertEqual(conn._cursor.queries[0][1], (42, 81))
        self.assertIn("WHERE rv.tenant_id = %s AND rv.vendita_id = %s", conn._cursor.queries[1][0])
        self.assertEqual(conn._cursor.queries[1][1], (42, 81))
        self.assertEqual(document["mittente"]["ragione_sociale"], "Macelleria Test")
        self.assertEqual(document["destinatario"]["denominazione"], "Cliente Test")
        self.assertEqual(
            document["righe"],
            [{
                "articolo": "Salsiccia fresca",
                "lotto": "V-25",
                "quantita": "1.250",
                "unita_misura": "kg",
            }],
        )

    def test_repository_returns_none_for_sale_outside_tenant(self):
        class FakeCursor:
            def execute(self, query, params=None):
                self.query = query
                self.params = params

            def fetchone(self):
                return None

        class FakeConnection:
            def __init__(self):
                self._cursor = FakeCursor()

            def cursor(self):
                return self._cursor

        conn = FakeConnection()

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            document = tracciabilita_repo.dettaglio_ddt_vendita(42, 81)

        self.assertIsNone(document)
        self.assertEqual(conn._cursor.params, (42, 81))

    def test_history_endpoint_uses_tenant_from_authenticated_user(self):
        expected = [{"id": 81, "numero": 5}]

        with patch.object(
            vendite_service, "elenco_ddt_vendita", return_value=expected
        ) as list_ddt:
            result = elenco_ddt_vendita({"tenant_id": 42})

        self.assertEqual(result, expected)
        list_ddt.assert_called_once_with(42)

    def test_ddt_endpoint_generates_pdf_from_persisted_document(self):
        document = {
            "id": 81,
            "numero": 5,
            "data_vendita": date(2026, 11, 10),
            "tipo_documento": "DDT",
            "mittente": {
                "ragione_sociale": "Macelleria Test",
                "indirizzo": "Via Roma 1",
                "laboratorio": "",
                "partita_iva": "IT123",
            },
            "destinatario": {"denominazione": "Cliente Test"},
            "righe": [{
                "articolo": "Salsiccia fresca",
                "lotto": "V-25",
                "quantita": "1.250",
                "unita_misura": "kg",
            }],
        }

        with (
            patch.object(
                vendite_service, "dettaglio_ddt_vendita", return_value=document
            ) as get_document,
            patch(
                "saas.main.printing_service.genera_ddt_vendita_pdf",
                return_value=b"%PDF-test",
            ) as generate_pdf,
        ):
            response = genera_ddt_vendita(81, {"tenant_id": 42, "ruolo": "operatore"})

        get_document.assert_called_once_with(42, 81)
        generate_pdf.assert_called_once_with(
            numero=5,
            data="10/11/2026",
            mittente=document["mittente"],
            destinatario=document["destinatario"],
            righe=document["righe"],
        )
        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(response.body, b"%PDF-test")
        self.assertEqual(
            response.headers["content-disposition"],
            'attachment; filename="ddt_5.pdf"',
        )

    def test_reprinting_reuses_same_document_number_and_rows_without_writes(self):
        document = {
            "id": 81,
            "numero": 5,
            "data_vendita": date(2026, 11, 10),
            "tipo_documento": "DDT",
            "mittente": {"ragione_sociale": "Macelleria Test", "indirizzo": "Via Roma"},
            "destinatario": {"denominazione": "Cliente Test"},
            "righe": [{
                "articolo": "Salsiccia fresca",
                "lotto": "V-25",
                "quantita": "1.250",
                "unita_misura": "kg",
            }],
        }

        with (
            patch.object(
                vendite_service, "dettaglio_ddt_vendita", return_value=document
            ) as get_document,
            patch(
                "saas.main.printing_service.genera_ddt_vendita_pdf",
                side_effect=[b"%PDF-first", b"%PDF-reprint"],
            ) as generate_pdf,
        ):
            first = genera_ddt_vendita(81, {"tenant_id": 42, "ruolo": "operatore"})
            again = genera_ddt_vendita(81, {"tenant_id": 42, "ruolo": "operatore"})

        self.assertEqual(get_document.call_count, 2)
        self.assertEqual(generate_pdf.call_count, 2)
        self.assertEqual(first.headers["content-disposition"], again.headers["content-disposition"])
        self.assertEqual(first.headers["content-disposition"], 'attachment; filename="ddt_5.pdf"')
        self.assertEqual(
            generate_pdf.call_args_list[0].kwargs["righe"],
            generate_pdf.call_args_list[1].kwargs["righe"],
        )

    def test_endpoint_rejects_non_ddt_documents_and_tenant_misses(self):
        with patch.object(
            vendite_service,
            "dettaglio_ddt_vendita",
            return_value={"tipo_documento": "RICEVUTA"},
        ):
            with self.assertRaises(HTTPException) as error:
                genera_ddt_vendita(81, {"tenant_id": 42, "ruolo": "operatore"})
        self.assertEqual(error.exception.status_code, 409)

        with patch.object(
            vendite_service, "dettaglio_ddt_vendita", return_value=None
        ):
            with self.assertRaises(HTTPException) as error:
                genera_ddt_vendita(81, {"tenant_id": 42, "ruolo": "operatore"})
        self.assertEqual(error.exception.status_code, 404)

    def test_ddt_pdf_contains_persisted_sale_details(self):
        pdf = printing_service.genera_ddt_vendita_pdf(
            numero=5,
            data="10/11/2026",
            mittente={
                "ragione_sociale": "Macelleria Test",
                "indirizzo": "Via Roma 1",
                "laboratorio": "",
                "partita_iva": "IT123",
            },
            destinatario={
                "denominazione": "Cliente Test",
                "indirizzo": "Via Verdi",
                "numero_civico": "2",
                "cap": "00100",
                "citta": "Roma",
                "provincia": "RM",
                "paese": "Italia",
                "partita_iva": "IT456",
            },
            righe=[{
                "articolo": "Salsiccia fresca",
                "lotto": "V-25",
                "quantita": "1.250",
                "unita_misura": "kg",
            }],
        )

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)


class FakeVenditaCursor:
    def __init__(self, cliente_valido=True, numeri_per_tenant=None):
        self.cliente_valido = cliente_valido
        self.numeri_per_tenant = numeri_per_tenant or {42: 4}
        self.lastrowid = 81
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))

    def fetchone(self):
        query, params = self.statements[-1]
        if query.startswith("SELECT id FROM tenant"):
            return (params[0],)
        if query.startswith("SELECT s.id FROM soggetti"):
            return (13,) if self.cliente_valido else None
        if query.startswith("SELECT COALESCE(MAX(numero)"):
            return (self.numeri_per_tenant.get(params[0], 0),)
        return None


class CreaVenditaTests(unittest.TestCase):
    def invoke_repository(
        self, cliente_id=13, cliente_valido=True, tenant_id=42, numeri_per_tenant=None
    ):
        cursor = FakeVenditaCursor(cliente_valido, numeri_per_tenant)
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.crea_vendita(
                tenant_id,
                date(2026, 11, 10),
                cliente_id,
                "DDT",
            )
        return result, cursor, connection

    def test_creates_tenant_scoped_header_with_next_number(self):
        vendita, cursor, connection = self.invoke_repository()

        self.assertEqual(
            vendita,
            {
                "id": 81,
                "tenant_id": 42,
                "numero": 5,
                "data_vendita": date(2026, 11, 10),
                "cliente_id": 13,
                "tipo_documento": "DDT",
            },
        )
        self.assertIn("FOR UPDATE", cursor.statements[0][0])
        self.assertEqual(cursor.statements[0][1], (42,))
        self.assertIn("WHERE tenant_id = %s", cursor.statements[2][0])
        self.assertEqual(cursor.statements[2][1], (42,))
        self.assertEqual(
            cursor.statements[-1][1],
            (42, 5, date(2026, 11, 10), 13, "DDT"),
        )
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)

    def test_numbering_uses_the_current_tenants_sequence(self):
        vendita, cursor, _ = self.invoke_repository(
            tenant_id=99,
            numeri_per_tenant={42: 4, 99: 2},
        )

        self.assertEqual(vendita["tenant_id"], 99)
        self.assertEqual(vendita["numero"], 3)
        self.assertEqual(cursor.statements[2][1], (99,))
        self.assertEqual(cursor.statements[-1][1][0:2], (99, 3))

    def test_bank_receipt_does_not_require_a_customer(self):
        cursor = FakeVenditaCursor()
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            vendita = tracciabilita_repo.crea_vendita(
                42, date(2026, 11, 10), None, "RICEVUTA"
            )

        self.assertIsNone(vendita["cliente_id"])
        self.assertFalse(any("FROM soggetti s" in query for query, _ in cursor.statements))
        self.assertEqual(
            cursor.statements[-1][1],
            (42, 5, date(2026, 11, 10), None, "RICEVUTA"),
        )

    def test_invalid_customer_rolls_back(self):
        cursor = FakeVenditaCursor(cliente_valido=False)
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.ClienteVenditaNonValido):
                tracciabilita_repo.crea_vendita(
                    42, date(2026, 11, 10), 13, "DDT"
                )

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_endpoint_uses_tenant_from_authenticated_user(self):
        payload = VenditaCreate(
            data=date(2026, 11, 10),
            cliente_id=13,
            tipo_documento="DDT",
        )
        expected = {"id": 81, "tenant_id": 42, "numero": 5}

        with patch.object(
            vendite_service, "crea_vendita", return_value=expected
        ) as create:
            result = crea_vendita(payload, {"tenant_id": 42})

        self.assertEqual(result, expected)
        create.assert_called_once_with(
            tenant_id=42,
            data_vendita=payload.data,
            cliente_id=13,
            tipo_documento="DDT",
        )

    def test_endpoint_translates_invalid_customer(self):
        payload = VenditaCreate(
            data=date(2026, 11, 10),
            cliente_id=13,
            tipo_documento="DDT",
        )

        with patch.object(
            vendite_service,
            "crea_vendita",
            side_effect=tracciabilita_repo.ClienteVenditaNonValido,
        ):
            with self.assertRaises(HTTPException) as error:
                crea_vendita(payload, {"tenant_id": 42})

        self.assertEqual(error.exception.status_code, 404)

    def test_ddt_requires_a_customer(self):
        with self.assertRaises(ValueError):
            VenditaCreate(
                data=date(2026, 11, 10),
                cliente_id=None,
                tipo_documento="DDT",
            )


class CreaVenditaCompletaTests(unittest.TestCase):
    def test_endpoint_delegates_complete_sale_with_tenant_from_jwt(self):
        payload = VenditaCompletaCreate(
            data=date(2026, 11, 10),
            cliente_id=None,
            tipo_documento="RICEVUTA",
            righe=[
                VenditaRigaCreate(
                    lotto_id=7,
                    articolo_id=3,
                    quantita=Decimal("1.250"),
                    unita_misura="kg",
                    prezzo_unitario=Decimal("12.50"),
                )
            ],
        )
        expected = {"id": 81, "numero": 5, "righe": []}

        with patch.object(
            vendite_service, "crea_vendita_completa", return_value=expected
        ) as create:
            result = crea_vendita_completa(payload, {"tenant_id": 42})

        self.assertEqual(result, expected)
        create.assert_called_once_with(
            tenant_id=42,
            data_vendita=payload.data,
            cliente_id=None,
            tipo_documento="RICEVUTA",
            righe=payload.righe,
        )

    def test_endpoint_translates_insufficient_stock_to_conflict(self):
        payload = VenditaCompletaCreate(
            data=date(2026, 11, 10),
            tipo_documento="RICEVUTA",
            righe=[
                VenditaRigaCreate(
                    lotto_id=7,
                    articolo_id=3,
                    quantita=Decimal("1.250"),
                    unita_misura="kg",
                    prezzo_unitario=Decimal("12.50"),
                )
            ],
        )

        with patch.object(
            vendite_service,
            "crea_vendita_completa",
            side_effect=tracciabilita_repo.GiacenzaInsufficiente("stock"),
        ):
            with self.assertRaises(HTTPException) as error:
                crea_vendita_completa(payload, {"tenant_id": 42})

        self.assertEqual(error.exception.status_code, 409)


class FakeRigheVenditaCursor:
    def __init__(
        self,
        vendita_esistente=True,
        lotti_validi=None,
        giacenze=None,
        fail_on_movement=False,
        vendita_tenant_id=42,
        lotti_tenant_id=None,
        prezzo_articolo=Decimal("12.50"),
    ):
        self.vendita_esistente = vendita_esistente
        self.lotti_validi = lotti_validi if lotti_validi is not None else {7}
        self.giacenze = giacenze if giacenze is not None else {7: Decimal("5.000")}
        self.fail_on_movement = fail_on_movement
        self.vendita_tenant_id = vendita_tenant_id
        self.lotti_tenant_id = lotti_tenant_id if lotti_tenant_id is not None else {7: 42}
        self.prezzo_articolo = prezzo_articolo
        self.statements = []
        self.lastrowid = 100

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith("INSERT INTO movimenti_lotto") and self.fail_on_movement:
            raise RuntimeError("movement insert failed")
        if query.startswith("INSERT INTO righe_vendita"):
            self.lastrowid += 1
        if query.startswith("UPDATE lotti"):
            self.giacenze[params[3]] = params[0]

    def fetchone(self):
        query, params = self.statements[-1]
        if query.startswith("SELECT id FROM vendite"):
            return (
                (81,)
                if self.vendita_esistente and params[0] == self.vendita_tenant_id
                else None
            )
        if query.startswith("SELECT l.articolo_id, l.unita_misura"):
            lotto_id = params[1]
            if (
                params[0] != self.lotti_tenant_id.get(lotto_id)
                or lotto_id not in self.lotti_validi
                or lotto_id not in self.giacenze
            ):
                return None
            return (3, "kg", self.giacenze[lotto_id], 1, "kg", 1, self.prezzo_articolo)
        return None


class FakeVenditaCompletaCursor:
    def __init__(self, giacenza=Decimal("5.000")):
        self.giacenza = giacenza
        self.lastrowid = 80
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith("INSERT INTO vendite"):
            self.lastrowid = 81
        elif query.startswith("INSERT INTO righe_vendita"):
            self.lastrowid = 101

    def fetchone(self):
        query = self.statements[-1][0]
        if query.startswith("SELECT id FROM tenant"):
            return (42,)
        if query.startswith("SELECT COALESCE(MAX(numero)"):
            return (4,)
        if query.startswith("SELECT l.articolo_id, l.unita_misura"):
            return (3, "kg", self.giacenza, 1, "kg", 1, Decimal("12.50"))
        return None


class CreaVenditaCompletaRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.riga = VenditaRigaCreate(
            lotto_id=7,
            articolo_id=3,
            quantita=Decimal("1.250"),
            unita_misura="kg",
            prezzo_unitario=Decimal("12.50"),
            iva_percentuale=Decimal("0.00"),
        )

    def invoke(self, giacenza=Decimal("5.000")):
        cursor = FakeVenditaCompletaCursor(giacenza)
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.crea_vendita_completa(
                42,
                date(2026, 11, 10),
                None,
                "RICEVUTA",
                [self.riga],
            )
        return result, cursor, connection

    def test_header_rows_and_stock_commit_together(self):
        result, cursor, connection = self.invoke()

        self.assertEqual(result["id"], 81)
        self.assertEqual(result["numero"], 5)
        self.assertEqual(len(result["righe"]), 1)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertTrue(any(query.startswith("INSERT INTO vendite") for query, _ in cursor.statements))
        self.assertTrue(any(query.startswith("INSERT INTO righe_vendita") for query, _ in cursor.statements))
        self.assertTrue(any(query.startswith("INSERT INTO movimenti_lotto") for query, _ in cursor.statements))

    def test_stock_error_rolls_back_new_header(self):
        cursor = FakeVenditaCompletaCursor(giacenza=Decimal("0.500"))
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.GiacenzaInsufficiente):
                tracciabilita_repo.crea_vendita_completa(
                    42,
                    date(2026, 11, 10),
                    None,
                    "RICEVUTA",
                    [self.riga],
                )

        self.assertTrue(any(query.startswith("INSERT INTO vendite") for query, _ in cursor.statements))
        self.assertFalse(any(query.startswith("INSERT INTO righe_vendita") for query, _ in cursor.statements))
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)


class AggiungiRigheVenditaTests(unittest.TestCase):
    def setUp(self):
        self.riga = VenditaRigaCreate(
            lotto_id=7,
            articolo_id=3,
            quantita=Decimal("1.250"),
            unita_misura="kg",
            prezzo_unitario=Decimal("12.5000"),
            iva_percentuale=Decimal("10.00"),
        )

    def invoke_repository(
        self,
        righe=None,
        vendita_esistente=True,
        lotti_validi=None,
        giacenze=None,
        fail_on_movement=False,
        vendita_tenant_id=42,
        lotti_tenant_id=None,
        prezzo_articolo=Decimal("12.50"),
    ):
        cursor = FakeRigheVenditaCursor(
            vendita_esistente,
            lotti_validi,
            giacenze,
            fail_on_movement,
            vendita_tenant_id,
            lotti_tenant_id,
            prezzo_articolo,
        )
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.aggiungi_righe_vendita(
                42, 81, [self.riga] if righe is None else righe
            )
        return result, cursor, connection

    def test_records_line_deducts_stock_and_records_sale_movement(self):
        righe, cursor, connection = self.invoke_repository()

        self.assertEqual(
            righe,
            [
                {
                    "id": 101,
                    "vendita_id": 81,
                    "lotto_id": 7,
                    "articolo_id": 3,
                    "quantita": "1.250",
                    "unita_misura": "kg",
                    "prezzo_unitario": "12.5000",
                    "iva_percentuale": "10.00",
                }
            ],
        )
        self.assertIn("FOR UPDATE", cursor.statements[0][0])
        self.assertEqual(cursor.statements[0][1], (42, 81))
        stock_lock = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("SELECT l.articolo_id, l.unita_misura")
        )
        self.assertIn("FOR UPDATE", stock_lock[0])
        self.assertEqual(stock_lock[1], (42, 7))
        self.assertLess(
            cursor.statements.index(stock_lock),
            next(
                index
                for index, (query, _) in enumerate(cursor.statements)
                if query.startswith("UPDATE lotti")
            ),
        )
        self.assertEqual(
            next(
                params
                for query, params in cursor.statements
                if query.startswith("UPDATE lotti")
            ),
            (Decimal("3.750"), Decimal("3.750"), 42, 7),
        )
        movement = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("INSERT INTO movimenti_lotto")
        )
        self.assertIn("'VENDITA'", movement[0])
        self.assertEqual(movement[1], (42, 7, Decimal("-1.250")))
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)

    def test_sale_owned_by_another_tenant_is_not_accessible(self):
        cursor = FakeRigheVenditaCursor(vendita_tenant_id=99)
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.VenditaNonTrovata):
                tracciabilita_repo.aggiungi_righe_vendita(42, 81, [self.riga])

        sale_lookup = cursor.statements[0]
        self.assertIn("WHERE tenant_id = %s AND id = %s", sale_lookup[0])
        self.assertEqual(sale_lookup[1], (42, 81))
        self.assertFalse(
            any(
                query.startswith("SELECT l.articolo_id")
                for query, _ in cursor.statements
            )
        )
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_lot_owned_by_another_tenant_cannot_be_sold(self):
        cursor = FakeRigheVenditaCursor(lotti_tenant_id={7: 99})
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.RigaVenditaNonValida):
                tracciabilita_repo.aggiungi_righe_vendita(42, 81, [self.riga])

        lot_lookup = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("SELECT l.articolo_id")
        )
        self.assertIn("WHERE l.tenant_id = %s AND l.id = %s", lot_lookup[0])
        self.assertEqual(lot_lookup[1], (42, 7))
        self.assertFalse(
            any(query.startswith("UPDATE lotti") for query, _ in cursor.statements)
        )
        self.assertFalse(
            any(
                query.startswith("INSERT INTO righe_vendita")
                for query, _ in cursor.statements
            )
        )
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_depleted_lot_is_closed(self):
        _, cursor, connection = self.invoke_repository(
            giacenze={7: Decimal("1.250")}
        )

        update, params = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("UPDATE lotti")
        )
        self.assertIn("attivo = CASE WHEN %s = 0 THEN 0 ELSE attivo END", update)
        self.assertEqual(params, (Decimal("0.000"), Decimal("0.000"), 42, 7))
        self.assertEqual(connection.commits, 1)

    def test_insufficient_stock_rolls_back_without_persisting_sale(self):
        cursor = FakeRigheVenditaCursor(giacenze={7: Decimal("1.000")})
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.GiacenzaInsufficiente):
                tracciabilita_repo.aggiungi_righe_vendita(42, 81, [self.riga])

        self.assertFalse(
            any(query.startswith("INSERT INTO righe_vendita") for query, _ in cursor.statements)
        )
        self.assertFalse(any(query.startswith("UPDATE lotti") for query, _ in cursor.statements))
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_noncanonical_price_is_rejected_and_rolls_back(self):
        cursor = FakeRigheVenditaCursor(prezzo_articolo=Decimal("13.00"))
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.PrezzoVenditaNonValido):
                tracciabilita_repo.aggiungi_righe_vendita(42, 81, [self.riga])

        self.assertFalse(any(query.startswith("UPDATE lotti") for query, _ in cursor.statements))
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_combined_lines_cannot_exceed_locked_lot_stock(self):
        seconda_riga = self.riga.model_copy(
            update={"quantita": Decimal("0.250")}
        )
        cursor = FakeRigheVenditaCursor(giacenze={7: Decimal("1.000")})
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.GiacenzaInsufficiente):
                tracciabilita_repo.aggiungi_righe_vendita(
                    42, 81, [self.riga, seconda_riga]
                )

        self.assertFalse(
            any(
                query.startswith("INSERT INTO righe_vendita")
                for query, _ in cursor.statements
            )
        )
        self.assertFalse(
            any(query.startswith("UPDATE lotti") for query, _ in cursor.statements)
        )
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_movement_failure_rolls_back_stock_and_sale_line(self):
        cursor = FakeRigheVenditaCursor(fail_on_movement=True)
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaisesRegex(RuntimeError, "movement insert failed"):
                tracciabilita_repo.aggiungi_righe_vendita(42, 81, [self.riga])

        self.assertTrue(any(query.startswith("UPDATE lotti") for query, _ in cursor.statements))
        self.assertTrue(any(query.startswith("INSERT INTO righe_vendita") for query, _ in cursor.statements))
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_missing_sale_rolls_back(self):
        cursor = FakeRigheVenditaCursor(vendita_esistente=False)
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.VenditaNonTrovata):
                tracciabilita_repo.aggiungi_righe_vendita(42, 81, [self.riga])

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_invalid_lot_rolls_back_all_lines(self):
        riga_non_valida = self.riga.model_copy(update={"lotto_id": 8})
        cursor = FakeRigheVenditaCursor(lotti_validi={7})
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.RigaVenditaNonValida):
                tracciabilita_repo.aggiungi_righe_vendita(
                    42, 81, [self.riga, riga_non_valida]
                )

        self.assertFalse(
            any(query.startswith("INSERT INTO righe_vendita") for query, _ in cursor.statements)
        )
        self.assertFalse(any(query.startswith("UPDATE lotti") for query, _ in cursor.statements))
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_endpoint_uses_authenticated_tenant(self):
        payload = VenditaRigheCreate(righe=[self.riga])
        expected = [{"id": 101}]

        with patch.object(
            vendite_service, "aggiungi_righe_vendita", return_value=expected
        ) as add_lines:
            result = aggiungi_righe_vendita(81, payload, {"tenant_id": 42})

        self.assertEqual(result, expected)
        add_lines.assert_called_once_with(
            tenant_id=42,
            vendita_id=81,
            righe=payload.righe,
        )

    def test_endpoint_translates_nonexistent_sale(self):
        payload = VenditaRigheCreate(righe=[self.riga])
        with patch.object(
            vendite_service,
            "aggiungi_righe_vendita",
            side_effect=tracciabilita_repo.VenditaNonTrovata,
        ):
            with self.assertRaises(HTTPException) as error:
                aggiungi_righe_vendita(81, payload, {"tenant_id": 42})

        self.assertEqual(error.exception.status_code, 404)

    def test_endpoint_translates_insufficient_stock_to_conflict(self):
        payload = VenditaRigheCreate(righe=[self.riga])
        with patch.object(
            vendite_service,
            "aggiungi_righe_vendita",
            side_effect=tracciabilita_repo.GiacenzaInsufficiente(
                "La giacenza del lotto 7 è insufficiente."
            ),
        ):
            with self.assertRaises(HTTPException) as error:
                aggiungi_righe_vendita(81, payload, {"tenant_id": 42})

        self.assertEqual(error.exception.status_code, 409)


class VenditeServiceTests(unittest.TestCase):
    def test_service_delegates_to_traceability_repository(self):
        expected_lots = [{"id": 7}]
        expected_sale = {"id": 81}
        expected_lines = [{"id": 101}]

        with (
            patch.object(
                tracciabilita_repo,
                "lotti_disponibili_vendita",
                return_value=expected_lots,
            ) as list_lots,
            patch.object(
                tracciabilita_repo, "crea_vendita", return_value=expected_sale
            ) as create_sale,
            patch.object(
                tracciabilita_repo,
                "aggiungi_righe_vendita",
                return_value=expected_lines,
            ) as add_lines,
        ):
            lots = vendite_service.lotti_disponibili_vendita(42)
            sale = vendite_service.crea_vendita(
                42, date(2026, 11, 10), 13, "DDT"
            )
            lines = vendite_service.aggiungi_righe_vendita(42, 81, [])

        self.assertIs(lots, expected_lots)
        list_lots.assert_called_once_with(42)
        self.assertIs(sale, expected_sale)
        create_sale.assert_called_once_with(
            tenant_id=42,
            data_vendita=date(2026, 11, 10),
            cliente_id=13,
            tipo_documento="DDT",
        )
        self.assertIs(lines, expected_lines)
        add_lines.assert_called_once_with(tenant_id=42, vendita_id=81, righe=[])


if __name__ == "__main__":
    unittest.main()
