import datetime
import io
import os
import tempfile
import unittest
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

from core import backup_database


class BackupCursor:
    def __init__(self, objects=()):
        self.objects = list(objects)
        self.rows = []
        self.description = []

    def execute(self, query):
        if query == "SHOW FULL TABLES":
            self.rows = self.objects
        elif query.startswith("SHOW CREATE TABLE"):
            self.rows = [
                ("items", "CREATE TABLE `items` (`id` int, `value` text)")
            ]
        elif query.startswith("SELECT * FROM"):
            self.description = [("id",), ("value",)]
            self.rows = [
                (1, "l'unità \\ test"),
                (2, None),
            ]
        else:
            self.rows = []

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchmany(self, size):
        rows, self.rows = self.rows[:size], self.rows[size:]
        return rows


class BackupConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class BackupDatabaseTests(unittest.TestCase):
    def test_sql_value_serializes_supported_values(self):
        self.assertEqual(backup_database._sql_value(None), "NULL")
        self.assertEqual(backup_database._sql_value(True), "1")
        self.assertEqual(backup_database._sql_value(Decimal("1.250")), "1.250")
        self.assertEqual(backup_database._sql_value(b"\x00\xff"), "X'00ff'")
        self.assertEqual(
            backup_database._sql_value("è"),
            "CONVERT(X'c3a8' USING utf8mb4)",
        )
        self.assertEqual(
            backup_database._sql_value(datetime.datetime(2026, 11, 7, 9, 5)),
            "CONVERT(X'323032362d31312d30372030393a30353a3030' USING utf8mb4)",
        )
        self.assertEqual(
            backup_database._sql_value(datetime.timedelta(hours=26, minutes=3)),
            "CONVERT(X'32363a30333a3030' USING utf8mb4)",
        )
        self.assertEqual(
            backup_database._sql_value(datetime.timedelta(microseconds=-500000)),
            "CONVERT(X'2d30303a30303a30302e353030303030' USING utf8mb4)",
        )

    def test_writes_table_schema_and_rows_with_counts(self):
        cursor = BackupCursor([("items", "BASE TABLE")])
        output = io.StringIO()

        counts = backup_database._scrivi_backup(cursor, output)

        self.assertEqual(counts, {"items": 2})
        self.assertIn("CREATE TABLE `items`", output.getvalue())
        self.assertIn("INSERT INTO `items` (`id`, `value`)", output.getvalue())
        self.assertIn("Righe esportate: 2", output.getvalue())
        self.assertIn("SET FOREIGN_KEY_CHECKS=1;", output.getvalue())

    def test_export_creates_backup_and_does_not_overwrite_existing_file(self):
        cursor = BackupCursor()
        fake_connection = BackupConnection(cursor)

        @contextmanager
        def fake_connection_context():
            yield fake_connection

        with tempfile.TemporaryDirectory() as directory:
            output_path = os.path.join(directory, "backup.sql")
            with patch.object(
                backup_database, "connection", fake_connection_context
            ):
                path, counts = backup_database.esporta_backup(output_path)

            self.assertEqual(path, output_path)
            self.assertEqual(counts, {})
            with open(path, encoding="utf-8") as backup:
                self.assertIn("Backup GestLab", backup.read())

            with open(output_path, "w", encoding="utf-8") as existing:
                existing.write("preservare")
            with patch.object(
                backup_database, "connection", fake_connection_context
            ):
                with self.assertRaises(FileExistsError):
                    backup_database.esporta_backup(output_path)
            with open(output_path, encoding="utf-8") as existing:
                self.assertEqual(existing.read(), "preservare")


if __name__ == "__main__":
    unittest.main()
