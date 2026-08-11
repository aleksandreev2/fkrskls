from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

CORE_SPEC = importlib.util.spec_from_file_location("live_benchmark", SCRIPTS / "live_benchmark.py")
assert CORE_SPEC and CORE_SPEC.loader
core = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(core)

import sys
sys.modules["live_benchmark"] = core
ENTRY_SPEC = importlib.util.spec_from_file_location("run_live_benchmark", SCRIPTS / "run_live_benchmark.py")
assert ENTRY_SPEC and ENTRY_SPEC.loader
entry = importlib.util.module_from_spec(ENTRY_SPEC)
ENTRY_SPEC.loader.exec_module(entry)


class BenchmarkEntrypointTests(unittest.TestCase):
    def test_requested_agents_supports_both_forms(self) -> None:
        self.assertEqual(entry.requested_agents([]), ["codex", "claude"])
        self.assertEqual(entry.requested_agents(["--agent", "codex"]), ["codex"])
        self.assertEqual(entry.requested_agents(["--agent=claude"]), ["claude"])

    def test_guarded_claude_command_explicitly_disallows_edit_tools(self) -> None:
        command = entry.guarded_claude_command("claude", "prompt", None, 8, 0.25)
        joined = " ".join(command)
        self.assertIn("--disallowedTools Edit,Write,NotebookEdit", joined)
        self.assertEqual(command[-1], "prompt")

    def test_guarded_tracked_changes_ignores_only_injected_skill_files(self) -> None:
        status = "\n".join(
            [
                "?? .codex/skills/fukurou-development/SKILL.md",
                "?? .agents/skills/fukurou-development/SKILL.md",
                "?? .claude/skills/fukurou-development/references/frontend.md",
                "?? accidental.py",
                " M tracked.py",
            ]
        )
        with mock.patch.object(entry.core, "git_output", return_value=status):
            changes = entry.guarded_tracked_changes(Path("repo"))
        self.assertEqual(changes, ["?? accidental.py", " M tracked.py"])

    def test_guard_ignores_replaced_or_removed_committed_codex_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            repo.mkdir()
            core.run_process(["git", "init"], cwd=repo)
            core.run_process(["git", "config", "user.email", "bench@example.test"], cwd=repo)
            core.run_process(["git", "config", "user.name", "Benchmark Test"], cwd=repo)
            old_skill = repo / ".codex/skills/fukurou-development/SKILL.md"
            old_skill.parent.mkdir(parents=True)
            old_skill.write_text("old skill\n", encoding="utf-8")
            core.run_process(["git", "add", ".codex"], cwd=repo)
            core.run_process(["git", "commit", "-m", "fixture"], cwd=repo)

            core.prepare_variant(repo, "codex", "skill")
            self.assertEqual(entry.guarded_tracked_changes(repo), [])
            core.prepare_variant(repo, "codex", "baseline")
            self.assertEqual(entry.guarded_tracked_changes(repo), [])

    def test_preflight_rejects_missing_required_flag_before_model_run(self) -> None:
        with mock.patch.object(entry.shutil, "which", return_value="/bin/codex"), \
             mock.patch.object(entry.subprocess, "run") as run:
            run.side_effect = [
                mock.Mock(stdout="codex-cli 1.0", stderr="", returncode=0),
                mock.Mock(stdout="--json --ephemeral", stderr="", returncode=0),
            ]
            with self.assertRaisesRegex(RuntimeError, "missing benchmark-required flags"):
                entry.preflight_agent("codex")

    def test_preflight_accepts_complete_codex_help(self) -> None:
        help_text = " ".join(sorted(entry.CODEX_REQUIRED_FLAGS))
        with mock.patch.object(entry.shutil, "which", return_value="/bin/codex"), \
             mock.patch.object(entry.subprocess, "run") as run:
            run.side_effect = [
                mock.Mock(stdout="codex-cli 1.0", stderr="", returncode=0),
                mock.Mock(stdout=help_text, stderr="", returncode=0),
            ]
            result = entry.preflight_agent("codex")
        self.assertEqual(result["version"], "codex-cli 1.0")

    def test_isolated_worktree_round_trip_with_real_git(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "source"
            repo.mkdir()
            core.run_process(["git", "init"], cwd=repo)
            core.run_process(["git", "config", "user.email", "bench@example.test"], cwd=repo)
            core.run_process(["git", "config", "user.name", "Benchmark Test"], cwd=repo)
            (repo / "tracked.txt").write_text("original\n", encoding="utf-8")
            core.run_process(["git", "add", "tracked.txt"], cwd=repo)
            commit = core.run_process(["git", "commit", "-m", "fixture"], cwd=repo)
            self.assertEqual(commit.returncode, 0)

            with core.isolated_worktree(repo, "HEAD") as worktree:
                self.assertEqual((worktree / "tracked.txt").read_text(encoding="utf-8"), "original\n")
                core.prepare_variant(worktree, "codex", "skill")
                self.assertTrue((worktree / ".agents/skills/fukurou-development/SKILL.md").is_file())
                (worktree / "accidental.py").write_text("x = 1\n", encoding="utf-8")
                changes = entry.guarded_tracked_changes(worktree)
                self.assertEqual(changes, ["?? accidental.py"])


if __name__ == "__main__":
    unittest.main()
