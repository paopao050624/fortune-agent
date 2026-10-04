import json
import importlib.util
import unittest
from types import SimpleNamespace

from fortune_agent.agent import TarotAgent


class FakeResponses:
    def __init__(self, output_text="牌面提示你梳理当前选择。"):
        self.calls = []
        self.output_text = output_text

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(
                output=[SimpleNamespace(type="function_call", name="draw_tarot", arguments="{}", call_id="call-1")]
            )
        return SimpleNamespace(output_text=self.output_text)


class AgentTests(unittest.TestCase):
    def test_agent_uses_draw_tool_and_passes_exact_cards_to_model(self):
        responses = FakeResponses()
        result = TarotAgent(SimpleNamespace(responses=responses), "test-model").read(
            "我应该怎样安排学习？", "three", (1, 15, 78), "direct"
        )
        self.assertEqual(len(result.reading.cards), 3)
        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[0]["tool_choice"]["name"], "draw_tarot")
        self.assertEqual(responses.calls[1]["tool_choice"], "none")
        output = responses.calls[1]["input"][-1]
        self.assertEqual(output["type"], "function_call_output")
        self.assertEqual(output["call_id"], "call-1")
        payload = json.loads(output["output"])
        self.assertEqual(payload["question"], result.reading.question)
        self.assertEqual(
            [entry["card"]["id"] for entry in payload["cards"]],
            [entry.card.id for entry in result.reading.cards],
        )
        self.assertEqual(len(payload["source_meanings"]), len(result.reading.cards))
        self.assertEqual(payload["source_meanings"], list(result.evidence))
        self.assertFalse(responses.calls[0]["store"])
        self.assertFalse(responses.calls[1]["store"])

    def test_invalid_style_does_not_call_api(self):
        responses = FakeResponses()
        agent = TarotAgent(SimpleNamespace(responses=responses), "test-model")
        with self.assertRaises(ValueError):
            agent.read("学习", style="certain")
        self.assertEqual(responses.calls, [])

    def test_missing_tool_call_is_an_error(self):
        class MissingTool:
            def create(self, **kwargs):
                return SimpleNamespace(output=[])

        with self.assertRaisesRegex(RuntimeError, "draw_tarot"):
            TarotAgent(SimpleNamespace(responses=MissingTool()), "test-model").read("学习")

    def test_empty_interpretation_is_an_error(self):
        responses = FakeResponses("  ")
        with self.assertRaisesRegex(RuntimeError, "empty interpretation"):
            TarotAgent(SimpleNamespace(responses=responses), "test-model").read("学习")

    def test_baseline_mode_omits_source_meanings(self):
        responses = FakeResponses()
        agent = TarotAgent(SimpleNamespace(responses=responses), "test-model", use_sources=False)
        result = agent.read("学习")
        payload = json.loads(responses.calls[1]["input"][-1]["output"])
        self.assertNotIn("source_meanings", payload)
        self.assertEqual(result.evidence, ())

    @unittest.skipUnless(importlib.util.find_spec("openai"), "OpenAI optional dependency absent")
    def test_openai_sdk_serializes_both_requests(self):
        import httpx2
        from openai import OpenAI

        requests = []

        def respond(request):
            self.assertEqual(request.url.host, "relay.example.com")
            self.assertEqual(request.url.path, "/v1/responses")
            self.assertEqual(request.headers["authorization"], "Bearer test-only")
            requests.append(json.loads(request.content))
            if len(requests) == 1:
                output = [{
                    "type": "function_call", "name": "draw_tarot",
                    "arguments": "{}", "call_id": "call-1",
                }]
            else:
                output = [{
                    "type": "message", "id": "msg-1", "role": "assistant",
                    "status": "completed", "content": [{
                        "type": "output_text", "text": "先列出今天最重要的任务。", "annotations": [],
                    }],
                }]
            return httpx2.Response(200, json={
                "id": f"resp-{len(requests)}", "object": "response", "output": output,
            })

        client = OpenAI(
            api_key="test-only",
            base_url="https://relay.example.com/v1",
            http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
        )
        result = TarotAgent(client, "test-model").read("今天怎么安排学习？")
        self.assertIn("先列出", result.interpretation)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["tool_choice"]["name"], "draw_tarot")
        self.assertEqual(requests[1]["tool_choice"], "none")
        self.assertEqual(requests[1]["input"][-1]["call_id"], "call-1")
        self.assertFalse(requests[0]["store"])
        self.assertFalse(requests[1]["store"])


if __name__ == "__main__":
    unittest.main()
