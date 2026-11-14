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
        self.assertEqual(len(self.tables), 27)
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

    def test_sales_document_and_lines_are_persisted_tenant_scoped(self):
        sale = self.tables["vendite"]
        self.assertRegex(sale, r"`numero`\s+bigint unsigned NOT NULL")
        self.assertRegex(sale, r"`data_vendita`\s+datetime NOT NULL")
        self.assertRegex(sale, r"`cliente_id`\s+bigint DEFAULT NULL")
        self.assertIn("UNIQUE KEY `uq_vendite_tenant_numero` (`tenant_id`, `numero`)", sale)
        self.assertIn("CHECK (`tipo_documento` IN ('DDT', 'RICEVUTA'))", sale)
        self.assertIn("FOREIGN KEY (`tenant_id`, `cliente_id`)", sale)

        lines = self.tables["righe_vendita"]
        self.assertRegex(lines, r"`quantita`\s+decimal\(12,3\) NOT NULL")
        self.assertRegex(lines, r"`prezzo_unitario`\s+decimal\(12,4\) NOT NULL")
        self.assertRegex(lines, r"`iva_percentuale`\s+decimal\(5,2\) NOT NULL")
        self.assertIn("FOREIGN KEY (`tenant_id`, `vendita_id`)", lines)
        self.assertIn("FOREIGN KEY (`tenant_id`, `lotto_id`)", lines)
        self.assertIn("FOREIGN KEY (`tenant_id`, `articolo_id`)", lines)
        self.assertIn("`quantita` > 0", lines)
        self.assertIn("`iva_percentuale` <= 100", lines)

    def test_lot_expiration_and_best_before_are_mutually_exclusive(self):
        definition = self.tables["lotti"]
        self.assertRegex(definition, r"`data_scadenza`\s+date DEFAULT NULL")
        self.assertRegex(definition, r"`data_tmc`\s+date DEFAULT NULL")
        self.assertRegex(
            definition,
            r"CHECK\s*\(`data_scadenza` IS NULL OR `data_tmc` IS NULL\)",
        )

    def test_password_reset_keeps_only_the_token_hash(self):
        definition = self.tables["password_reset"]
        self.assertRegex(definition, r"`token_hash`\s+char\(64\)")
        self.assertRegex(definition, r"`scade_il`\s+datetime NOT NULL")
        self.assertRegex(definition, r"`usato_il`\s+datetime DEFAULT NULL")
        self.assertIn("UNIQUE KEY `uq_password_reset_token` (`token_hash`)", definition)
        self.assertIn(
            "FOREIGN KEY (`utente_id`) REFERENCES `utenti` (`id`)", definition
        )
        self.assertIn("fk_password_reset_utente", definition)

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
