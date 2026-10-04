import http.client
import importlib.util
import json
import re
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fortune_agent.web import LocalApp, make_server


class WebTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.server = make_server(0, Path(self.directory.name) / "daily.sqlite3")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        self.connection.request("GET", "/")
        response = self.connection.getresponse()
        page = response.read().decode()
        self.token = re.search(r'name="request-token" content="([^"]+)"', page).group(1)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def post(self, payload, token=None):
        self.connection.request("POST", "/api/run", body=json.dumps(payload), headers={
            "Content-Type": "application/json", "X-Fortune-Token": token or self.token,
        })
        response = self.connection.getresponse()
        return response.status, json.loads(response.read())

    def test_draw_is_local_and_selected_positions_are_validated(self):
        with patch.object(LocalApp, "model_client", side_effect=AssertionError("API must not be used")):
            status, data = self.post({"mode": "tarot", "question": "怎么安排学习？", "spread": "three", "picks": [1, 15, 78]})
        self.assertEqual(status, 200)
        self.assertEqual(len(data["reading"]["cards"]), 3)
        self.assertIsNone(data["interpretation"])
        status, _ = self.post({"mode": "tarot", "question": "学习", "spread": "three", "picks": [1, 1, 2]})
        self.assertEqual(status, 400)

    def test_daily_repeated_requests_have_same_reading(self):
        payload = {"mode": "daily", "profile": "web-reader", "timezone": "Asia/Shanghai"}
        status, first = self.post(payload)
        _, second = self.post(payload)
        self.assertEqual(status, 200)
        self.assertEqual(first["reading"], second["reading"])

    def test_iching_uses_supplied_six_lines_and_validates_question(self):
        with patch.object(LocalApp, "model_client", side_effect=AssertionError("No model for this mode")):
            status, data = self.post({"mode": "iching", "lines": [9] * 6})
            self.assertEqual(status, 200)
            self.assertEqual(data["cast"]["main_hexagram"]["name"], "乾")
            self.assertEqual(data["cast"]["changed_hexagram"]["name"], "坤")
            self.assertEqual(data["selection"]["passages"][0]["kind"], "用九")
            status, _ = self.post({"mode": "iching", "lines": [7] * 5})
            self.assertEqual(status, 400)
            status, _ = self.post({"mode": "iching", "interpret": True})
            self.assertEqual(status, 400)

    def test_full_iching_reference_available_without_model(self):
        status, data = self.post({"mode":"iching", "reference":1})
        self.assertEqual(status,200)
        self.assertEqual(len(data["reference"]["lines"]),6)
        self.assertIn("用九",data["reference"]["special"])

    def test_cross_site_requests_and_nonlocal_host_are_rejected(self):
        status, _ = self.post({"mode": "daily"}, token="wrong-token")
        self.assertEqual(status, 403)
        self.connection.request("GET", "/", headers={"Host": "external.example"})
        response = self.connection.getresponse()
        response.read()
        self.assertEqual(response.status, 403)

    def test_malformed_input_does_not_call_model(self):
        with patch.object(LocalApp, "model_client", side_effect=AssertionError("API must not be used")):
            status, _ = self.post({"mode": "tarot", "question": "学习", "picks": [True], "interpret": True})
        self.assertEqual(status, 400)

    def test_direct_pillars_without_calculator_dependency_and_conflicting_inputs(self):
        status, data = self.post({"mode": "bazi", "pillars": "己卯 丙子 戊午 戊午"})
        self.assertEqual(status, 200)
        self.assertIsNone(data["chart"]["birth_time"])
        self.assertEqual(data["chart"]["day_master"], "戊")
        status, _ = self.post({"mode": "bazi", "pillars": "甲丑 丙子 戊午 戊午"})
        self.assertEqual(status, 400)
        status, _ = self.post({"mode": "bazi", "pillars": "己卯 丙子 戊午 戊午",
                               "birth": "2000-01-01T12:00:00+08:00"})
        self.assertEqual(status, 400)

    def test_provider_error_details_are_not_sent_to_browser(self):
        with patch.object(LocalApp, "model_client", side_effect=Exception("secret-provider-detail")):
            status, data = self.post({"mode": "tarot", "question": "学习", "interpret": True})
        self.assertEqual(status, 502)
        self.assertNotIn("secret-provider-detail", str(data))

    def test_chat_clarifies_then_clear_invalidates_session(self):
        from test_unified_agent import FakeResponses,plan
        responses=FakeResponses([plan(method="bazi"),plan(method="bazi")])
        with patch.object(LocalApp,"model_client",return_value=(SimpleNamespace(responses=responses),"test-model")):
            status,data=self.post({"mode":"chat","message":"算八字"})
            self.assertEqual(status,200)
            self.assertEqual(data["status"],"needs_input")
            identifier=data["session_id"]
            status,data=self.post({"mode":"chat-clear","session_id":identifier})
            self.assertEqual(status,200)
            self.assertTrue(data["cleared"])
            status,_=self.post({"mode":"chat","session_id":identifier,"message":"再试"})
            self.assertEqual(status,400)

    def test_failed_chat_retains_session_and_actual_cards_for_retry(self):
        from test_unified_agent import FakeResponses,plan
        responses=FakeResponses([plan(question="学习安排"),plan(action="followup")])
        with patch.object(LocalApp,"model_client",return_value=(SimpleNamespace(responses=responses),"test-model")):
            with patch("fortune_agent.unified_agent.TarotAgent.read",side_effect=RuntimeError("fake-provider-private-error")):
                status,first=self.post({"mode":"chat","message":"塔罗看学习安排"})
            self.assertEqual(status,200)
            self.assertEqual(first["status"],"failed")
            self.assertNotIn("fake-provider-private-error",str(first))
            status,second=self.post({"mode":"chat","session_id":first["session_id"],"message":"重试解读"})
            self.assertEqual(status,200)
            self.assertEqual(second["result"]["reading"]["cards"],first["result"]["reading"]["cards"])
            self.assertTrue(second["trace"][-1]["reused"])

    def test_daily_interpretation_reuses_cache_without_model_configuration(self):
        class Responses:
            def __init__(self):
                self.calls = 0

            def create(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return SimpleNamespace(output=[SimpleNamespace(
                        type="function_call", name="draw_tarot", arguments="{}", call_id="web-daily",
                    )])
                return SimpleNamespace(output_text="先完成一件小事。")

        responses = Responses()
        payload = {"mode": "daily", "profile": "cached-web-reader", "timezone": "Asia/Shanghai", "interpret": True}
        with patch.object(LocalApp, "model_client", return_value=(SimpleNamespace(responses=responses), "test-model")):
            status, first = self.post(payload)
        with patch.object(LocalApp, "model_client", side_effect=AssertionError("Cached answer must not call model")):
            second_status, second = self.post(payload)
        self.assertEqual((status, second_status), (200, 200))
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(first["interpretation"], second["interpretation"])
        self.assertEqual(responses.calls, 2)

    @unittest.skipUnless(importlib.util.find_spec("lunar_python"), "optional calculator absent")
    def test_bazi_response_includes_source_and_unknown_conditions(self):
        status, data = self.post({"mode": "bazi", "birth": "2000-01-01T12:00:00+08:00"})
        self.assertEqual(status, 200)
        self.assertEqual(data["chart"]["day_master"], "戊")
        self.assertEqual(data["method_checklist"]["conclusion"], "undetermined")
        self.assertEqual(len(data["evidence"]), 8)

    @unittest.skipUnless(importlib.util.find_spec("lunar_python"),"optional calculator absent")
    def test_daily_bazi_returns_reference_facts_without_model(self):
        with patch.object(LocalApp,"model_client",side_effect=AssertionError("No model expected")):
            status,data=self.post({"mode":"bazi","pillars":"己卯 丙子 戊午 戊午","daily_bazi":True})
        self.assertEqual(status,200)
        self.assertIsNone(data["chart"]["birth_time"])
        self.assertEqual(data["daily_context"]["natal_day_master"],"戊")
        status,_=self.post({"mode":"bazi","pillars":"己卯 丙子 戊午 戊午","daily_bazi":"yes"})
        self.assertEqual(status,400)


if __name__ == "__main__":
    unittest.main()
