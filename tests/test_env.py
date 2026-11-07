import os
import unittest
from unittest.mock import patch

from core.env import get_secret
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


if __name__ == "__main__":
    unittest.main()
