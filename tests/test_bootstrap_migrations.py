import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from saas import bootstrap


class MigrationCursor:
    def __init__(self, applied=()):
        self.applied = list(applied)
        self.result = []
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith("SELECT `migration_id`"):
            self.result = [(migration,) for migration in self.applied]
        elif query.startswith("INSERT INTO `schema_migrations`"):
            self.applied.append(params[0])

    def fetchall(self):
        return self.result


class SchemaCursor:
    def __init__(self, columns, primary_keys):
        self.columns = columns
        self.primary_keys = primary_keys
        self.result = []

    def execute(self, query, params=None):
        if "information_schema.columns" in query:
            self.result = self.columns
        elif "information_schema.key_column_usage" in query:
            self.result = self.primary_keys
        else:
            raise AssertionError(f"Query inattesa: {query}")

    def fetchall(self):
        return self.result


class BootstrapMigrationsTests(unittest.TestCase):
    def test_explicit_migration_order_covers_every_sql_file(self):
        files = {
            path.name for path in Path(bootstrap.MIGRATIONS_DIR).glob("*.sql")
        }

        self.assertEqual(set(bootstrap.MIGRATION_ORDER), files)
        self.assertEqual(len(bootstrap.MIGRATION_ORDER), len(files))

    def test_tmc_migration_is_additive_and_recognized_only_when_complete(self):
        migration = "20261107_lotti_tmc.sql"
        sql = Path(bootstrap.MIGRATIONS_DIR, migration).read_text(encoding="utf-8")
        self.assertIn("ADD COLUMN `data_tmc` DATE NULL", sql)
        self.assertIn("CHECK (`data_scadenza` IS NULL OR `data_tmc` IS NULL)", sql)
        self.assertNotIn("UPDATE `lotti`", sql)

        class TmcSchemaCursor:
            def __init__(self, columns, create_table=""):
                self.columns = columns
                self.create_table = create_table
                self.result = []

            def execute(self, query, params=None):
                if query == "SHOW COLUMNS FROM `lotti`":
                    self.result = [(column,) for column in self.columns]
                elif query == "SHOW CREATE TABLE `lotti`":
                    self.result = [("lotti", self.create_table)]
                else:
                    raise AssertionError(f"Query inattesa: {query}")

            def fetchall(self):
                return self.result

            def fetchone(self):
                return self.result[0] if self.result else None

        self.assertFalse(
            bootstrap._migrazione_gia_applicata(
                TmcSchemaCursor({"data_scadenza"}), migration
            )
        )
        self.assertTrue(
            bootstrap._migrazione_gia_applicata(
                TmcSchemaCursor(
                    {"data_scadenza", "data_tmc"},
                    "CONSTRAINT `chk_lotti_data_scadenza_tmc` CHECK (...)",
                ),
                migration,
            )
        )

    def test_osa_tenant_migration_is_additive_and_recognized_only_when_complete(self):
        migration = "20261108_dati_osa_tenant.sql"
        self.assertIn(migration, bootstrap.MIGRATION_ORDER)
        sql = Path(bootstrap.MIGRATIONS_DIR, migration).read_text(encoding="utf-8")
        for column in (
            "osa_ragione_sociale",
            "osa_indirizzo",
            "osa_laboratorio",
            "osa_partita_iva",
        ):
            self.assertIn(f"ADD COLUMN `{column}`", sql)

        class OsaCursor:
            def __init__(self, columns):
                self.columns = columns
                self.result = []

            def execute(self, query, params=None):
                if query == "SHOW COLUMNS FROM `tenant`":
                    self.result = [(column,) for column in self.columns]
                else:
                    raise AssertionError(f"Query inattesa: {query}")

            def fetchall(self):
                return self.result

        required = {
            "osa_ragione_sociale",
            "osa_indirizzo",
            "osa_laboratorio",
            "osa_partita_iva",
        }
        self.assertFalse(
            bootstrap._migrazione_gia_applicata(
                OsaCursor(required - {"osa_laboratorio"}), migration
            )
        )
        self.assertTrue(
            bootstrap._migrazione_gia_applicata(OsaCursor(required), migration)
        )

    def test_work_recipe_migration_is_ordered_and_requires_column_and_foreign_key(self):
        migration = "20261108_lavorazioni_ricetta.sql"
        self.assertIn(migration, bootstrap.MIGRATION_ORDER)
        sql = Path(bootstrap.MIGRATIONS_DIR, migration).read_text(encoding="utf-8")
        self.assertIn("ADD COLUMN `ricetta_id`", sql)
        self.assertIn("REFERENCES `ricette` (`tenant_id`, `id`)", sql)

        class RecipeWorkCursor:
            def __init__(self, columns, create_table):
                self.columns = columns
                self.create_table = create_table
                self.result = []

            def execute(self, query, params=None):
                if query == "SHOW COLUMNS FROM `lavorazioni`":
                    self.result = [(column,) for column in self.columns]
                elif query == "SHOW CREATE TABLE `lavorazioni`":
                    self.result = [("lavorazioni", self.create_table)]
                else:
                    raise AssertionError(f"Query inattesa: {query}")

            def fetchall(self):
                return self.result

            def fetchone(self):
                return self.result[0] if self.result else None

        applied_schema = (
            "CONSTRAINT `fk_lavorazioni_ricetta` FOREIGN KEY (...) "
            "KEY `idx_lavorazioni_ricetta` (...)"
        )
        self.assertFalse(
            bootstrap._migrazione_gia_applicata(
                RecipeWorkCursor({"id"}, applied_schema), migration
            )
        )
        self.assertFalse(
            bootstrap._migrazione_gia_applicata(
                RecipeWorkCursor({"id", "ricetta_id"}, ""), migration
            )
        )
        self.assertTrue(
            bootstrap._migrazione_gia_applicata(
                RecipeWorkCursor({"id", "ricetta_id"}, applied_schema), migration
            )
        )

    def test_new_database_records_current_schema_as_migration_baseline(self):
        cursor = MigrationCursor()
        commits = []

        bootstrap._applica_migrazioni(
            cursor, lambda: commits.append(True), database_nuovo=True
        )

        self.assertEqual(cursor.applied, list(bootstrap.MIGRATION_ORDER))
        self.assertEqual(len(commits), len(bootstrap.MIGRATION_ORDER))
        self.assertFalse(
            any(query.startswith("ALTER TABLE") for query, _ in cursor.statements)
        )

    def test_existing_database_applies_each_pending_migration_in_order(self):
        cursor = MigrationCursor()
        commits = []

        with tempfile.TemporaryDirectory() as migrations_dir:
            for migration in bootstrap.MIGRATION_ORDER:
                Path(migrations_dir, migration).write_text(
                    f"SELECT '{migration}';\n", encoding="utf-8"
                )
            with patch.object(bootstrap, "MIGRATIONS_DIR", migrations_dir), patch.object(
                bootstrap, "_migrazione_gia_applicata", return_value=False
            ):
                bootstrap._applica_migrazioni(
                    cursor, lambda: commits.append(True)
                )

        executed = [
            query.split("'")[1]
            for query, params in cursor.statements
            if query.startswith("SELECT '")
        ]
        self.assertEqual(executed, list(bootstrap.MIGRATION_ORDER))
        self.assertEqual(cursor.applied, list(bootstrap.MIGRATION_ORDER))
        self.assertEqual(len(commits), len(bootstrap.MIGRATION_ORDER))

    def test_migration_execution_errors_are_not_marked_as_applied(self):
        class FailingCursor(MigrationCursor):
            def execute(self, query, params=None):
                if query.startswith("SELECT '"):
                    raise RuntimeError("migration failed")
                super().execute(query, params)

        cursor = FailingCursor()
        with tempfile.TemporaryDirectory() as migrations_dir:
            for migration in bootstrap.MIGRATION_ORDER:
                Path(migrations_dir, migration).write_text(
                    f"SELECT '{migration}';\n", encoding="utf-8"
                )
            with patch.object(bootstrap, "MIGRATIONS_DIR", migrations_dir), patch.object(
                bootstrap, "_migrazione_gia_applicata", return_value=False
            ):
                with self.assertRaisesRegex(RuntimeError, "migration failed"):
                    bootstrap._applica_migrazioni(cursor, lambda: None)

        self.assertEqual(cursor.applied, [])

    def test_schema_verification_accepts_required_columns_and_primary_keys(self):
        required = bootstrap._schema_richiesto()
        columns = [
            (table_name, column_name)
            for table_name, table_columns in required.items()
            for column_name in table_columns
        ]
        primary_keys = [(table_name,) for table_name in required]

        bootstrap._verifica_schema(SchemaCursor(columns, primary_keys))

    def test_schema_verification_rejects_missing_columns_or_primary_keys(self):
        required = bootstrap._schema_richiesto()
        table_name = next(iter(required))
        column_name = next(iter(required[table_name]))
        columns = [
            (name, column)
            for name, table_columns in required.items()
            for column in table_columns
            if (name, column) != (table_name, column_name)
        ]
        primary_keys = [(name,) for name in required if name != table_name]

        with self.assertRaisesRegex(
            RuntimeError,
            f"{table_name}: colonne mancanti|{table_name}: chiave primaria assente",
        ):
            bootstrap._verifica_schema(SchemaCursor(columns, primary_keys))


if __name__ == "__main__":
    unittest.main()
