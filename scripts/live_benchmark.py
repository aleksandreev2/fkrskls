from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "fukurou-development"
EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"
SUITES_PATH = ROOT / "benchmarks" / "suites.json"
SCHEMA_PATH = ROOT / "benchmarks" / "response_schema.json"
CANONICAL_REFERENCES = {
    "references/architecture.md",
    "references/debugging.md",
    "references/frontend.md",
    "references/product-design.md",
    "references/review.md",
}
REFERENCE_RE = re.compile(r"references/[A-Za-z0-9_.-]+\.md")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_process(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 900,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    stdout_handle = stdout_path.open("w", encoding="utf-8") if stdout_path else subprocess.PIPE
    stderr_handle = stderr_path.open("w", encoding="utf-8") if stderr_path else subprocess.PIPE
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
            timeout=timeout,
            check=False,
        )
    finally:
        if stdout_path:
            stdout_handle.close()  # type: ignore[union-attr]
        if stderr_path:
            stderr_handle.close()  # type: ignore[union-attr]


def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


@contextmanager
def isolated_worktree(repo: Path, ref: str) -> Iterator[Path]:
    root = Path(tempfile.mkdtemp(prefix="fukurou-bench-worktree-"))
    worktree = root / "repo"
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), ref],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        shutil.rmtree(root, ignore_errors=True)
        raise RuntimeError(result.stderr.strip() or "git worktree add failed")
    try:
        yield worktree
    finally:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
            text=True,
            capture_output=True,
            check=False,
        )
        shutil.rmtree(root, ignore_errors=True)


def remove_target_skill(worktree: Path) -> None:
    for relative in (
        Path(".agents/skills/fukurou-development"),
        Path(".claude/skills/fukurou-development"),
    ):
        shutil.rmtree(worktree / relative, ignore_errors=True)


def copy_runtime_skill(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SKILL_ROOT / "SKILL.md", destination / "SKILL.md")
    if (SKILL_ROOT / "references").is_dir():
        shutil.copytree(SKILL_ROOT / "references", destination / "references")
    if (SKILL_ROOT / "agents").is_dir():
        shutil.copytree(SKILL_ROOT / "agents", destination / "agents")


def prepare_variant(worktree: Path, agent: str, variant: str) -> None:
    remove_target_skill(worktree)
    if variant != "skill":
        return
    relative = (
        Path(".agents/skills/fukurou-development")
        if agent == "codex"
        else Path(".claude/skills/fukurou-development")
    )
    copy_runtime_skill(worktree / relative)


def benchmark_prompt(case: dict[str, Any]) -> str:
    prompt = str(case["prompt"]).replace("@GitHub fukurouserver", "In this Fukurou checkout,")
    return (
        "Solve the engineering task below as you normally would inside the current Fukurou repository. "
        "This run is planning-only: investigate enough to make a concrete implementation decision, but do not modify "
        "tracked source files. You may run repository diagnostics and Developer Intelligence commands that write ignored "
        "runtime state. Do not force or pretend to use a skill, reference, or workflow just because this is an evaluation. "
        "Use only guidance that the host actually makes available and that is relevant to the task.\n\n"
        f"TASK:\n{prompt}\n\n"
        "For the structured final response, `references_used` must contain only repository-relative supporting reference "
        "files you actually consulted during this run; use an empty array if none were consulted. "
        "`developer_intelligence_used` must reflect whether you actually used Fukurou Developer Intelligence. "
        "Keep `user_questions` empty unless an unresolved product/scope choice truly blocks a sound decision."
    )


def compact_schema() -> str:
    return json.dumps(load_json(SCHEMA_PATH), ensure_ascii=False, separators=(",", ":"))


def command_version(command: str) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    result = subprocess.run([executable, "--version"], text=True, capture_output=True, check=False)
    text = (result.stdout or result.stderr).strip()
    return text or None


def codex_environment(shadow_home: Path) -> dict[str, str]:
    env = os.environ.copy()
    real_home = Path.home()
    shadow_home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(shadow_home)
    env["USERPROFILE"] = str(shadow_home)
    env["CODEX_HOME"] = env.get("CODEX_HOME", str(real_home / ".codex"))
    return env


def build_codex_command(
    executable: str,
    worktree: Path,
    prompt: str,
    structured_path: Path,
    model: str | None,
) -> list[str]:
    command = [
        executable,
        "--cd",
        str(worktree),
    ]
    if model:
        command.extend(["--model", model])
    command.extend(
        [
            "exec",
            "--ephemeral",
            "--json",
            "--sandbox",
            "workspace-write",
            "--ignore-user-config",
            "--output-schema",
            str(SCHEMA_PATH),
            "--output-last-message",
            str(structured_path),
            prompt,
        ]
    )
    return command


