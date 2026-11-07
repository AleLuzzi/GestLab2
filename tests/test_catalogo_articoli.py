import unittest
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

from core.repositories import prodotti as prodotti_repo
from saas.repositories import tracciabilita_repo
from saas.schemas import ArticoloCreate, ArticoloUpdate


class FakeCursor:
    def __init__(self, row=None, rows=()):
        self.row = row
        self.rows = list(rows)
        self.query = None
        self.params = None
        self.statements = []

    def execute(self, query, params=None):
        self.query = query
        self.params = params
        self.statements.append((query, params))

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


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


class CatalogoArticoliTests(unittest.TestCase):
    def test_ean_lookup_uses_article_and_bizerba_profile(self):
        cursor = FakeCursor(
            row=(12, "Salsiccia", "00234", "SAL01", "8001234567897", Decimal("12.50"), "kg")
        )

        @contextmanager
        def fake_connection():
            yield FakeConnection(cursor)

        with patch.object(prodotti_repo, "connection", fake_connection):
            article = prodotti_repo.trova_per_ean("8001234567897", tenant_id=7)

        self.assertIn("FROM articoli a LEFT JOIN articoli_bilancia b", cursor.query)
        self.assertNotIn("FROM prodotti", cursor.query)
        self.assertIn("a.tenant_id = %s", cursor.query)
        self.assertEqual(cursor.params, ("8001234567897", "8001234567897", 7, "8001234567897"))
        self.assertEqual(article["articolo_id"], 12)
        self.assertEqual(article["nome"], "Salsiccia")
        self.assertEqual(article["plu"], "00234")
        self.assertEqual(article["prezzo_unitario"], "12.50")

    def test_menu_reads_active_articles_and_optional_bizerba_plu(self):
        cursor = FakeCursor(rows=[("Hamburger", None)])

        @contextmanager
        def fake_connection():
            yield FakeConnection(cursor)

        with patch.object(prodotti_repo, "connection", fake_connection):
            items = prodotti_repo.prodotti_per_merceologia("Secondi", tenant_id=7)

        self.assertIn("FROM articoli a", cursor.query)
        self.assertIn("LEFT JOIN articoli_bilancia b", cursor.query)
        self.assertIn("a.attivo = 1", cursor.query)
        self.assertEqual(items, [{"prodotto": "Hamburger", "plu": ""}])
        self.assertEqual(cursor.params, ("Secondi", 7))

    def test_article_schemas_accept_shared_ean_and_price(self):
        create = ArticoloCreate(
            nome="Salsiccia",
            ean="8001234567897",
            prezzo_unitario="12.50",
        )
        update = ArticoloUpdate(
            nome="Salsiccia",
            unita_misura="kg",
            ean="8001234567897",
            prezzo_unitario="12.50",
        )

        self.assertEqual(create.prezzo_unitario, Decimal("12.50"))
        self.assertEqual(update.prezzo_unitario, Decimal("12.50"))

    def test_article_schema_rejects_negative_price(self):
        with self.assertRaises(ValueError):
            ArticoloCreate(nome="Salsiccia", prezzo_unitario="-0.01")

    def test_update_preserves_catalog_fields_omitted_by_older_clients(self):
        cursor = FakeCursor(
            row=(12, "SAL01", "Salsiccia", "Preparati", "kg", "8001234567897",
                 Decimal("12.50"), 1, 1)
        )
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            article = tracciabilita_repo.aggiorna_articolo(
                7,
                12,
                "SAL01",
                "Salsiccia",
                "Preparati",
                "kg",
                True,
                ean=None,
                prezzo_unitario=None,
                ean_impostato=False,
                prezzo_impostato=False,
            )

        update_query, update_params = cursor.statements[0]
        self.assertIn("ean = CASE WHEN %s THEN %s ELSE ean END", update_query)
        self.assertIn(
            "prezzo_unitario = CASE WHEN %s THEN %s ELSE prezzo_unitario END",
            update_query,
        )
        self.assertEqual(update_params[4:8], (0, None, 0, None))
        self.assertEqual(article["ean"], "8001234567897")
        self.assertEqual(article["prezzo_unitario"], "12.50")
        self.assertEqual(conn.commits, 1)


if __name__ == "__main__":
    unittest.main()
