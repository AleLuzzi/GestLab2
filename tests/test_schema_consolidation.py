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
        self.assertEqual(len(self.tables), 21)
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
