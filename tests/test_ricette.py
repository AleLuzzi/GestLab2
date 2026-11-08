import unittest
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from saas import bootstrap
from saas.main import crea_ricetta, lista_ricette
from saas.repositories import tracciabilita_repo
from saas.schemas import RicettaCreate


class RicettaCursor:
    def __init__(self, articolo=(8,), ricetta=None, ricette=()):
        self.articolo = articolo
        self.ricetta = ricetta
        self.ricette = list(ricette)
        self.ricetta_esistente = True
        self.lastrowid = 17
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))

    def fetchone(self):
        query = self.statements[-1][0]
        if query.startswith("SELECT id FROM articoli"):
            return self.articolo
        if query.startswith("SELECT id FROM ricette"):
            return (17,) if self.ricetta_esistente else None
        if "FROM ricette r JOIN articoli a" in query:
            return self.ricetta
        return None

    def fetchall(self):
        return self.ricette


class RicettaConnection:
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


class RicetteTests(unittest.TestCase):
    def test_schema_normalizes_name_and_validates_expected_quantities(self):
        ricetta = RicettaCreate(
            nome="  Salsiccia fresca  ",
            articolo_id=8,
            resa_attesa="9.500",
            scarto_atteso="0.250",
        )

        self.assertEqual(ricetta.nome, "Salsiccia fresca")
        self.assertEqual(ricetta.resa_attesa, Decimal("9.500"))
        self.assertEqual(ricetta.scarto_atteso, Decimal("0.250"))

        with self.assertRaises(ValueError):
            RicettaCreate(nome="  ", articolo_id=8, resa_attesa=1)
        with self.assertRaises(ValueError):
            RicettaCreate(nome="Ricetta", articolo_id=8, resa_attesa=0)
        with self.assertRaises(ValueError):
            RicettaCreate(nome="Ricetta", articolo_id=8, resa_attesa=1, scarto_atteso=-1)

    def test_create_recipe_is_tenant_scoped_and_atomic(self):
        result_row = (
            17,
            "Salsiccia fresca",
            8,
            "Salsiccia",
            "kg",
            Decimal("9.500"),
            Decimal("0.250"),
            1,
        )
        cursor = RicettaCursor(ricetta=result_row)
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.crea_ricetta(
                42, "Salsiccia fresca", 8, Decimal("9.500"), Decimal("0.250")
            )

        self.assertEqual(result["id"], 17)
        self.assertEqual(result["articolo_nome"], "Salsiccia")
        self.assertEqual(result["unita_misura"], "kg")
        self.assertEqual(result["resa_attesa"], "9.500")
        self.assertEqual(result["scarto_atteso"], "0.250")
        self.assertEqual(cursor.statements[0][1], (42, 8))
        insert = next(
            params
            for query, params in cursor.statements
            if query.startswith("INSERT INTO ricette")
        )
        self.assertEqual(insert[0], 42)
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_create_rejects_article_from_another_tenant(self):
        cursor = RicettaCursor(articolo=None)
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.crea_ricetta(42, "Ricetta", 8, 1, 0)

        self.assertIsNone(result)
        self.assertFalse(any(q.startswith("INSERT INTO ricette") for q, _ in cursor.statements))
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_list_recipes_filters_by_tenant(self):
        row = (
            17,
            "Salsiccia fresca",
            8,
            "Salsiccia",
            "kg",
            Decimal("9.500"),
            Decimal("0.250"),
            1,
        )
        cursor = RicettaCursor(ricette=[row])
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            recipes = tracciabilita_repo.lista_ricette(42)

        self.assertEqual(recipes[0]["nome"], "Salsiccia fresca")
        self.assertIn("WHERE r.tenant_id = %s", cursor.statements[0][0])
        self.assertEqual(cursor.statements[0][1], (42,))

    def test_update_recipe_and_soft_disable_are_tenant_scoped(self):
        result_row = (
            17,
            "Salsiccia",
            8,
            "Salsiccia",
            "kg",
            Decimal("8.000"),
            Decimal("0.500"),
            1,
        )
        cursor = RicettaCursor(ricetta=result_row)
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.aggiorna_ricetta(42, 17, "Salsiccia", 8, 8, 0.5, True)

        self.assertEqual(result["id"], 17)
        update_params = next(
            params
            for query, params in cursor.statements
            if query.startswith("UPDATE ricette")
        )
        self.assertEqual(update_params[-2:], (42, 17))
        self.assertEqual(conn.commits, 1)

        cursor.statements.clear()
        cursor.ricetta_esistente = True
        with patch.object(tracciabilita_repo, "connection", fake_connection):
            self.assertTrue(tracciabilita_repo.disattiva_ricetta(42, 17))

        deactivate_query, deactivate_params = cursor.statements[0]
        self.assertIn("WHERE tenant_id = %s AND id = %s", deactivate_query)
        self.assertEqual(deactivate_params, (42, 17))

    def test_list_and_create_endpoints_use_authenticated_tenant(self):
        expected = [{"id": 17, "nome": "Salsiccia fresca"}]
        with patch.object(
            tracciabilita_repo, "lista_ricette", return_value=expected
        ) as list_recipes:
            result = lista_ricette({"tenant_id": 42})

        self.assertEqual(result, expected)
        list_recipes.assert_called_once_with(42)

        payload = RicettaCreate(nome="Ricetta", articolo_id=8, resa_attesa=1)
        with patch.object(
            tracciabilita_repo, "crea_ricetta", return_value=None
        ) as create_recipe:
            with self.assertRaises(HTTPException) as raised:
                crea_ricetta(payload, {"tenant_id": 42})

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(create_recipe.call_args.args[0], 42)

    def test_bootstrap_registers_recipe_migration(self):
        migration = "20261108_ricette.sql"
        self.assertIn(migration, bootstrap.MIGRATION_ORDER)
        sql = (Path(bootstrap.MIGRATIONS_DIR) / migration).read_text(
            encoding="utf-8"
        )
        self.assertIn("FOREIGN KEY (`tenant_id`, `articolo_id`)", sql)
        self.assertIn("CHECK (`resa_attesa` > 0 AND `scarto_atteso` >= 0)", sql)

    def test_bootstrap_recognizes_only_complete_recipe_migration(self):
        cursor = object()
        columns = {
            "tenant_id",
            "nome",
            "articolo_id",
            "resa_attesa",
            "scarto_atteso",
            "attiva",
        }
        with (
            patch.object(bootstrap, "_tabella_esiste", return_value=True),
            patch.object(bootstrap, "_colonne_tabella", return_value=columns),
        ):
            class RecipeSchemaCursor:
                def execute(self, query, params=None):
                    self.query = query

                def fetchone(self):
                    return (
                        "ricette",
                        "CREATE TABLE ricette CONSTRAINT fk_ricette_articolo "
                        "CHECK chk_ricette_quantita",
                    )

            self.assertTrue(
                bootstrap._migrazione_gia_applicata(
                    RecipeSchemaCursor(), "20261108_ricette.sql"
                )
            )

        with (
            patch.object(bootstrap, "_tabella_esiste", return_value=True),
            patch.object(bootstrap, "_colonne_tabella", return_value=columns),
        ):
            class IncompleteRecipeSchemaCursor:
                def execute(self, query, params=None):
                    pass

                def fetchone(self):
                    return ("ricette", "CREATE TABLE ricette")

            self.assertFalse(
                bootstrap._migrazione_gia_applicata(
                    IncompleteRecipeSchemaCursor(), "20261108_ricette.sql"
                )
            )


if __name__ == "__main__":
    unittest.main()
