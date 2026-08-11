from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "live_benchmark.py"
SPEC = importlib.util.spec_from_file_location("live_benchmark", MODULE_PATH)
assert SPEC and SPEC.loader
live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(live)


class LiveBenchmarkTests(unittest.TestCase):
    def test_prompt_does_not_leak_expected_references_or_answers(self) -> None:
        case = {
            "prompt": "@GitHub fukurouserver Fix the reader bug.",
            "expected_output": "SECRET EXPECTED ANSWER",
            "expected_references": ["references/debugging.md"],
        }
        prompt = live.benchmark_prompt(case)
        self.assertIn("Fix the reader bug", prompt)
        self.assertNotIn("SECRET EXPECTED ANSWER", prompt)
        self.assertNotIn("references/debugging.md", prompt)

    def test_runtime_skill_excludes_eval_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skill"
            live.copy_runtime_skill(destination)
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertTrue((destination / "references" / "debugging.md").is_file())
            self.assertFalse((destination / "evals").exists())
            self.assertFalse((destination / "scripts").exists())

    def test_prepare_variant_uses_host_specific_project_location(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            worktree = Path(temp)
            live.prepare_variant(worktree, "codex", "skill")
            self.assertTrue((worktree / ".agents/skills/fukurou-development/SKILL.md").is_file())
            self.assertFalse((worktree / ".claude/skills/fukurou-development").exists())
            live.prepare_variant(worktree, "claude", "skill")
            self.assertFalse((worktree / ".agents/skills/fukurou-development").exists())
            self.assertTrue((worktree / ".claude/skills/fukurou-development/SKILL.md").is_file())
            live.prepare_variant(worktree, "claude", "baseline")
            self.assertFalse((worktree / ".claude/skills/fukurou-development").exists())

    def test_codex_usage_is_summed_from_completed_turns(self) -> None:
        events = [
            {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10, "reasoning_output_tokens": 3}},
            {"type": "turn.completed", "usage": {"input_tokens": 50, "cached_input_tokens": 40, "output_tokens": 5, "reasoning_output_tokens": 2}},
        ]
        usage = live.extract_usage("codex", events)
        self.assertEqual(usage["input_tokens"], 150)
        self.assertEqual(usage["cached_input_tokens"], 120)
        self.assertEqual(usage["output_tokens"], 15)
        self.assertEqual(usage["reasoning_output_tokens"], 5)

    def test_claude_usage_and_structured_output(self) -> None:
        structured = {
            "summary": "x",
            "references_used": ["references/frontend.md"],
        }
        events = [
            {
                "type": "result",
                "subtype": "success",
                "usage": {"input_tokens": 90, "cache_read_input_tokens": 60, "output_tokens": 20},
                "total_cost_usd": 0.04,
                "num_turns": 4,
                "structured_output": structured,
            }
        ]
        usage = live.extract_usage("claude", events)
        self.assertEqual(usage["input_tokens"], 90)
        self.assertEqual(usage["cached_input_tokens"], 60)
        self.assertEqual(usage["output_tokens"], 20)
        self.assertEqual(usage["cost_usd"], 0.04)
        self.assertEqual(usage["num_turns"], 4)
        self.assertEqual(live.extract_structured("claude", events, Path("missing")), structured)

    def test_skill_routing_score_detects_missing_and_forbidden_refs(self) -> None:
        case = {
            "expected_references": ["references/debugging.md", "references/frontend.md"],
            "forbidden_references": ["references/product-design.md"],
        }
        good = {"references_used": ["references/debugging.md", "references/frontend.md"]}
        bad = {"references_used": ["references/debugging.md", "references/product-design.md"]}
        self.assertTrue(live.score_routing(case, "skill", good)["pass"])
        scored = live.score_routing(case, "skill", bad)
        self.assertFalse(scored["pass"])
        self.assertEqual(scored["missing_expected"], ["references/frontend.md"])
        self.assertEqual(scored["forbidden_used"], ["references/product-design.md"])

    def test_baseline_flags_skill_reference_contamination(self) -> None:
        case = {"expected_references": [], "forbidden_references": []}
        clean = live.score_routing(case, "baseline", {"references_used": []})
        dirty = live.score_routing(case, "baseline", {"references_used": ["references/review.md"]})
        self.assertTrue(clean["pass"])
        self.assertFalse(dirty["pass"])
        self.assertEqual(dirty["baseline_skill_reference_contamination"], ["references/review.md"])

    def test_trace_detects_skill_tool_and_reference_signal(self) -> None:
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "id": "tool-1", "name": "Skill", "input": {"skill": "fukurou-development"}},
                        {"type": "tool_use", "id": "tool-2", "name": "Read", "input": {"file_path": "references/debugging.md"}},
                    ]
                },
            }
        ]
        trace = live.extract_trace(events)
        self.assertTrue(trace["skill_signal"])
        self.assertEqual(trace["reference_signals"], ["references/debugging.md"])
        self.assertEqual(trace["tool_calls"]["Skill"], 1)
        self.assertEqual(trace["tool_calls"]["Read"], 1)

    def test_codex_command_uses_ephemeral_json_and_ignores_user_config(self) -> None:
        command = live.build_codex_command(
            "codex",
            Path("repo"),
            "prompt",
            Path("result.json"),
            None,
        )
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("workspace-write", command)

    def test_claude_command_uses_project_only_settings_and_budget_cap(self) -> None:
        command = live.build_claude_command("claude", "prompt", None, 8, 0.25)
        joined = " ".join(command)
        self.assertIn("--setting-sources project", joined)
        self.assertIn("--max-budget-usd 0.25", joined)
        self.assertIn("--json-schema", command)
        self.assertIn("stream-json", command)


if __name__ == "__main__":
    unittest.main()
