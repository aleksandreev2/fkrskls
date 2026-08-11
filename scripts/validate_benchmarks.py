from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS_PATH = ROOT / "skills" / "fukurou-development" / "evals" / "evals.json"
SUITES_PATH = ROOT / "benchmarks" / "suites.json"
SCHEMA_PATH = ROOT / "benchmarks" / "response_schema.json"
RUNNER_PATH = ROOT / "scripts" / "live_benchmark.py"
ENTRYPOINT_PATH = ROOT / "scripts" / "run_live_benchmark.py"
GITIGNORE_PATH = ROOT / ".gitignore"

EXPECTED_RESULT_FIELDS = {
    "summary",
    "root_cause_or_decision",
    "approach",
    "references_used",
    "developer_intelligence_used",
    "verification_plan",
    "risks",
    "user_questions",
    "confidence",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    errors: list[str] = []
    for path in (EVALS_PATH, SUITES_PATH, SCHEMA_PATH, RUNNER_PATH, ENTRYPOINT_PATH):
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")
    if errors:
        return errors

    eval_data = load(EVALS_PATH)
    suites = load(SUITES_PATH)
    schema = load(SCHEMA_PATH)
    eval_ids = {int(item["id"]) for item in eval_data.get("evals", [])}

    if not isinstance(suites, dict) or not suites:
        errors.append("benchmarks/suites.json must contain named suites")
    else:
        for name, ids in suites.items():
            if not isinstance(name, str) or not name:
                errors.append("suite names must be non-empty strings")
                continue
            if not isinstance(ids, list) or not ids:
                errors.append(f"suite {name!r} must contain at least one case id")
                continue
            if len(ids) != len(set(ids)):
                errors.append(f"suite {name!r} contains duplicate case ids")
            unknown = sorted(set(ids) - eval_ids)
            if unknown:
                errors.append(f"suite {name!r} contains unknown eval ids: {unknown}")

        smoke = suites.get("smoke", [])
        if len(smoke) > 5:
            errors.append("smoke suite must stay at five cases or fewer")
        if set(suites.get("routing", [])) != eval_ids:
            errors.append("routing suite must cover every quality eval exactly once")

    if schema.get("type") != "object":
        errors.append("benchmark response schema must be an object")
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or set(properties) != EXPECTED_RESULT_FIELDS:
        errors.append("benchmark response schema properties differ from the canonical result fields")
    if not isinstance(required, list) or set(required) != EXPECTED_RESULT_FIELDS:
        errors.append("benchmark response schema must require every canonical result field")
    if schema.get("additionalProperties") is not False:
        errors.append("benchmark response schema must reject additional properties")

    for path, label in (
        (RUNNER_PATH, "live benchmark core"),
        (ENTRYPOINT_PATH, "guarded live benchmark entrypoint"),
    ):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            errors.append(f"{label} syntax error: {exc}")

    entrypoint_text = ENTRYPOINT_PATH.read_text(encoding="utf-8")
    for required_text in ("CODEX_REQUIRED_FLAGS", "CLAUDE_REQUIRED_FLAGS", "--disallowedTools", "--untracked-files=all"):
        if required_text not in entrypoint_text:
            errors.append(f"guarded entrypoint missing required safety contract: {required_text}")

    if not GITIGNORE_PATH.is_file() or "benchmark-results/" not in GITIGNORE_PATH.read_text(encoding="utf-8"):
        errors.append("benchmark-results/ must be ignored by Git")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Live benchmark validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Live benchmark validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
