import unittest
from types import SimpleNamespace

from fortune_agent.bazi_sources import evidence_for, load_catalog, load_ziping_catalog


class BaziSourceTests(unittest.TestCase):
    def test_all_ten_stems_have_unique_revision_cited_excerpts(self):
        catalog = load_catalog()
        self.assertEqual(len(catalog["entries"]), 10)
        self.assertEqual({entry["stem"] for entry in catalog["entries"]}, set("甲乙丙丁戊己庚辛壬癸"))
        self.assertEqual(len({entry["id"] for entry in catalog["entries"]}), 10)
        for entry in catalog["entries"]:
            with self.subTest(stem=entry["stem"]):
                self.assertTrue(entry["source_text"].startswith(entry["heading"]))
                self.assertIn(f"oldid={catalog['source']['revision_id']}", entry["source_url"])
                self.assertNotIn("{{", entry["source_text"])

    def test_retrieval_returns_only_computed_day_master(self):
        for stem in "甲乙丙丁戊己庚辛壬癸":
            with self.subTest(stem=stem):
                evidence = evidence_for(SimpleNamespace(day_master=stem))
                self.assertEqual(len(evidence), 8)
                self.assertEqual(evidence[0]["stem"], stem)
                self.assertEqual({entry["chapter"] for entry in evidence[1:]}, {"月令论", "衰旺论", "论用神", "论用神成败救应"})

    def test_unrecognized_stem_is_rejected(self):
        with self.assertRaises(ValueError):
            evidence_for(SimpleNamespace(day_master="错误"))

    def test_transcription_variant_is_preserved_with_note(self):
        evidence = evidence_for(SimpleNamespace(day_master="丁"))[0]
        self.assertIn("抱乙而考", evidence["source_text"])
        self.assertTrue(evidence["notes"])

    def test_ziping_excerpt_locations_preserve_printed_and_scan_pages(self):
        catalog = load_ziping_catalog()
        self.assertEqual(len(catalog["entries"]), 5)
        self.assertIsNone(catalog["source"]["publication_year"])
        self.assertEqual(catalog["source"]["scan_page_count"], 287)
        for entry in catalog["entries"]:
            self.assertEqual(len(entry["scan_pages"]), len(entry["printed_pages"]))
            self.assertTrue(entry["source_url"].endswith(f"#page={entry['scan_pages'][0]}"))
            self.assertTrue(set(entry["printed_pages"]) <= {17, 18, 19})

    def test_ziping_original_word_order_and_context_are_preserved(self):
        catalog = load_ziping_catalog()
        first = catalog["entries"][0]
        self.assertIn("以干日", first["source_text"])
        self.assertNotIn("以日干", first["source_text"])
        self.assertTrue(first["notes"])
        self.assertIn("设问", catalog["entries"][2]["notes"][0])


if __name__ == "__main__":
    unittest.main()