def build_claude_command(
    executable: str,
    prompt: str,
    model: str | None,
    max_turns: int,
    max_budget_usd: float,
) -> list[str]:
    command = [
        executable,
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--json-schema",
        compact_schema(),
        "--max-turns",
        str(max_turns),
        "--max-budget-usd",
        str(max_budget_usd),
        "--permission-mode",
        "acceptEdits",
        "--setting-sources",
        "project",
        "--no-session-persistence",
        "--no-chrome",
        "--allowedTools",
        "Read,Glob,Grep,Skill,Bash(python tools/dev.py:*),Bash(git status:*),Bash(git diff:*)",
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    return command


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.is_file():
        return events
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def strings_in(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)


def extract_usage(agent: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    usage: dict[str, Any] = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
        "cost_usd": None,
        "num_turns": None,
    }
    if agent == "codex":
        for event in events:
            if event.get("type") != "turn.completed" or not isinstance(event.get("usage"), dict):
                continue
            current = event["usage"]
            for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"):
                value = current.get(key)
                if isinstance(value, int):
                    usage[key] += value
        return usage

    for event in reversed(events):
        if event.get("type") != "result":
            continue
        current = event.get("usage")
        if isinstance(current, dict):
            for key in ("input_tokens", "cache_read_input_tokens", "output_tokens"):
                value = current.get(key)
                if not isinstance(value, int):
                    continue
                target = "cached_input_tokens" if key == "cache_read_input_tokens" else key
                usage[target] = value
        if isinstance(event.get("total_cost_usd"), (int, float)):
            usage["cost_usd"] = event["total_cost_usd"]
        if isinstance(event.get("num_turns"), int):
            usage["num_turns"] = event["num_turns"]
        break
    return usage


def extract_structured(agent: str, events: list[dict[str, Any]], structured_path: Path) -> dict[str, Any] | None:
    if agent == "codex" and structured_path.is_file():
        try:
            value = json.loads(structured_path.read_text(encoding="utf-8-sig"))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None
    for event in reversed(events):
        value = event.get("structured_output")
        if isinstance(value, dict):
            return value
    return None


def extract_trace(events: list[dict[str, Any]]) -> dict[str, Any]:
    reference_signals: set[str] = set()
    skill_signal = False
    tool_calls: dict[str, int] = {}
    seen_tool_ids: set[str] = set()
    for event in events:
        joined = "\n".join(strings_in(event))
        reference_signals.update(REFERENCE_RE.findall(joined))
        if "fukurou-development" in joined:
            skill_signal = True
        for node in walk_dicts(event):
            if node.get("type") == "tool_use" and isinstance(node.get("name"), str):
                tool_id = str(node.get("id", ""))
                if tool_id and tool_id in seen_tool_ids:
                    continue
                if tool_id:
                    seen_tool_ids.add(tool_id)
                name = node["name"]
                tool_calls[name] = tool_calls.get(name, 0) + 1
            item = node.get("item")
            if isinstance(item, dict) and str(event.get("type", "")).endswith("completed"):
                item_type = item.get("type")
                if isinstance(item_type, str):
                    tool_calls[item_type] = tool_calls.get(item_type, 0) + 1
    return {
        "skill_signal": skill_signal,
        "reference_signals": sorted(reference_signals),
        "tool_calls": dict(sorted(tool_calls.items())),
    }


def walk_dicts(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def normalize_reported_references(structured: dict[str, Any] | None) -> list[str]:
    if not structured or not isinstance(structured.get("references_used"), list):
        return []
    normalized: set[str] = set()
    for value in structured["references_used"]:
        if not isinstance(value, str):
            continue
        match = REFERENCE_RE.search(value.replace("\\", "/"))
        if match:
            normalized.add(match.group(0))
    return sorted(normalized)


def score_routing(case: dict[str, Any], variant: str, structured: dict[str, Any] | None) -> dict[str, Any]:
    reported = set(normalize_reported_references(structured))
    expected = set(case.get("expected_references", []))
    forbidden = set(case.get("forbidden_references", []))
    if variant == "baseline":
        contamination = sorted(reported & CANONICAL_REFERENCES)
        return {
            "applicable": False,
            "reported_references": sorted(reported),
            "baseline_skill_reference_contamination": contamination,
            "pass": not contamination,
        }
    missing = sorted(expected - reported)
    forbidden_used = sorted(forbidden & reported)
    extra = sorted((reported - expected) & CANONICAL_REFERENCES)
    return {
        "applicable": True,
        "expected_references": sorted(expected),
        "reported_references": sorted(reported),
        "missing_expected": missing,
        "forbidden_used": forbidden_used,
        "extra_skill_references": extra,
        "pass": not missing and not forbidden_used and len(reported) <= 2,
    }


def tracked_changes(worktree: Path) -> list[str]:
    output = git_output(worktree, "status", "--porcelain", "--untracked-files=no")
    return [line for line in output.splitlines() if line.strip()]


def run_one(
    *,
    repo: Path,
    ref: str,
    case: dict[str, Any],
    agent: str,
    variant: str,
    out_dir: Path,
    timeout: int,
    codex_model: str | None,
    claude_model: str | None,
    claude_max_turns: int,
    claude_max_budget_usd: float,
    dry_run: bool,
) -> dict[str, Any]:
    run_name = f"case-{case['id']:02d}-{agent}-{variant}"
    run_dir = out_dir / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt = benchmark_prompt(case)
    stdout_path = run_dir / "events.jsonl"
    stderr_path = run_dir / "stderr.log"
    structured_path = run_dir / "structured.json"
    started = time.monotonic()

    executable = shutil.which(agent)
    if not executable:
        raise RuntimeError(f"{agent!r} executable was not found on PATH")

    with isolated_worktree(repo, ref) as worktree:
        prepare_variant(worktree, agent, variant)
        if agent == "codex":
            shadow_home = run_dir / "shadow-home"
            command = build_codex_command(executable, worktree, prompt, structured_path, codex_model)
            env = codex_environment(shadow_home)
        else:
            command = build_claude_command(
                executable,
                prompt,
                claude_model,
                claude_max_turns,
                claude_max_budget_usd,
            )
            env = os.environ.copy()

        (run_dir / "command.json").write_text(json.dumps(command, ensure_ascii=False, indent=2), encoding="utf-8")
        if dry_run:
            return {
                "case_id": case["id"],
                "case_name": case["name"],
                "agent": agent,
                "variant": variant,
                "dry_run": True,
                "command": command,
            }

        result = run_process(
            command,
            cwd=worktree,
            env=env,
            timeout=timeout,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        changes = tracked_changes(worktree)

    events = read_jsonl(stdout_path)
    structured = extract_structured(agent, events, structured_path)
    usage = extract_usage(agent, events)
    trace = extract_trace(events)
    routing = score_routing(case, variant, structured)
    elapsed = round(time.monotonic() - started, 3)
    record = {
        "case_id": case["id"],
        "case_name": case["name"],
        "agent": agent,
        "agent_version": command_version(agent),
        "variant": variant,
        "repository_ref": ref,
        "exit_code": result.returncode,
        "wall_seconds": elapsed,
        "usage": usage,
        "trace": trace,
        "routing": routing,
        "tracked_changes": changes,
        "tracked_diff_clean": not changes,
        "structured_output": structured,
        "expectations": case.get("expectations", []),
        "raw_events": str(stdout_path.relative_to(out_dir)),
        "stderr": str(stderr_path.relative_to(out_dir)),
    }
    (run_dir / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def select_cases(args: argparse.Namespace, evals: list[dict[str, Any]], suites: dict[str, list[int]]) -> list[dict[str, Any]]:
    by_id = {int(case["id"]): case for case in evals}
    if args.all:
        ids = sorted(by_id)
    elif args.case:
        ids = args.case
    else:
        if args.suite not in suites:
            raise RuntimeError(f"unknown suite {args.suite!r}; available: {', '.join(sorted(suites))}")
        ids = suites[args.suite]
    missing = [case_id for case_id in ids if case_id not in by_id]
    if missing:
        raise RuntimeError(f"unknown eval case ids: {missing}")
    return [by_id[case_id] for case_id in ids]


def summarize(records: list[dict[str, Any]], out_dir: Path) -> None:
    serializable = [record for record in records if not record.get("dry_run")]
    (out_dir / "results.json").write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Fukurou live benchmark",
        "",
        "| Case | Agent | Variant | Exit | Routing | Tracked diff | Input | Cached | Output | Cost | Seconds |",
        "|---|---|---|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for record in serializable:
        usage = record["usage"]
        cost = usage.get("cost_usd")
        cost_text = "" if cost is None else f"{cost:.4f}"
        lines.append(
            "| {case} | {agent} | {variant} | {exit_code} | {routing} | {diff} | {input_tokens} | {cached} | {output} | {cost} | {seconds} |".format(
                case=record["case_name"],
                agent=record["agent"],
                variant=record["variant"],
                exit_code=record["exit_code"],
                routing="pass" if record["routing"].get("pass") else "fail",
                diff="clean" if record["tracked_diff_clean"] else "CHANGED",
                input_tokens=usage.get("input_tokens", 0),
                cached=usage.get("cached_input_tokens", 0),
                output=usage.get("output_tokens", 0),
                cost=cost_text,
                seconds=record["wall_seconds"],
            )
        )
    lines.extend(["", "## Pair deltas", ""])
    grouped: dict[tuple[int, str], dict[str, dict[str, Any]]] = {}
    for record in serializable:
        grouped.setdefault((record["case_id"], record["agent"]), {})[record["variant"]] = record
    for (_, agent), variants in grouped.items():
        if "baseline" not in variants or "skill" not in variants:
            continue
        baseline = variants["baseline"]
        skill = variants["skill"]
        delta_input = skill["usage"].get("input_tokens", 0) - baseline["usage"].get("input_tokens", 0)
        delta_output = skill["usage"].get("output_tokens", 0) - baseline["usage"].get("output_tokens", 0)
        delta_seconds = round(skill["wall_seconds"] - baseline["wall_seconds"], 3)
        lines.append(
            f"- **{skill['case_name']} / {agent}:** input {delta_input:+d}, output {delta_output:+d}, wall {delta_seconds:+.3f}s; "
            f"skill routing={'pass' if skill['routing'].get('pass') else 'fail'}, baseline contamination={baseline['routing'].get('baseline_skill_reference_contamination', [])}."
        )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run paired live Codex/Claude benchmarks for the Fukurou skill.")
    parser.add_argument("--repo", type=Path, required=True, help="Local fukurouserver checkout used to create isolated worktrees.")
    parser.add_argument("--ref", default="HEAD", help="Committed repository ref to benchmark. Default: HEAD.")
    parser.add_argument("--agent", choices=("codex", "claude", "both"), default="both")
    parser.add_argument("--variant", choices=("baseline", "skill", "both"), default="both")
    parser.add_argument("--suite", default="smoke", help="Suite from benchmarks/suites.json. Default: smoke.")
    parser.add_argument("--case", type=int, action="append", help="Run one eval case ID. Repeat to select several.")
    parser.add_argument("--all", action="store_true", help="Run every quality eval case. This can be expensive.")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmark-results")
    parser.add_argument("--timeout", type=int, default=900, help="Per-run timeout in seconds.")
    parser.add_argument("--codex-model")
    parser.add_argument("--claude-model")
    parser.add_argument("--claude-max-turns", type=int, default=16)
    parser.add_argument("--claude-max-budget-usd", type=float, default=0.50)
    parser.add_argument("--dry-run", action="store_true", help="Prepare worktrees and print commands without calling a model.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    if not (repo / ".git").exists() and not git_output(repo, "rev-parse", "--git-dir"):
        raise RuntimeError(f"not a Git checkout: {repo}")

    eval_data = load_json(EVALS_PATH)
    suites = load_json(SUITES_PATH)
    cases = select_cases(args, eval_data["evals"], suites)
    agents = ["codex", "claude"] if args.agent == "both" else [args.agent]
    variants = ["baseline", "skill"] if args.variant == "both" else [args.variant]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out.resolve() / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "created_at": stamp,
        "repository": str(repo),
        "repository_ref": args.ref,
        "repository_commit": git_output(repo, "rev-parse", args.ref),
        "suite": args.suite,
        "case_ids": [case["id"] for case in cases],
        "agents": agents,
        "variants": variants,
        "dry_run": args.dry_run,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    records: list[dict[str, Any]] = []
    failures = 0
    total = len(cases) * len(agents) * len(variants)
    index = 0
    for case in cases:
        for agent in agents:
            for variant in variants:
                index += 1
                print(f"[{index}/{total}] {case['name']} / {agent} / {variant}", flush=True)
                try:
                    record = run_one(
                        repo=repo,
                        ref=args.ref,
                        case=case,
                        agent=agent,
                        variant=variant,
                        out_dir=out_dir,
                        timeout=args.timeout,
                        codex_model=args.codex_model,
                        claude_model=args.claude_model,
                        claude_max_turns=args.claude_max_turns,
                        claude_max_budget_usd=args.claude_max_budget_usd,
                        dry_run=args.dry_run,
                    )
                except Exception as exc:
                    failures += 1
                    record = {
                        "case_id": case["id"],
                        "case_name": case["name"],
                        "agent": agent,
                        "variant": variant,
                        "error": str(exc),
                    }
                    print(f"  ERROR: {exc}", file=sys.stderr)
                records.append(record)

    summarize(records, out_dir)
    print(f"Results: {out_dir}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
