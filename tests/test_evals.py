from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import validate_evals


ROOT = Path(__file__).resolve().parents[1]


class EvalValidationTests(unittest.TestCase):
    def test_repository_eval_corpus_is_valid(self) -> None:
        errors, stats = validate_evals.validate(ROOT)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(stats["quality"], validate_evals.MIN_QUALITY_EVALS)
        self.assertGreaterEqual(stats["positive"], validate_evals.MIN_TRIGGER_POLARITY)
        self.assertGreaterEqual(stats["negative"], validate_evals.MIN_TRIGGER_POLARITY)
        self.assertGreaterEqual(stats["zero_ref"], 1)

    def test_rejects_quality_case_that_loads_too_many_references(self) -> None:
        case = {
            "skill_name": validate_evals.SKILL_NAME,
            "evals": [
                {
                    "id": 1,
                    "name": "over-routed-case",
                    "prompt": "Fukurou task",
                    "expected_output": "Do the task",
                    "files": [],
                    "expected_references": [
                        "references/debugging.md",
                        "references/frontend.md",
                        "references/review.md",
                    ],
                    "forbidden_references": [],
                    "expectations": ["Expectation one", "Expectation two"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evals.json"
            path.write_text(json.dumps(case), encoding="utf-8")
            errors: list[str] = []
            validate_evals.validate_quality(path, errors)
        self.assertTrue(any("progressive-disclosure limit" in error for error in errors))

    def test_rejects_trigger_corpus_without_negative_cases(self) -> None:
        cases = [
            {"query": f"Fukurou task {index}", "should_trigger": True, "reason": "Fukurou work"}
            for index in range(validate_evals.MIN_TRIGGER_EVALS)
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trigger_evals.json"
            path.write_text(json.dumps(cases), encoding="utf-8")
            errors: list[str] = []
            validate_evals.validate_triggers(path, errors)
        self.assertTrue(any("negative cases" in error for error in errors))

    def test_rejects_reference_expected_and_forbidden_together(self) -> None:
        case = {
            "skill_name": validate_evals.SKILL_NAME,
            "evals": [
                {
                    "id": 1,
                    "name": "contradictory-routing",
                    "prompt": "Fukurou task",
                    "expected_output": "Do the task",
                    "files": [],
                    "expected_references": ["references/frontend.md"],
                    "forbidden_references": ["references/frontend.md"],
                    "expectations": ["Expectation one", "Expectation two"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evals.json"
            path.write_text(json.dumps(case), encoding="utf-8")
            errors: list[str] = []
            validate_evals.validate_quality(path, errors)
        self.assertTrue(any("expects and forbids" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
