from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import live_benchmark as core

CODEX_REQUIRED_FLAGS = {
    "--ephemeral",
    "--ignore-user-config",
    "--json",
    "--output-last-message",
    "--output-schema",
    "--sandbox",
}
CLAUDE_REQUIRED_FLAGS = {
    "--allowedTools",
    "--disallowedTools",
    "--json-schema",
    "--max-budget-usd",
    "--max-turns",
    "--no-chrome",
    "--no-session-persistence",
    "--output-format",
    "--permission-mode",
    "--setting-sources",
}
INJECTED_SKILL_PREFIXES = (
    ".agents/skills/fukurou-development/",
    ".claude/skills/fukurou-development/",
)
ORIGINAL_CLAUDE_BUILDER = core.build_claude_command
ORIGINAL_TRACKED_CHANGES = core.tracked_changes


def requested_agents(argv: list[str]) -> list[str]:
    value = "both"
    for index, item in enumerate(argv):
        if item == "--agent" and index + 1 < len(argv):
            value = argv[index + 1]
        elif item.startswith("--agent="):
            value = item.split("=", 1)[1]
    if value == "both":
        return ["codex", "claude"]
    if value not in {"codex", "claude"}:
        raise RuntimeError(f"invalid --agent value {value!r}")
    return [value]


def help_text(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return (result.stdout or "") + "\n" + (result.stderr or "")


def preflight_agent(agent: str) -> dict[str, str]:
    executable = shutil.which(agent)
    if not executable:
        raise RuntimeError(f"{agent!r} executable was not found on PATH")

    version_result = subprocess.run(
        [executable, "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    version = (version_result.stdout or version_result.stderr).strip() or "unknown"

    if agent == "codex":
        help_output = help_text([executable, "exec", "--help"])
        required = CODEX_REQUIRED_FLAGS
    else:
        help_output = help_text([executable, "--help"])
        required = CLAUDE_REQUIRED_FLAGS

    missing = sorted(flag for flag in required if flag not in help_output)
    if missing:
        raise RuntimeError(
            f"{agent} CLI is missing benchmark-required flags: {', '.join(missing)}. "
            f"Detected version: {version}. Update the CLI before running paid evaluations."
        )
    return {"executable": executable, "version": version}


def guarded_tracked_changes(worktree: Path) -> list[str]:
    output = core.git_output(worktree, "status", "--porcelain", "--untracked-files=all")
    changes: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        path = line[3:].replace("\\", "/") if len(line) > 3 else ""
        if any(path.startswith(prefix) for prefix in INJECTED_SKILL_PREFIXES):
            continue
        changes.append(line)
    return changes


def guarded_claude_command(
    executable: str,
    prompt: str,
    model: str | None,
    max_turns: int,
    max_budget_usd: float,
) -> list[str]:
    command = ORIGINAL_CLAUDE_BUILDER(
        executable,
        prompt,
        model,
        max_turns,
        max_budget_usd,
    )
    prompt_value = command.pop()
    command.extend(["--disallowedTools", "Edit,Write,NotebookEdit", prompt_value])
    return command


def main() -> int:
    agents = requested_agents(sys.argv[1:])
    capabilities = {agent: preflight_agent(agent) for agent in agents}
    for agent, info in capabilities.items():
        print(f"preflight {agent}: {info['version']}", flush=True)

    try:
        core.tracked_changes = guarded_tracked_changes
        core.build_claude_command = guarded_claude_command
        return core.main()
    finally:
        core.tracked_changes = ORIGINAL_TRACKED_CHANGES
        core.build_claude_command = ORIGINAL_CLAUDE_BUILDER


if __name__ == "__main__":
    raise SystemExit(main())
