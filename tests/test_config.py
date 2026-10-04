import os
import unittest
from unittest.mock import patch

from fortune_agent.config import ApiConfig


class ApiConfigTests(unittest.TestCase):
    def test_loads_relay_configuration(self):
        values = {
            "FORTUNE_API_KEY": "test-key",
            "FORTUNE_BASE_URL": "https://relay.example.com/v1/",
            "FORTUNE_MODEL": "example-model",
        }
        with patch.dict(os.environ, values):
            config = ApiConfig.from_env()
        self.assertEqual(config.base_url, "https://relay.example.com/v1")
        self.assertEqual(config.model, "example-model")

    def test_requires_every_setting(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "FORTUNE_API_KEY.*FORTUNE_BASE_URL.*FORTUNE_MODEL"):
                ApiConfig.from_env()

    def test_rejects_insecure_remote_url(self):
        values = {
            "FORTUNE_API_KEY": "test-key",
            "FORTUNE_BASE_URL": "http://relay.example.com/v1",
            "FORTUNE_MODEL": "example-model",
        }
        with patch.dict(os.environ, values):
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                ApiConfig.from_env()

    def test_allows_local_http_proxy(self):
        values = {
            "FORTUNE_API_KEY": "test-key",
            "FORTUNE_BASE_URL": "http://localhost:3000/v1",
            "FORTUNE_MODEL": "example-model",
        }
        with patch.dict(os.environ, values):
            self.assertEqual(ApiConfig.from_env().base_url, values["FORTUNE_BASE_URL"])
