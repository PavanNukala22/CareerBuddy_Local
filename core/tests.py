from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from business_english_lms import settings as settings_module


def _fake_config(values):
    def fake_config(name, default=None, **kwargs):
        return values.get(name, default)
    return fake_config


class DatabaseSettingsTests(SimpleTestCase):
    """MySQL is the only supported database — see get_database_config()."""

    @patch("business_english_lms.settings.config")
    def test_uses_mysql(self, mock_config):
        mock_config.side_effect = _fake_config({
            "DB_NAME": "business_english_lms",
            "DB_USER": "root",
            "DB_PASSWORD": "",
            "DB_HOST": "localhost",
            "DB_PORT": "3306",
        })

        db_config = settings_module.get_database_config()

        self.assertEqual(db_config["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(db_config["NAME"], "business_english_lms")
        self.assertEqual(db_config["OPTIONS"]["charset"], "utf8mb4")

    @patch("business_english_lms.settings.config")
    def test_missing_db_password_still_uses_mysql(self, mock_config):
        """An empty password must never silently fall back to a local file."""
        mock_config.side_effect = _fake_config({"DB_PASSWORD": ""})

        self.assertEqual(
            settings_module.get_database_config()["ENGINE"],
            "django.db.backends.mysql",
        )

    @patch("business_english_lms.settings.config")
    def test_requesting_sqlite_fails_loudly(self, mock_config):
        mock_config.side_effect = _fake_config({"USE_SQLITE": True})

        with self.assertRaises(ImproperlyConfigured):
            settings_module.get_database_config()

    @patch("business_english_lms.settings.config")
    def test_db_engine_sqlite_fails_loudly(self, mock_config):
        mock_config.side_effect = _fake_config({"DB_ENGINE": "sqlite"})

        with self.assertRaises(ImproperlyConfigured):
            settings_module.get_database_config()
