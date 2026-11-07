from concurrent.futures import ThreadPoolExecutor
import os
import threading
import unittest
from unittest.mock import patch

from core import db


class DatabaseConnectionTests(unittest.TestCase):
    def setUp(self):
        self.pool_patch = patch.object(db, "_connection_pool", None)
        self.pool_patch.start()
        self.addCleanup(self.pool_patch.stop)

    def test_local_connection_does_not_require_tls(self):
        settings = {
            "DB_HOST": "127.0.0.1",
            "DB_PORT": "3306",
            "DB_NAME": "gestlab",
            "DB_USER": "gestlab_app",
            "DB_PWD": "secret",
            "DB_POOL_SIZE": "10",
            "DB_SSL_CA": "",
        }
        pool = unittest.mock.Mock()
        with patch.object(
            db, "get_secret", side_effect=lambda name, default="": settings.get(name, default)
        ), patch.dict(os.environ, {"GESTLAB_ENV": "production"}), patch.object(
            db.mysql.connector.pooling, "MySQLConnectionPool", return_value=pool
        ) as create_pool:
            connection = db.get_connection()

        self.assertIs(connection, pool.get_connection.return_value)
        self.assertEqual(
            create_pool.call_args.kwargs,
            {
                "pool_size": 10,
                "host": "127.0.0.1",
                "port": 3306,
                "database": "gestlab",
                "user": "gestlab_app",
                "password": "secret",
            },
        )

    def test_remote_production_connection_requires_ca_file(self):
        with patch.object(
            db, "get_secret", side_effect=lambda name, default="": {
                "DB_HOST": "db.example.com",
                "DB_SSL_CA": "",
            }.get(name, default)
        ), patch.dict(os.environ, {"GESTLAB_ENV": "production"}), patch.object(
            db.mysql.connector.pooling, "MySQLConnectionPool"
        ) as create_pool:
            with self.assertRaisesRegex(RuntimeError, "DB_SSL_CA è obbligatorio"):
                db.get_connection()

        create_pool.assert_not_called()

    def test_remote_connection_verifies_ca_and_server_identity(self):
        settings = {
            "DB_HOST": "db.example.com",
            "DB_PORT": "3306",
            "DB_NAME": "gestlab",
            "DB_USER": "gestlab_app",
            "DB_PWD": "secret",
            "DB_POOL_SIZE": "10",
            "DB_SSL_CA": "/etc/ssl/certs/rds-global-bundle.pem",
        }
        with patch.object(
            db, "get_secret", side_effect=lambda name, default="": settings.get(name, default)
        ), patch.dict(os.environ, {"GESTLAB_ENV": "production"}), patch.object(
            db.mysql.connector.pooling, "MySQLConnectionPool"
        ) as create_pool:
            db.get_connection()

        self.assertEqual(
            create_pool.call_args.kwargs["ssl_ca"],
            "/etc/ssl/certs/rds-global-bundle.pem",
        )
        self.assertTrue(create_pool.call_args.kwargs["ssl_verify_cert"])
        self.assertTrue(create_pool.call_args.kwargs["ssl_verify_identity"])

    def test_pool_reuses_connections_under_concurrent_load(self):
        connection_class = db.mysql.connector.connection.MySQLConnection
        connections = []

        def create_connection(**kwargs):
            connection = connection_class()
            connections.append(connection)
            return connection

        barrier = threading.Barrier(4)

        def use_pool():
            pooled_connection = db.get_connection()
            connection_id = id(pooled_connection._cnx)
            barrier.wait(timeout=5)
            pooled_connection.close()
            for _ in range(25):
                pooled_connection = db.get_connection()
                self.assertTrue(pooled_connection.is_connected())
                pooled_connection.close()
            return connection_id

        with patch.object(
            db, "get_secret", side_effect=lambda name, default="": {
                "DB_HOST": "localhost",
                "DB_POOL_SIZE": "4",
            }.get(name, default)
        ), patch.dict(os.environ, {"GESTLAB_ENV": "development"}), patch.object(
            db.mysql.connector.pooling, "connect", side_effect=create_connection
        ), patch.object(
            connection_class, "is_connected", return_value=True
        ), patch.object(
            connection_class, "reset_session"
        ):
            with ThreadPoolExecutor(max_workers=4) as executor:
                initial_connection_ids = set(executor.map(lambda _: use_pool(), range(4)))

        self.assertEqual(len(connections), 5)
        self.assertEqual(len(initial_connection_ids), 4)

    def test_pool_size_must_be_within_driver_limit(self):
        with patch.object(
            db, "get_secret", side_effect=lambda name, default="": {
                "DB_POOL_SIZE": "33",
            }.get(name, default)
        ), patch.object(
            db.mysql.connector.pooling, "MySQLConnectionPool"
        ) as create_pool:
            with self.assertRaisesRegex(ValueError, "DB_POOL_SIZE"):
                db.get_connection()

        create_pool.assert_not_called()


if __name__ == "__main__":
    unittest.main()
