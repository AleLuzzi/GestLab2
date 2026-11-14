import os
import unittest
from unittest.mock import patch

from core.env import get_secret, valida_hosting_gestito
from saas import auth
from saas.print_agent import _leggi_token_config


class SecretConfigurationTests(unittest.TestCase):
    def test_production_secret_comes_from_environment(self):
        config = patch("core.config.get_config")
        with config as get_config, patch.dict(
            os.environ,
            {"GESTLAB_ENV": "production", "DB_PWD": "environment-secret"},
            clear=True,
        ):
            self.assertEqual(get_secret("DB_PWD", "default"), "environment-secret")

        get_config.assert_not_called()

    def test_production_does_not_fall_back_to_config_ini(self):
        config = patch(
            "core.config.get_config",
            return_value={"DataBase": {"pwd": "ini-secret"}},
        )
        with config as get_config, patch.dict(
            os.environ, {"GESTLAB_ENV": "production"}, clear=True
        ):
            self.assertEqual(get_secret("DB_PWD", "missing"), "missing")

        get_config.assert_not_called()

    def test_development_keeps_config_ini_compatibility(self):
        config = patch(
            "core.config.get_config",
            return_value={"DataBase": {"pwd": "ini-secret"}},
        )
        with config as get_config, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_secret("DB_PWD", "missing"), "ini-secret")

        get_config.assert_called_once_with()

    def test_print_agent_uses_environment_token_in_production(self):
        config = patch("core.config.get_config")
        with config as get_config, patch.dict(
            os.environ,
            {"GESTLAB_ENV": "production", "GESTLAB_AGENT_TOKEN": "environment-token"},
            clear=True,
        ):
            self.assertEqual(_leggi_token_config(), "environment-token")

        get_config.assert_not_called()

    def test_staging_does_not_fall_back_to_config_ini(self):
        config = patch(
            "core.config.get_config",
            return_value={"DataBase": {"pwd": "ini-secret"}},
        )
        with config as get_config, patch.dict(
            os.environ, {"GESTLAB_ENV": "staging"}, clear=True
        ):
            self.assertEqual(get_secret("DB_PWD", "missing"), "missing")

        get_config.assert_not_called()


def _ambiente_gestito(ambiente="production"):
    altro = "staging" if ambiente == "production" else "production"
    dominio = "app.example.com" if ambiente == "production" else "staging.example.com"
    return {
        "GESTLAB_HOSTING": "managed",
        "GESTLAB_ENV": ambiente,
        "GESTLAB_PUBLIC_URL": f"https://{dominio}",
        "DB_HOST": f"{ambiente}.db.example.com",
        "DB_NAME": f"gestlab_{ambiente}",
        "DB_SSL_CA": "/etc/ssl/certs/rds-global-bundle.pem",
        "GESTLAB_SECRET_SOURCE": "secrets-manager",
        "GESTLAB_DB_BACKUP": "pitr",
        "GESTLAB_PEER_DB_HOST": f"{altro}.db.example.com",
        "GESTLAB_PEER_DB_NAME": f"gestlab_{altro}",
    }


class ManagedHostingTests(unittest.TestCase):
    def test_lightsail_test_is_not_subject_to_the_managed_profile(self):
        with patch.dict(os.environ, {"GESTLAB_ENV": "production"}, clear=True):
            valida_hosting_gestito()

    def test_managed_production_and_staging_accept_separate_databases(self):
        for ambiente in ("production", "staging"):
            with self.subTest(ambiente=ambiente), patch.dict(
                os.environ, _ambiente_gestito(ambiente), clear=True
            ):
                valida_hosting_gestito()

    def test_managed_profile_rejects_http_local_db_and_shared_server(self):
        casi = (
            ("GESTLAB_PUBLIC_URL", "http://app.example.com", "HTTPS"),
            ("DB_HOST", "127.0.0.1", "non può essere locale"),
            ("DB_SSL_CA", "", "DB_SSL_CA è obbligatorio"),
            ("DB_NAME", "gestlab", "deve chiamarsi gestlab_production"),
            ("GESTLAB_SECRET_SOURCE", "env", "Secret Manager"),
            ("GESTLAB_DB_BACKUP", "snapshot", "point-in-time recovery"),
            ("GESTLAB_PEER_DB_HOST", "production.db.example.com", "stesso server"),
            ("GESTLAB_PEER_DB_NAME", "gestlab_production", "gestlab_staging"),
        )
        for chiave, valore, messaggio in casi:
            ambiente = _ambiente_gestito()
            ambiente[chiave] = valore
            with self.subTest(chiave=chiave), patch.dict(
                os.environ, ambiente, clear=True
            ):
                with self.assertRaisesRegex(RuntimeError, messaggio):
                    valida_hosting_gestito()

    def test_staging_domain_must_identify_the_environment(self):
        ambiente = _ambiente_gestito("staging")
        ambiente["GESTLAB_PUBLIC_URL"] = "https://app.example.com"
        with patch.dict(os.environ, ambiente, clear=True):
            with self.assertRaisesRegex(RuntimeError, "staging nel dominio"):
                valida_hosting_gestito()


class JwtSecretProductionTests(unittest.TestCase):
    def test_production_rejects_known_default_secrets(self):
        defaults = (
            "cambia-questa-secret-key",
            "change_me_in_production_please",
            "gestlab-dev-secret",
            "  cambia-questa-secret-key  ",
            "   ",
            "",
        )
        for secret in defaults:
            with self.subTest(secret=secret), patch.dict(
                os.environ,
                {"GESTLAB_ENV": " Production ", "JWT_SECRET": secret},
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "JWT_SECRET di default"):
                    auth.resolve_jwt_secret()

    def test_production_rejects_legacy_environment_default(self):
        with patch.dict(
            os.environ,
            {"GESTLAB_ENV": "production", "GESTLAB_JWT_SECRET": "gestlab-dev-secret"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "JWT_SECRET di default"):
                auth.resolve_jwt_secret()

    def test_production_ignores_config_ini_and_rejects_builtin_default(self):
        config = patch(
            "core.config.get_config",
            return_value={"Auth": {"jwt_secret": "change_me_in_production_please"}},
        )
        with config as get_config, patch.dict(
            os.environ, {"GESTLAB_ENV": "production"}, clear=True
        ):
            with self.assertRaisesRegex(RuntimeError, "JWT_SECRET di default"):
                auth.resolve_jwt_secret()

        get_config.assert_not_called()

    def test_production_accepts_dedicated_secret(self):
        secret = "una-chiave-lunga-casuale-non-di-sviluppo"
        with patch.dict(
            os.environ,
            {"GESTLAB_ENV": "production", "JWT_SECRET": secret},
            clear=True,
        ):
            self.assertEqual(auth.resolve_jwt_secret(), secret)

    def test_development_allows_default_secret(self):
        with patch.dict(
            os.environ, {"JWT_SECRET": "cambia-questa-secret-key"}, clear=True
        ):
            self.assertEqual(auth.resolve_jwt_secret(), "cambia-questa-secret-key")


if __name__ == "__main__":
    unittest.main()
