"""Vendite, scadenze e isolamento tenant del prodotto vendibile.

Un lotto con scadenza già passata non si vende. Il TMC trascorso resta
vendibile. Una lettura o una vendita del tenant A non usa i dati del tenant B:
se la query non filtra il tenant del token, il cursore restituisce il record
altrui e il test fallisce.
"""

import unittest
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from saas.main import (
    aggiungi_righe_vendita,
    crea_vendita_completa,
    dettaglio_lotto_tracciato,
    genera_ddt_vendita,
)
from saas.repositories import tracciabilita_repo
from saas.schemas import VenditaCompletaCreate, VenditaRigaCreate, VenditaRigheCreate


TENANT_A = 42
OGGI = date(2026, 11, 21)
UTENTE_A = {"tenant_id": TENANT_A, "ruolo": "operatore", "sub": "a@laboratorio.test"}


def riga_vendita():
    return VenditaRigaCreate(
        lotto_id=7,
        articolo_id=3,
        quantita=Decimal("1.000"),
        unita_misura="kg",
        prezzo_unitario=Decimal("12.50"),
        iva_percentuale=Decimal("10.00"),
    )


class CursoreVendita:
    def __init__(self, data_scadenza, oggi=OGGI, lotto_tenant=TENANT_A, leaky=False):
        self.data_scadenza = data_scadenza
        self.oggi = oggi
        self.lotto_tenant = lotto_tenant
        self.leaky = leaky
        self.statements = []
        self.lastrowid = 80

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith("INSERT INTO vendite"):
            self.lastrowid = 81
        elif query.startswith("INSERT INTO righe_vendita"):
            self.lastrowid = 101

    def fetchone(self):
        query, params = self.statements[-1]
        params = params or ()
        if query.startswith("SELECT id FROM tenant"):
            return (TENANT_A,) if params[0] == TENANT_A else None
        if query.startswith("SELECT COALESCE(MAX(numero)"):
            return (4,)
        if query.startswith("SELECT id FROM vendite"):
            return (81,) if params[0] == TENANT_A else None
        if query.startswith("SELECT l.articolo_id"):
            scoped = "tenant_id" in query and TENANT_A in params
            if not scoped:
                return self._lotto() if self.leaky else None
            if self.lotto_tenant != params[0]:
                return None
            return self._lotto()
        return None

    def _lotto(self):
        return (
            3,
            "kg",
            Decimal("5.000"),
            1,
            "kg",
            1,
            Decimal("12.50"),
            self.data_scadenza,
            self.oggi,
        )


class Connessione:
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


def connessione(cursor):
    conn = Connessione(cursor)

    @contextmanager
    def fake_connection():
        yield conn

    return fake_connection, conn


class CursoreElenco:
    def __init__(self):
        self.query = ""
        self.params = None

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return []


