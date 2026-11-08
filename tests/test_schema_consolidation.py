import re
import unittest
from pathlib import Path


SCHEMA_FILE = Path(__file__).resolve().parents[1] / "saas" / "init_database.sql"


def load_schema_tables():
    schema = SCHEMA_FILE.read_text(encoding="utf-8")
    tables = {}
    pattern = re.compile(
        r"CREATE TABLE IF NOT EXISTS `([^`]+)` \((.*?)\) ENGINE="
        r"InnoDB DEFAULT CHARSET=utf8mb4\b",
        re.DOTALL,
    )
    for match in pattern.finditer(schema):
        tables[match.group(1)] = match.group(2)
    return tables


class ConsolidatedSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = load_schema_tables()

    def test_every_table_has_a_primary_key_and_utf8mb4_charset(self):
        self.assertTrue(self.tables)
        self.assertEqual(len(self.tables), 24)
        for table_name, definition in self.tables.items():
            with self.subTest(table=table_name):
                self.assertRegex(definition, r"(?m)^\s*PRIMARY KEY\s*\(")

    def test_tenant_columns_are_required_and_have_tenant_foreign_keys(self):
        for table_name, definition in self.tables.items():
            if not re.search(r"`tenant_id`\s+bigint", definition):
                continue
            with self.subTest(table=table_name):
                self.assertRegex(definition, r"`tenant_id`\s+bigint NOT NULL")

        for table_name, constraint in (
            ("reparti", "fk_reparti_tenant"),
            ("dipendenti", "fk_dipendenti_tenant"),
            ("fornitori", "fk_fornitori_tenant"),
            ("merceologie", "fk_merceologie_tenant"),
            ("progressivi", "fk_progressivi_tenant"),
            ("ricette", "fk_ricette_tenant"),
        ):
            with self.subTest(table=table_name):
                self.assertIn(constraint, self.tables[table_name])

    def test_quantities_use_fixed_three_decimal_precision(self):
        for table_name, definition in self.tables.items():
            for column in re.findall(
                r"`(quantita[^`]*)`\s+([a-zA-Z]+(?:\([^)]*\))?)", definition
            ):
                with self.subTest(table=table_name, column=column[0]):
                    self.assertRegex(column[1], r"(?i)^decimal\(12,3\)")

    def test_lot_notes_are_optional_and_bounded(self):
        self.assertRegex(
            self.tables["lotti"],
            r"`note_lotto`\s+varchar\(500\)\s+DEFAULT NULL",
        )

    def test_recipes_link_output_article_and_expected_quantities(self):
        definition = self.tables["ricette"]
        self.assertRegex(definition, r"`resa_attesa`\s+decimal\(12,3\) NOT NULL")
        self.assertRegex(definition, r"`scarto_atteso`\s+decimal\(12,3\) NOT NULL")
        self.assertIn("FOREIGN KEY (`tenant_id`, `articolo_id`)", definition)
        self.assertIn("fk_ricette_articolo", definition)

    def test_tenant_stores_osa_data_for_product_labels(self):
        definition = self.tables["tenant"]
        for column, sql_type in (
            ("osa_ragione_sociale", "varchar\\(255\\) COLLATE utf8mb4_general_ci"),
            ("osa_indirizzo", "varchar\\(255\\) COLLATE utf8mb4_general_ci"),
            ("osa_laboratorio", "varchar\\(255\\) COLLATE utf8mb4_general_ci"),
            ("osa_partita_iva", "varchar\\(20\\) COLLATE utf8mb4_general_ci"),
        ):
            with self.subTest(column=column):
                self.assertRegex(
                    definition,
                    rf"`{column}`\s+{sql_type}\s+DEFAULT NULL",
                )

    def test_recipe_ingredients_are_tenant_scoped_and_typed(self):
        definition = self.tables["ricetta_ingredienti"]
        self.assertIn("PRIMARY KEY (`tenant_id`, `ricetta_id`, `articolo_id`)", definition)
        self.assertIn("FOREIGN KEY (`tenant_id`, `ricetta_id`)", definition)
        self.assertIn("FOREIGN KEY (`tenant_id`, `articolo_id`)", definition)
        self.assertRegex(definition, r"`valore`\s+decimal\(12,3\) NOT NULL")
        self.assertIn("`obbligatorio` tinyint(1) NOT NULL DEFAULT 1", definition)
        self.assertIn("`tipo_quantita` = 'percentuale' AND `valore` <= 100", definition)

    def test_recipe_allergens_and_shelf_life_are_structured(self):
        recipe = self.tables["ricette"]
        self.assertRegex(recipe, r"`giorni_vita`\s+int unsigned DEFAULT NULL")
        self.assertRegex(
            recipe, r"`istruzioni_conservazione`\s+varchar\(1000\) DEFAULT NULL"
        )
        self.assertRegex(
            recipe, r"`istruzioni_cottura`\s+varchar\(1000\) DEFAULT NULL"
        )
        self.assertIn("chk_ricette_giorni_vita", recipe)
        allergens = self.tables["ricetta_allergeni"]
        self.assertIn(
            "PRIMARY KEY (`tenant_id`, `ricetta_id`, `codice`)", allergens
        )
        self.assertIn("FOREIGN KEY (`tenant_id`, `ricetta_id`)", allergens)
        self.assertIn("chk_ricetta_allergeni_codice", allergens)

    def test_lot_expiration_and_best_before_are_mutually_exclusive(self):
        definition = self.tables["lotti"]
        self.assertRegex(definition, r"`data_scadenza`\s+date DEFAULT NULL")
        self.assertRegex(definition, r"`data_tmc`\s+date DEFAULT NULL")
        self.assertRegex(
            definition,
            r"CHECK\s*\(`data_scadenza` IS NULL OR `data_tmc` IS NULL\)",
        )

    def test_department_and_operator_relations_are_tenant_scoped(self):
        self.assertIn(
            "FOREIGN KEY (`tenant_id`, `reparto`)", self.tables["dipendenti"]
        )
        self.assertIn(
            "FOREIGN KEY (`tenant_id`, `Id_Reparto`)", self.tables["merceologie"]
        )
        self.assertIn(
            "FOREIGN KEY (`tenant_id`, `operatore_id`)", self.tables["lavorazioni"]
        )


if __name__ == "__main__":
    unittest.main()
