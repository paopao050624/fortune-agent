import json
from types import SimpleNamespace
import unittest

from fortune_agent.iching import build_cast
from fortune_agent.iching_agent import interpret_cast, validate_interpretation
from fortune_agent.iching_reading import select_passages


def response_data(ids):
    return {"summary":"这是反思提示。", "explanations":[{"passage_id":identifier,
            "meaning":"历史语义。", "application":"先核实手头资料。"} for identifier in ids],
            "advice":["先完成一个小步骤。"], "limitations":["不保证未来结果。"]}


class InterpretationTests(unittest.TestCase):
    def test_prompt_receives_exact_cast_and_only_selected_texts(self):
        cast = build_cast([9,9,7,7,7,7])
        selection = select_passages(cast)
        ids = [p["id"] for p in selection["passages"]]
        class Responses:
            def create(self, **kwargs):
                self.request = kwargs
                return SimpleNamespace(output_text=json.dumps(response_data(ids),ensure_ascii=False))
        responses = Responses()
        result = interpret_cast(cast,"研究项目如何推进？",SimpleNamespace(responses=responses),"test-model")
        request = json.loads(responses.request["input"][0]["content"])
        self.assertEqual(request["selection"]["passages"], selection["passages"])
        self.assertEqual(request["cast"]["moving_positions"], [1,2])
        self.assertFalse(responses.request["store"])
        self.assertEqual(responses.request["text"]["format"]["type"], "json_schema")
        for passage in selection["passages"]:
            self.assertIn(passage["source_text"], result["interpretation"])
            self.assertIn(passage["source_url"], result["interpretation"])

    def test_missing_duplicate_and_invented_ids_are_rejected(self):
        ids = ["a", "b"]
        for kind in ("missing", "duplicate", "invented"):
            result = response_data(ids)
            if kind == "missing": result["explanations"].pop()
            elif kind == "duplicate": result["explanations"][1]["passage_id"] = "a"
            else: result["explanations"][1]["passage_id"] = "fake"
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                validate_interpretation(result,ids)

    def test_invalid_json_is_not_returned_as_an_interpretation(self):
        client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output_text="编造回答")))
        with self.assertRaises(RuntimeError):
            interpret_cast(build_cast([7]*6),"问题",client,"test-model")

    def test_empty_question_is_rejected_before_model_call(self):
        with self.assertRaises(ValueError):
            interpret_cast(build_cast([7]*6)," ",None,"test-model")


if __name__ == "__main__":
    unittest.main()
