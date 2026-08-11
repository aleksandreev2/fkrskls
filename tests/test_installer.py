from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "skills" / "fukurou-development" / "scripts" / "install.py"


class InstallerTests(unittest.TestCase):
    def run_installer(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INSTALLER), *args],
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_install_and_check_both_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_installer("--home", str(home))
            self.assertEqual(result.returncode, 0, result.stderr)

            codex = home / ".agents" / "skills" / "fukurou-development"
            claude = home / ".claude" / "skills" / "fukurou-development"
            self.assertTrue((codex / "SKILL.md").is_file())
            self.assertTrue((claude / "SKILL.md").is_file())
            self.assertTrue((codex / ".fukurou-managed-skill").is_file())
            self.assertTrue((claude / ".fukurou-managed-skill").is_file())

            check = self.run_installer("--home", str(home), "--check")
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            self.assertIn("codex: current", check.stdout)
            self.assertIn("claude: current", check.stdout)

    def test_stale_copy_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            self.assertEqual(self.run_installer("--home", str(home)).returncode, 0)

            target = home / ".claude" / "skills" / "fukurou-development" / "references" / "review.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")

            check = self.run_installer("--home", str(home), "--check")
            self.assertEqual(check.returncode, 1)
            self.assertIn("claude: stale", check.stdout)
            self.assertIn("codex: current", check.stdout)

    def test_unmanaged_destination_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            target = home / ".agents" / "skills" / "fukurou-development"
            target.mkdir(parents=True)
            (target / "owned-by-user.txt").write_text("keep", encoding="utf-8")

            refused = self.run_installer("--home", str(home), "--codex-only")
            self.assertEqual(refused.returncode, 2)
            self.assertIn("Refusing to replace unmanaged skill", refused.stderr)
            self.assertTrue((target / "owned-by-user.txt").is_file())

            forced = self.run_installer("--home", str(home), "--codex-only", "--force")
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertFalse((target / "owned-by-user.txt").exists())

    def test_installed_copy_cannot_be_update_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as second_temp:
            home = Path(temp)
            self.assertEqual(self.run_installer("--home", str(home), "--codex-only").returncode, 0)

            installed = home / ".agents" / "skills" / "fukurou-development" / "scripts" / "install.py"
            result = subprocess.run(
                [sys.executable, str(installed), "--home", second_temp, "--check"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("canonical fkrskls checkout", result.stderr)


if __name__ == "__main__":
    unittest.main()
