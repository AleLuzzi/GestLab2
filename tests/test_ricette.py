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
    def __init__(
        self,
        articolo=(8,),
        ricetta=None,
        ricette=(),
        articoli_input=(),
        ingredienti=(),
        allergeni=(),
    ):
        self.articolo = articolo
        self.ricetta = ricetta
        self.ricette = list(ricette)
        self.articoli_input = list(articoli_input)
        self.ingredienti = list(ingredienti)
        self.allergeni = list(allergeni)
        self.ricetta_esistente = True
        self.lastrowid = 17
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))

    def fetchone(self):
        query = self.statements[-1][0]
        if query.startswith("SELECT id FROM articoli") and "utilizzabile_come_input" not in query:
            return self.articolo
        if query.startswith("SELECT id FROM ricette"):
            return (17,) if self.ricetta_esistente else None
        if "FROM ricette r JOIN articoli a" in query:
            return self.ricetta
        return None

    def fetchall(self):
        query = self.statements[-1][0]
        if "utilizzabile_come_input" in query:
            return self.articoli_input
        if "FROM ricetta_allergeni" in query:
            return self.allergeni
        if "FROM ricetta_ingredienti" in query:
            return self.ingredienti
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

    def test_recipe_ingredient_schema_validates_quantity_percentage_and_uniqueness(self):
        ricetta = RicettaCreate(
            nome="Salsiccia",
            articolo_id=8,
            resa_attesa=1,
            ingredienti=[
                {
                    "articolo_id": 5,
                    "tipo_quantita": "quantita",
                    "valore": "0.250",
                    "obbligatorio": False,
                },
                {
                    "articolo_id": 6,
                    "tipo_quantita": "percentuale",
                    "valore": "15.000",
                },
            ],
        )

        self.assertEqual(len(ricetta.ingredienti), 2)
        self.assertFalse(ricetta.ingredienti[0].obbligatorio)
        self.assertTrue(ricetta.ingredienti[1].obbligatorio)

        with self.assertRaises(ValueError):
            RicettaCreate(
                nome="Salsiccia",
                articolo_id=8,
                resa_attesa=1,
                ingredienti=[
                    {"articolo_id": 5, "tipo_quantita": "percentuale", "valore": 100.001}
                ],
            )
        with self.assertRaises(ValueError):
            RicettaCreate(
                nome="Salsiccia",
                articolo_id=8,
                resa_attesa=1,
                ingredienti=[
                    {"articolo_id": 5, "tipo_quantita": "quantita", "valore": 1},
                    {"articolo_id": 5, "tipo_quantita": "quantita", "valore": 2},
                ],
            )

    def test_recipe_schema_validates_allergens_lifetime_and_instructions(self):
        recipe = RicettaCreate(
            nome="Salsiccia",
            articolo_id=8,
            resa_attesa=1,
            allergeni=["glutine", "latte"],
            giorni_vita=3,
            istruzioni_conservazione="  Conservare tra 0 e 4 °C  ",
            istruzioni_cottura="Cuocere completamente",
        )

        self.assertEqual(recipe.allergeni, ["glutine", "latte"])
        self.assertEqual(recipe.giorni_vita, 3)
        self.assertEqual(recipe.istruzioni_conservazione, "Conservare tra 0 e 4 °C")
        self.assertEqual(recipe.istruzioni_cottura, "Cuocere completamente")
        with self.assertRaises(ValueError):
            RicettaCreate(
                nome="Salsiccia",
                articolo_id=8,
                resa_attesa=1,
                allergeni=["latte", "latte"],
            )
        with self.assertRaises(ValueError):
            RicettaCreate(
                nome="Salsiccia",
                articolo_id=8,
                resa_attesa=1,
                allergeni=["non_riconosciuto"],
            )
        with self.assertRaises(ValueError):
            RicettaCreate(
                nome="Salsiccia", articolo_id=8, resa_attesa=1, giorni_vita=0
            )

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

    def test_update_recipe_replaces_allergens_and_shelf_life_atomically(self):
        result_row = (
            17,
            "Salsiccia",
            8,
            "Salsiccia",
            "kg",
            Decimal("8.000"),
            Decimal("0.500"),
            1,
            2,
            "Conservare a 4 °C",
            "Cuocere completamente",
        )
        cursor = RicettaCursor(
            ricetta=result_row, allergeni=[("latte",)]
        )
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            recipe = tracciabilita_repo.aggiorna_ricetta(
                42,
                17,
                "Salsiccia",
                8,
                8,
                0.5,
                True,
                allergeni=["latte"],
                giorni_vita=2,
                istruzioni_conservazione="Conservare a 4 °C",
                istruzioni_cottura="Cuocere completamente",
            )

        update = next(
            params
            for query, params in cursor.statements
            if query.startswith("UPDATE ricette")
        )
        self.assertEqual(update[5:8], (2, "Conservare a 4 °C", "Cuocere completamente"))
        self.assertEqual(recipe["allergeni"], ["latte"])
        self.assertTrue(
            any(query.startswith("DELETE FROM ricetta_allergeni") for query, _ in cursor.statements)
        )
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_create_recipe_persists_ordered_input_ingredients(self):
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
        ingredient_rows = [
            (17, 5, "Carne", "kg", "quantita", Decimal("0.800"), 1),
            (17, 6, "Sale", "kg", "percentuale", Decimal("1.500"), 0),
        ]
        cursor = RicettaCursor(
            ricetta=result_row,
            articoli_input=[(5,), (6,)],
            ingredienti=ingredient_rows,
        )
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.crea_ricetta(
                42,
                "Salsiccia fresca",
                8,
                Decimal("9.500"),
                Decimal("0.250"),
                [
                    {
                        "articolo_id": 5,
                        "tipo_quantita": "quantita",
                        "valore": Decimal("0.800"),
                        "obbligatorio": True,
                    },
                    {
                        "articolo_id": 6,
                        "tipo_quantita": "percentuale",
                        "valore": Decimal("1.500"),
                        "obbligatorio": False,
                    },
                ],
            )

        self.assertEqual(
            [ingrediente["articolo_id"] for ingrediente in result["ingredienti"]],
            [5, 6],
        )
        self.assertEqual(result["ingredienti"][1]["tipo_quantita"], "percentuale")
        self.assertFalse(result["ingredienti"][1]["obbligatorio"])
        inserts = [
            params
            for query, params in cursor.statements
            if query.startswith("INSERT INTO ricetta_ingredienti")
        ]
        self.assertEqual([param[3] for param in inserts], [1, 2])
        self.assertEqual([param[0] for param in inserts], [42, 42])
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_create_recipe_rolls_back_if_input_article_is_not_valid_for_tenant(self):
        cursor = RicettaCursor(articoli_input=[])
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.crea_ricetta(
                42,
                "Ricetta",
                8,
                1,
                0,
                [
                    {
                        "articolo_id": 5,
                        "tipo_quantita": "quantita",
                        "valore": 1,
                        "obbligatorio": True,
                    }
                ],
            )

        self.assertIsNone(result)
        self.assertFalse(
            any(query.startswith("INSERT INTO ricetta_ingredienti") for query, _ in cursor.statements)
        )
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_list_recipes_includes_tenant_scoped_ingredient_rows(self):
        recipe_row = (
            17,
            "Salsiccia fresca",
            8,
            "Salsiccia",
            "kg",
            Decimal("9.500"),
            Decimal("0.250"),
            1,
        )
        ingredient_row = (
            17,
            5,
            "Carne",
            "kg",
            "quantita",
            Decimal("0.800"),
            1,
        )
        cursor = RicettaCursor(
            ricette=[recipe_row],
            ingredienti=[ingredient_row],
            allergeni=[(17, "latte")],
        )
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            recipes = tracciabilita_repo.lista_ricette(42)

        self.assertEqual(recipes[0]["ingredienti"][0]["articolo_nome"], "Carne")
        self.assertEqual(recipes[0]["ingredienti"][0]["valore"], "0.800")
        self.assertEqual(recipes[0]["allergeni"], ["latte"])
        ingredient_query, ingredient_params = cursor.statements[1]
        self.assertIn("WHERE ri.tenant_id = %s", ingredient_query)
        self.assertEqual(ingredient_params, (42,))
        allergen_query, allergen_params = cursor.statements[2]
        self.assertIn("WHERE tenant_id = %s", allergen_query)
        self.assertEqual(allergen_params, (42,))

    def test_create_recipe_persists_allergens_lifetime_and_instructions(self):
        result_row = (
            17,
            "Salsiccia",
            8,
            "Salsiccia",
            "kg",
            Decimal("9.500"),
            Decimal("0.250"),
            1,
            3,
            "Conservare a 4 °C",
            "Cuocere completamente",
        )
        cursor = RicettaCursor(
            ricetta=result_row, allergeni=[("latte",), ("glutine",)]
        )
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            recipe = tracciabilita_repo.crea_ricetta(
                42,
                "Salsiccia",
                8,
                Decimal("9.500"),
                Decimal("0.250"),
                allergeni=["latte", "glutine"],
                giorni_vita=3,
                istruzioni_conservazione="Conservare a 4 °C",
                istruzioni_cottura="Cuocere completamente",
            )

        self.assertEqual(recipe["allergeni"], ["glutine", "latte"])
        self.assertEqual(recipe["giorni_vita"], 3)
        insert = next(
            params
            for query, params in cursor.statements
            if query.startswith("INSERT INTO ricette")
        )
        self.assertEqual(insert[-3:], (3, "Conservare a 4 °C", "Cuocere completamente"))
        allergen_inserts = [
            params
            for query, params in cursor.statements
            if query.startswith("INSERT INTO ricetta_allergeni")
        ]
        self.assertEqual(allergen_inserts, [(42, 17, "glutine"), (42, 17, "latte")])
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_update_recipe_replaces_ingredients_in_same_transaction(self):
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
        cursor = RicettaCursor(
            ricetta=result_row,
            articoli_input=[(6,)],
            ingredienti=[(17, 6, "Sale", "kg", "percentuale", Decimal("1.500"), 1)],
        )
        conn = RicettaConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.aggiorna_ricetta(
                42,
                17,
                "Salsiccia",
                8,
                8,
                0.5,
                True,
                [
                    {
                        "articolo_id": 6,
                        "tipo_quantita": "percentuale",
                        "valore": Decimal("1.500"),
                        "obbligatorio": True,
                    }
                ],
            )

        self.assertEqual(result["ingredienti"][0]["articolo_id"], 6)
        self.assertTrue(
            any(
                query.startswith("DELETE FROM ricetta_ingredienti")
                for query, _ in cursor.statements
            )
        )
        self.assertTrue(
            any(
                query.startswith("INSERT INTO ricetta_ingredienti")
                for query, _ in cursor.statements
            )
        )
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

        payload = RicettaCreate(
            nome="Ricetta",
            articolo_id=8,
            resa_attesa=1,
            ingredienti=[
                {
                    "articolo_id": 5,
                    "tipo_quantita": "quantita",
                    "valore": 0.25,
                }
            ],
        )
        with patch.object(
            tracciabilita_repo, "crea_ricetta", return_value=expected
        ) as create_recipe:
            crea_ricetta(payload, {"tenant_id": 42})

        self.assertEqual(create_recipe.call_args.args[0], 42)
        self.assertEqual(create_recipe.call_args.args[5], payload.ingredienti)
        self.assertEqual(create_recipe.call_args.args[6], payload.allergeni)
        self.assertEqual(create_recipe.call_args.args[7], payload.giorni_vita)

    def test_bootstrap_registers_recipe_migration(self):
        migration = "20261108_ricette.sql"
        self.assertIn(migration, bootstrap.MIGRATION_ORDER)
        sql = (Path(bootstrap.MIGRATIONS_DIR) / migration).read_text(
            encoding="utf-8"
        )
        self.assertIn("FOREIGN KEY (`tenant_id`, `articolo_id`)", sql)
        self.assertIn("CHECK (`resa_attesa` > 0 AND `scarto_atteso` >= 0)", sql)
        ingredient_migration = "20261108_ricetta_ingredienti.sql"
        self.assertIn(ingredient_migration, bootstrap.MIGRATION_ORDER)
        ingredient_sql = (Path(bootstrap.MIGRATIONS_DIR) / ingredient_migration).read_text(
            encoding="utf-8"
        )
        self.assertIn("FOREIGN KEY (`tenant_id`, `ricetta_id`)", ingredient_sql)
        self.assertIn("FOREIGN KEY (`tenant_id`, `articolo_id`)", ingredient_sql)

        enrichment_migration = "20261108_ricetta_allergeni_durata.sql"
        self.assertIn(enrichment_migration, bootstrap.MIGRATION_ORDER)
        enrichment_sql = Path(bootstrap.MIGRATIONS_DIR, enrichment_migration).read_text(
            encoding="utf-8"
        )
        self.assertIn("ADD COLUMN `giorni_vita`", enrichment_sql)
        self.assertIn("fk_ricetta_allergeni_ricetta", enrichment_sql)
        self.assertIn("chk_ricetta_allergeni_codice", enrichment_sql)

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

    def test_bootstrap_recognizes_recipe_ingredients_migration(self):
        migration = "20261108_ricetta_ingredienti.sql"
        columns = {
            "tenant_id",
            "ricetta_id",
            "articolo_id",
            "posizione",
            "tipo_quantita",
            "valore",
            "obbligatorio",
        }

        class CompleteIngredientSchemaCursor:
            def execute(self, query, params=None):
                self.query = query

            def fetchone(self):
                return (
                    "ricetta_ingredienti",
                    "CREATE TABLE ricetta_ingredienti "
                    "CONSTRAINT fk_ricetta_ingredienti_ricetta "
                    "CONSTRAINT fk_ricetta_ingredienti_articolo "
                    "CHECK chk_ricetta_ingredienti_quantita",
                )

        with (
            patch.object(bootstrap, "_tabella_esiste", return_value=True),
            patch.object(bootstrap, "_colonne_tabella", return_value=columns),
        ):
            self.assertTrue(
                bootstrap._migrazione_gia_applicata(
                    CompleteIngredientSchemaCursor(), migration
                )
            )

        with (
            patch.object(bootstrap, "_tabella_esiste", return_value=True),
            patch.object(bootstrap, "_colonne_tabella", return_value=columns - {"valore"}),
        ):
            self.assertFalse(
                bootstrap._migrazione_gia_applicata(
                    CompleteIngredientSchemaCursor(), migration
                )
            )

    def test_bootstrap_recognizes_recipe_allergen_lifetime_migration(self):
        migration = "20261108_ricetta_allergeni_durata.sql"
        columns = {
            "giorni_vita",
            "istruzioni_conservazione",
            "istruzioni_cottura",
        }
        allergen_columns = {"tenant_id", "ricetta_id", "codice"}

        class CompleteSchemaCursor:
            def execute(self, query, params=None):
                self.query = query

            def fetchone(self):
                if self.query == "SHOW CREATE TABLE `ricette`":
                    return (
                        "ricette",
                        "CREATE TABLE ricette CONSTRAINT chk_ricette_giorni_vita",
                    )
                return (
                    "ricetta_allergeni",
                    "CREATE TABLE ricetta_allergeni "
                    "CONSTRAINT fk_ricetta_allergeni_ricetta "
                    "CHECK chk_ricetta_allergeni_codice",
                )

        with (
            patch.object(bootstrap, "_tabella_esiste", return_value=True),
            patch.object(
                bootstrap,
                "_colonne_tabella",
                side_effect=[columns, allergen_columns],
            ),
        ):
            self.assertTrue(
                bootstrap._migrazione_gia_applicata(
                    CompleteSchemaCursor(), migration
                )
            )


if __name__ == "__main__":
    unittest.main()
