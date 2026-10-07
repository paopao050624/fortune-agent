import os
import unittest
from unittest.mock import patch

from fortune_agent.config import api_status, configure_api
from fortune_agent.web import LocalApp


class ApiConfigTests(unittest.TestCase):
    def test_status_does_not_expose_key(self):
        with patch.dict(os.environ, {}, clear=True):
            status = api_status()
        self.assertFalse(status["configured"])
        self.assertNotIn("api_key", status)

    def test_configure_validates_and_applies_process_settings(self):
        with patch.dict(os.environ, {}, clear=True):
            result = configure_api(
                api_key="test-secret-key", base_url="https://relay.example/v1", model="gpt-6-sol", test=False
            )
            self.assertTrue(result["configured"])
            self.assertEqual(result["model"], "gpt-6-sol")
            self.assertNotIn("test-secret-key", str(result))

    def test_web_app_status_is_safe(self):
        with patch.dict(os.environ, {}, clear=True):
            result = LocalApp(__import__("pathlib").Path("/tmp/fortune-api-test.sqlite3")).run(
                {"mode": "api-config", "action": "status"}
            )
        self.assertFalse(result["configured"])
        self.assertNotIn("api_key", result)


if __name__ == "__main__":
    unittest.main()
