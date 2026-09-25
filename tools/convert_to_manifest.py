#!/usr/bin/env python3
"""Rewrite a non-connector task's tests/verifier.json as tests/manifest.json.

Usage:  python tools/convert_to_manifest.py <task_dir> [--python PY312]

Last packaging step (guide §7: non-connector tasks iterate on tests/verifier.json and
are rewritten to tests/manifest.json before submission; re-run the Oracle afterwards).

What it does:
  1. tests/verifier.json  {"task_id": ..., "verifiers": [...]}
     -> tests/manifest.json  [...]   (the verifier list, entries unchanged, order kept)
  2. Patches tests/score.py and tests/test_outputs.py to load manifest.json, wrapping the
     list back into the engine's VerifierSpec with the original task_id.
  3. Deletes tests/verifier.json so there is one source of truth.
  4. Self-check: grades solution/files with the grader before and after the conversion
     and fails unless every check's verdict is identical and the reward is 1.0.

The self-check needs a Python >= 3.12 interpreter with the grader's deps (the engine
ships as 3.12 bytecode); pass it with --python, default "python3".
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OLD_SCORE = re.compile(
    r'SPEC = VerifierSpec\.model_validate_json\(\(TESTS_DIR / "verifier\.json"\)'
    r'\.read_text\(encoding="utf-8"\)\)'
)
OLD_TESTS = re.compile(
    r'SPEC = VerifierSpec\.model_validate_json\(\s*\(TESTS_DIR / "verifier\.json"\)'
    r'\.read_text\(encoding="utf-8"\)\s*\)'
)


def loader(task_id: str) -> str:
    return (
        '_MANIFEST = json.loads((TESTS_DIR / "manifest.json").read_text(encoding="utf-8"))\n'
        f'SPEC = VerifierSpec.model_validate({{"task_id": {json.dumps(task_id)}, "verifiers": _MANIFEST}})'
    )


def grade(python: str, tests_dir: Path, gold_dir: Path) -> dict:
    with tempfile.TemporaryDirectory() as ws:
        for f in gold_dir.iterdir():
            shutil.copy(f, ws)
        env = dict(os.environ, HARBOR_TASK_WORKSPACE=ws, HARBOR_AGENT_LOGS_DIR=ws + "/none")
        out = subprocess.run([python, str(tests_dir / "score.py")], env=env,
                             capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir", type=Path)
    ap.add_argument("--python", default="python3")
    args = ap.parse_args()

    tests = args.task_dir / "tests"
    src, dst = tests / "verifier.json", tests / "manifest.json"
    if not src.exists():
        sys.exit(f"{src} not found (already converted?)")
    spec = json.loads(src.read_text(encoding="utf-8"))
    if set(spec) - {"task_id", "verifiers", "config"}:
        sys.exit(f"unexpected top-level keys in verifier.json: {sorted(spec)}")
    if spec.get("config") is not None:
        sys.exit("verifier.json carries a non-null 'config'; a list manifest cannot hold it")
    names = [v["name"] for v in spec["verifiers"]]
    if len(names) != len(set(names)):
        sys.exit("duplicate verifier names")

    before = grade(args.python, tests, args.task_dir / "solution" / "files")

    for name, pattern in (("score.py", OLD_SCORE), ("test_outputs.py", OLD_TESTS)):
        path = tests / name
        text = path.read_text(encoding="utf-8")
        new, n = pattern.subn(loader(spec["task_id"]), text)
        if n != 1:
            sys.exit(f"{name}: expected one verifier.json loader, found {n}; not converted")
        new = new.replace("The spec in `verifier.json`", "The spec in `manifest.json`")
        path.write_text(new, encoding="utf-8", newline="\n")

    dst.write_text(json.dumps(spec["verifiers"], indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    src.unlink()

    after = grade(args.python, tests, args.task_dir / "solution" / "files")
    verdicts = lambda r: [(c["name"], c["tag"], c["passed"]) for c in r["checks"]]
    if verdicts(before) != verdicts(after) or after["reward"] != 1.0:
        sys.exit(f"self-check FAILED: before={before['reward']} after={after['reward']}")
    leftovers = [p for p in args.task_dir.rglob("*") if p.is_file() and p.suffix != ".pyc"
                 and "verifier.json" in p.read_text(encoding="utf-8", errors="ignore")]
    print(f"converted {len(names)} verifiers -> {dst}")
    print(f"self-check: gold reward {after['reward']}, {after['passed']}/{after['total']} "
          "checks, verdicts identical before/after")
    if leftovers:
        print("note: still mentions verifier.json:", *leftovers, sep="\n  ")


if __name__ == "__main__":
    main()
