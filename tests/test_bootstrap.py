import unittest

from saas.bootstrap import _migra_progressivi_tenant


class FakeCursor:
    def __init__(self, duplicates=(), indexes=()):
        self.duplicates = list(duplicates)
        self.indexes = list(indexes)
        self.rowcount = 0
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith("SELECT tenant_id"):
            self.result = self.duplicates
        elif query.startswith("SHOW INDEX"):
            self.result = self.indexes
        elif query.startswith("DELETE FROM progressivi"):
            self.rowcount = params[1]
        else:
            self.result = []

    def fetchall(self):
        return self.result


class ProgressiviMigrationTests(unittest.TestCase):
    def test_consolidates_duplicate_tenants_preserving_highest_counters(self):
        cursor = FakeCursor(duplicates=[(42, 12, 18, 3)])

        _migra_progressivi_tenant(cursor)

        self.assertIn(
            (
                "UPDATE progressivi SET prog_acq = %s, prog_ven = %s "
                "WHERE tenant_id = %s",
                (12, 18, 42),
            ),
            cursor.statements,
        )
        self.assertIn(
            ("DELETE FROM progressivi WHERE tenant_id = %s LIMIT %s", (42, 2)),
            cursor.statements,
        )
        self.assertIn(
            (
                "ALTER TABLE progressivi "
                "ADD UNIQUE KEY uq_progressivi_tenant_id (tenant_id)",
                None,
            ),
            cursor.statements,
        )

    def test_does_not_recreate_existing_single_column_unique_index(self):
        cursor = FakeCursor(indexes=[(0, 0, "uq_progressivi_tenant_id", 1, "tenant_id")])

        _migra_progressivi_tenant(cursor)

        self.assertFalse(
            any(query.startswith("ALTER TABLE progressivi") for query, _ in cursor.statements)
        )


if __name__ == "__main__":
    unittest.main()
