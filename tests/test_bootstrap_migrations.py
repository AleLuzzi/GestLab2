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


class BootstrapMigrationsTests(unittest.TestCase):
    def test_explicit_migration_order_covers_every_sql_file(self):
        files = {
            path.name for path in Path(bootstrap.MIGRATIONS_DIR).glob("*.sql")
        }

        self.assertEqual(set(bootstrap.MIGRATION_ORDER), files)
        self.assertEqual(len(bootstrap.MIGRATION_ORDER), len(files))

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


if __name__ == "__main__":
    unittest.main()