class VenditeEScadenzeTests(unittest.TestCase):
    def _registra(self, cursor):
        fake_connection, conn = connessione(cursor)
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            risultato = tracciabilita_repo.aggiungi_righe_vendita(
                TENANT_A, 81, [riga_vendita()]
            )
        return risultato, cursor, conn

    def test_lotto_con_scadenza_passata_non_si_vende_e_annulla_la_transazione(self):
        cursor = CursoreVendita(date(2026, 11, 20))
        fake_connection, conn = connessione(cursor)
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.LottoScaduto) as error:
                tracciabilita_repo.aggiungi_righe_vendita(
                    TENANT_A, 81, [riga_vendita()]
                )

        self.assertIn("scadenza superata", str(error.exception))
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)
        self.assertFalse(
            any(query.startswith("UPDATE lotti") for query, _ in cursor.statements)
        )
        self.assertFalse(
            any(query.startswith("INSERT INTO movimenti_lotto") for query, _ in cursor.statements)
        )

    def test_scadenza_di_oggi_resta_vendibile(self):
        _, cursor, conn = self._registra(CursoreVendita(OGGI))

        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)
        movimento = next(
            params
            for query, params in cursor.statements
            if query.startswith("INSERT INTO movimenti_lotto")
        )
        self.assertEqual(movimento, (TENANT_A, 7, Decimal("-1.000")))

    def test_tmc_trascorso_non_blocca_la_vendita(self):
        cursor = CursoreVendita(None)
        _, cursor, conn = self._registra(cursor)

        blocco = next(
            query
            for query, _ in cursor.statements
            if query.startswith("SELECT l.articolo_id")
        )
        self.assertIn("l.data_scadenza", blocco)
        self.assertNotIn("data_tmc", blocco)
        self.assertEqual(conn.commits, 1)

    def test_date_testuali_e_orario_del_database_si_confrontano_come_giorni(self):
        cursor = CursoreVendita("2026-11-20", datetime(2026, 11, 21, 15, 4))
        fake_connection, conn = connessione(cursor)
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.LottoScaduto):
                tracciabilita_repo.aggiungi_righe_vendita(
                    TENANT_A, 81, [riga_vendita()]
                )
        self.assertEqual(conn.rollbacks, 1)

    def test_vendita_completa_di_un_lotto_scaduto_non_conserva_il_documento(self):
        cursor = CursoreVendita(date(2026, 11, 20))
        fake_connection, conn = connessione(cursor)
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.LottoScaduto):
                tracciabilita_repo.crea_vendita_completa(
                    TENANT_A,
                    OGGI,
                    None,
                    "RICEVUTA",
                    [riga_vendita()],
                )

        self.assertTrue(
            any(query.startswith("INSERT INTO vendite") for query, _ in cursor.statements)
        )
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_elenco_vendita_esclude_la_scadenza_passata_e_ordina_in_fefo(self):
        cursor = CursoreElenco()
        fake_connection, _ = connessione(cursor)
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            tracciabilita_repo.lotti_disponibili_vendita(TENANT_A)

        self.assertEqual(cursor.params, (TENANT_A,))
        self.assertIn("l.data_scadenza >= CURRENT_DATE", cursor.query)
        self.assertNotIn("data_tmc >=", cursor.query)
        self.assertIn("COALESCE(l.data_scadenza, l.data_tmc) ASC", cursor.query)
        self.assertIn("THEN 1 ELSE 0 END", cursor.query)
        self.assertIn("l.data_scadenza >= CURRENT_DATE", tracciabilita_repo._LOTTO_VENDIBILE)
        self.assertNotIn("data_tmc", tracciabilita_repo._LOTTO_VENDIBILE)

    def test_api_risponde_409_in_italiano_per_la_scadenza_superata(self):
        messaggio = "Il lotto 7 ha una data di scadenza superata."
        payload_righe = VenditaRigheCreate(righe=[riga_vendita()])
        payload_completa = VenditaCompletaCreate(
            data=OGGI,
            tipo_documento="RICEVUTA",
            righe=[riga_vendita()],
        )
        with patch(
            "saas.main.vendite_service.aggiungi_righe_vendita",
            side_effect=tracciabilita_repo.LottoScaduto(messaggio),
        ):
            with self.assertRaises(HTTPException) as righe:
                aggiungi_righe_vendita(81, payload_righe, UTENTE_A)
        with patch(
            "saas.main.vendite_service.crea_vendita_completa",
            side_effect=tracciabilita_repo.LottoScaduto(messaggio),
        ):
            with self.assertRaises(HTTPException) as completa:
                crea_vendita_completa(payload_completa, UTENTE_A)

        for error in (righe, completa):
            self.assertEqual(error.exception.status_code, 409)
            self.assertEqual(error.exception.detail, messaggio)


class CursoreLeaky:
    """Restituisce il record del tenant B solo se la query non filtra il tenant A."""

    def __init__(self, foreign_row):
        self.foreign_row = foreign_row
        self.statements = []
        self._scoped = True

    def execute(self, query, params=None):
        params = params or ()
        self.statements.append((query, params))
        self._scoped = "tenant_id" in query and TENANT_A in params

    def fetchone(self):
        if self._scoped:
            return None
        return self.foreign_row

    def fetchall(self):
        if self._scoped:
            return []
        return [self.foreign_row] if not isinstance(self.foreign_row, list) else self.foreign_row


class IsolamentoTenantTests(unittest.TestCase):
    def test_la_vendita_non_scarica_un_lotto_di_un_altro_tenant(self):
        cursor = CursoreVendita(OGGI, lotto_tenant=99, leaky=True)
        fake_connection, conn = connessione(cursor)
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.RigaVenditaNonValida):
                tracciabilita_repo.aggiungi_righe_vendita(
                    TENANT_A, 81, [riga_vendita()]
                )

        blocco = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("SELECT l.articolo_id")
        )
        self.assertIn("tenant_id", blocco[0])
        self.assertIn(TENANT_A, blocco[1])
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)
        self.assertFalse(
            any(query.startswith("UPDATE lotti") for query, _ in cursor.statements)
        )

    def test_il_dettaglio_lotto_di_un_altro_tenant_non_restituisce_dati(self):
        cursor = CursoreLeaky((99, 3, "Costata", "A", 1, "B-99") + (None,) * 21)
        fake_connection, _ = connessione(cursor)
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(HTTPException) as error:
                dettaglio_lotto_tracciato(99, UTENTE_A)

        self.assertEqual(error.exception.status_code, 404)
        self.assertIn("tenant_id", cursor.statements[0][0])
        self.assertIn(TENANT_A, cursor.statements[0][1])

    def test_il_ddt_di_un_altro_tenant_non_restituisce_dati(self):
        cursor = CursoreLeaky((8, 3, OGGI, "DDT") + (None,) * 12)
        fake_connection, _ = connessione(cursor)
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(HTTPException) as error:
                genera_ddt_vendita(8, UTENTE_A)

        self.assertEqual(error.exception.status_code, 404)
        self.assertIn("tenant_id", cursor.statements[0][0])
        self.assertIn(TENANT_A, cursor.statements[0][1])


if __name__ == "__main__":
    unittest.main()
