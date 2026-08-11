from __future__ import annotations

import importlib.util
import sys
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

    def test_prompt_preserves_multiline_unicode_task_text(self) -> None:
        prompt = live.benchmark_prompt({"prompt": "Проверь /levels.\nНаграды забираются вручную."})
        self.assertIn("TASK:\nПроверь /levels.\nНаграды забираются вручную.", prompt)

    def test_prompt_defines_references_as_specialized_skill_refs_only(self) -> None:
        prompt = live.benchmark_prompt({"prompt": "Inspect /levels."})
        self.assertIn("only specialized Fukurou skill references", prompt)
        self.assertIn("Do not include application source files, AGENTS.md, or SKILL.md", prompt)

    def test_run_process_preserves_multiline_unicode_stdin(self) -> None:
        payload = "TASK:\nПроверь /levels.\nPREMIUM — снизу."
        result = live.run_process(
            [sys.executable, "-c", "import sys; print(sys.stdin.read(), end='')"],
            input_text=payload,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, payload)

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
            self.assertFalse((worktree / ".codex/skills/fukurou-development").exists())
            self.assertFalse((worktree / ".claude/skills/fukurou-development").exists())
            live.prepare_variant(worktree, "claude", "skill")
            self.assertFalse((worktree / ".codex/skills/fukurou-development").exists())
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
        self.assertTrue(trace["skill_tool_signal"])
        self.assertFalse(trace["skill_entrypoint_command_signal"])
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
        self.assertIn("--approve-for-me", command)
        self.assertNotIn("--sandbox", command)
        self.assertNotIn("workspace-write", command)
        self.assertEqual(command[-1], "-")
        self.assertNotIn("prompt", command)

    def test_codex_environment_redirects_powershell_cache_out_of_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            shadow_home = Path(temp) / "shadow-home"
            env = live.codex_environment(shadow_home)
        self.assertEqual(env["HOME"], str(shadow_home))
        self.assertEqual(env["USERPROFILE"], str(shadow_home))
        self.assertEqual(
            env["PSModuleAnalysisCachePath"],
            str(shadow_home / "powershell" / "ModuleAnalysisCache"),
        )

    def test_masked_user_skill_is_restored_even_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = root / ".agents/skills/fukurou-development"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("fixture\n", encoding="utf-8")
            backup = root / "backup"
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                with live.masked_user_skills([skill], backup):
                    self.assertFalse(skill.exists())
                    self.assertTrue((backup / "skill-0/SKILL.md").is_file())
                    raise RuntimeError("fixture failure")
            self.assertTrue((skill / "SKILL.md").is_file())
            self.assertFalse(backup.exists())

    def test_codex_user_skill_discovery_does_not_mask_claude_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            codex_skill = root / ".agents/skills/fukurou-development"
            claude_skill = root / ".claude/skills/fukurou-development"
            codex_skill.mkdir(parents=True)
            claude_skill.mkdir(parents=True)
            actual = [path.resolve() for path in live.installed_user_skill_paths(root)]
            expected = [codex_skill.resolve()]
            self.assertEqual(actual, expected)

    def test_trace_records_skill_entrypoint_command_not_output_mention(self) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "Get-Content '.agents/skills/fukurou-development/SKILL.md'",
                    "aggregated_output": "Read references/review.md only when needed",
                    "exit_code": 0,
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "Get-Content '.agents/skills/fukurou-development/references/frontend.md'",
                    "aggregated_output": "frontend guidance",
                    "exit_code": 0,
                },
            },
        ]
        trace = live.extract_trace(events)
        self.assertTrue(trace["skill_signal"])
        self.assertTrue(trace["skill_entrypoint_command_signal"])
        self.assertFalse(trace["skill_tool_signal"])
        self.assertEqual(trace["reference_signals"], ["references/frontend.md"])

    def test_non_read_entrypoint_command_is_not_classified_as_actual_read(self) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "Test-Path '.agents/skills/fukurou-development/SKILL.md'",
                    "aggregated_output": "True",
                    "exit_code": 0,
                },
            }
        ]
        trace = live.extract_trace(events)
        self.assertTrue(trace["skill_entrypoint_command_signal"])
        self.assertNotIn("skill_entrypoint_read", trace)

    def test_trace_normalizes_codex_windows_escaped_paths(self) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": (
                        '"powershell.exe" -Command "Get-Content -Raw '
                        "'C:\\\\Users\\\\runneradmin\\\\repo\\\\.agents\\\\skills\\\\"
                        "fukurou-development\\\\SKILL.md'\""
                    ),
                    "aggregated_output": "skill contents",
                    "exit_code": 0,
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": (
                        "Get-Content 'C:\\\\repo\\\\.agents\\\\skills\\\\fukurou-development"
                        "\\\\references\\\\product-design.md'"
                    ),
                    "aggregated_output": "reference contents",
                    "exit_code": 0,
                },
            },
        ]
        trace = live.extract_trace(events)
        self.assertTrue(trace["skill_signal"])
        self.assertTrue(trace["skill_entrypoint_command_signal"])
        self.assertEqual(trace["reference_signals"], ["references/product-design.md"])

    def test_trace_ignores_skill_and_reference_names_found_only_in_output(self) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "git status --short",
                    "aggregated_output": "D .agents/skills/fukurou-development/SKILL.md references/review.md",
                    "exit_code": 0,
                },
            }
        ]
        trace = live.extract_trace(events)
        self.assertFalse(trace["skill_signal"])
        self.assertEqual(trace["reference_signals"], [])

    def test_git_output_preserves_porcelain_leading_space(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            live.run_process(["git", "init"], cwd=repo)
            live.run_process(["git", "config", "user.email", "bench@example.test"], cwd=repo)
            live.run_process(["git", "config", "user.name", "Benchmark Test"], cwd=repo)
            tracked = repo / "tracked.txt"
            tracked.write_text("before\n", encoding="utf-8")
            live.run_process(["git", "add", "tracked.txt"], cwd=repo)
            live.run_process(["git", "commit", "-m", "fixture"], cwd=repo)
            tracked.write_text("after\n", encoding="utf-8")
            status = live.git_output(repo, "status", "--porcelain")
        self.assertTrue(status.startswith(" M tracked.txt"), repr(status))

    def test_claude_command_uses_project_only_settings_and_budget_cap(self) -> None:
        command = live.build_claude_command("claude", "prompt", None, 8, 0.25)
        joined = " ".join(command)
        self.assertIn("--setting-sources project", joined)
        self.assertIn("--max-budget-usd 0.25", joined)
        self.assertIn("--json-schema", command)
        self.assertIn("stream-json", command)


if __name__ == "__main__":
    unittest.main()
