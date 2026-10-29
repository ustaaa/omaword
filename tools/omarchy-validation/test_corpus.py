"""Fault injection for the validator, independent of Rust build availability."""
import unittest
from corpus import check_warnings, compare, normalize, parse_results


class Gates(unittest.TestCase):
    def test_damage_is_failure_even_if_exit_zero(self):
        with self.assertRaisesRegex(ValueError, "lostSlides"):
            parse_results('file.open → {"lostSlides":["slide2.xml"],"damagedMedia":[],"missingFonts":[]}', [["file.open", {}]], "deck")

    def test_missing_damage_fields_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "missing damage"):
            parse_results('file.open → {"slides":2}', [["file.open", {}]], "deck")

    def test_nested_warning_and_no_oracle_are_failures(self):
        for value in ({"nested": {"warnings": ["loss"]}}, {"no_oracle": True}, {"damagedMedia": ["image1"]}):
            with self.assertRaises(ValueError):
                check_warnings(value)

    def test_missing_or_unsuccessful_command_result_fails(self):
        with self.assertRaises(ValueError):
            parse_results("", [["file.saveAs", {}]], "word")
        with self.assertRaises(ValueError):
            parse_results('file.saveAs: {"saved":false}', [["file.saveAs", {}]], "word")

    def test_normalization_keeps_content_styles_and_warnings(self):
        original = {"path": "/tmp/upstream/edited.docx", "properties": {"created": "a", "modified": "b", "author": "Author", "revision": 2}, "blocks": [{"font": "Liberation Sans"}], "warnings": ["keep"]}
        normalized = normalize(original, "word")
        self.assertEqual(normalized["path"], "edited.docx")
        self.assertEqual(normalized["properties"], {"author": "Author", "revision": 2})
        self.assertEqual(normalized["blocks"], original["blocks"])
        self.assertEqual(normalized["warnings"], ["keep"])
        self.assertEqual(original["properties"]["created"], "a")

    def test_each_comparison_gate_detects_regression(self):
        good = {"observations": [{"text": "hello"}], "render_sha256": ["abc"], "edit_results": [{"saved": True}]}
        for key, bad_value in (("observations", [{"text": "lost"}]), ("render_sha256", ["different"]), ("edit_results", [{"saved": False}])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                compare(good, dict(good, **{key: bad_value}), "word")


if __name__ == "__main__":
    unittest.main()
