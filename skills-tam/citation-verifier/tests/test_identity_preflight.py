"""Ensure the verifier uses the executable identity check, with honest scope."""

import contextlib
import io
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


class IdentityPreflightTests(unittest.TestCase):
    def test_verifier_routes_bibliographies_to_identity_validator(self):
        text = SKILL.read_text()
        for required in ["validate_citations.py", "--check-dois", "citation-identity-report.json"]:
            self.assertTrue(required in text, f"Missing executable preflight element: {required}")

    def test_incomplete_identity_check_does_not_establish_claim_support(self):
        text = SKILL.read_text().lower()
        for required in ["identity preflight", "claim support", "unverified"]:
            self.assertTrue(required in text, f"Missing verification-scope distinction: {required}")

    def test_first_author_identity_is_not_satisfied_by_any_coauthor(self):
        text = SKILL.read_text()
        self.assertFalse("first author's surname appears in the Crossref author list" in text)
        self.assertTrue("Crossref first author" in text)

    def test_fabrication_rule_requires_completed_crossref_check(self):
        text = SKILL.read_text()
        row = next(line for line in text.splitlines() if line.startswith("| `FABRICATED`"))
        self.assertTrue("Crossref" in row, "Fabrication rule omits registry evidence")
        self.assertTrue("completed" in row, "Failed requests are not completed negative searches")

    def test_manual_title_example_does_not_clear_meaningful_sign_mismatch(self):
        text = SKILL.read_text()
        start = text.index("from difflib import SequenceMatcher")
        code = text[start:].split('\n"\n```', 1)[0]
        code = code.replace("CITED_TITLE", "Growth outcomes in HIV+ children")
        code = code.replace("CROSSREF_TITLE", "Growth outcomes in HIV- children")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(code, "manual-title-example", "exec"), {})
        self.assertNotIn("FLAG:TITLE_OK", output.getvalue())


if __name__ == "__main__":
    unittest.main()
