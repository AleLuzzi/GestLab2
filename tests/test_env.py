import os
import unittest
from unittest.mock import patch

from core.env import get_secret
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
