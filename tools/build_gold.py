#!/usr/bin/env python3
"""Recompute the gold answer from the task inputs and push it everywhere it is pinned.

Usage:  python tools/build_gold.py <task_dir> [--check]

Reads environment/input/ under verification_rules.md with exact arithmetic (Fraction),
then:
  * writes solution/files/claim_register.csv and solution/files/results.json
  * updates tests/verifier.json: register_table rows + row_set, the per-claim trap check
    (register_table_trap_<id>), and results_figures
  * validates (does not rewrite) the note checks: each co-naming regex must target the
    claim/driver the data now implies and exclude exactly the claim ids carrying another
    driver; the confirmed/miscounted regexes must carry the right figures. A mismatch
    exits non-zero, because those regexes then need regenerating.
  * rebuilds solution/golden_trajectory.json so its printf steps write the current gold
    files byte-for-byte (verification_note.md is hand-written; it is only embedded).

--check: change nothing, exit 1 if any pinned value disagrees with the recomputation.
"""
import argparse
import csv
import io
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

CODES = ("BOTH_WRONG", "AVERAGE_WRONG", "COUNT_WRONG", "NOTHING_WRONG")


def one_decimal_half_up(x: Fraction) -> str:
    tenths = (x * 10 + Fraction(1, 2)).__floor__()
    return f"{tenths // 10}.{tenths % 10}"


def parse_display(s: str):
    m = re.fullmatch(r"\s*(\d\.\d)\s*out of\s*([\d.,]+)\s*Ratings\s*", s)
    if not m:
        raise ValueError(f"unreadable displayed_string {s!r}")
    return m.group(1), int(re.sub(r"[.,]", "", m.group(2)))


def compute(inp: Path):
    facts = {r["field"]: r["value"] for r in csv.DictReader(open(inp / "verification_facts.csv", newline=""))}
    as_of, snap_day = facts["breakdown_as_of"], facts["snapshots_captured_on"]
    export = {}
    for r in csv.DictReader(open(inp / "ratings_breakdown.csv", newline="")):
        if r.get("pulled_on", as_of) != as_of:  # pre-log format = one pull on as_of
            continue
        levels = export.setdefault((r["app_id"], r["platform"]), {})
        assert int(r["stars"]) not in levels, f"duplicate level {r}"
        levels[int(r["stars"])] = int(r["rating_count"])
    snaps = {}
    for r in csv.DictReader(open(inp / "listing_snapshot.csv", newline="")):
        if r["captured_on"] == snap_day:
            key = (r["app_id"], r["platform"])
            assert key not in snaps, f"two governing snapshots for {key}"
            snaps[key] = r["displayed_string"]

    rows, halves = [], []
    for c in csv.DictReader(open(inp / "claims.csv", newline="")):
        key = (c["app_id"], c["platform"])
        if key in export:
            lv = export[key]
            assert sorted(lv) == [1, 2, 3, 4, 5], f"{key} lacks star levels"
            count = sum(lv.values())
            mean = Fraction(sum(s * n for s, n in lv.items()), count)
            avg = one_decimal_half_up(mean)
            if (mean * 20).denominator == 1 and (mean * 10).denominator != 1:
                halves.append(c["claim_id"])
        else:
            avg, count = parse_display(snaps[key])
        avg_wrong = Fraction(c["claimed_average"]) != Fraction(avg)
        cnt_wrong = int(c["claimed_rating_count"]) != count
        driver = CODES[0] if avg_wrong and cnt_wrong else CODES[1] if avg_wrong else CODES[2] if cnt_wrong else CODES[3]
        gap = abs(int(c["claimed_rating_count"]) - count)
        rows.append({"claim_id": c["claim_id"], "true_average": avg, "true_count": count,
                     "driver": driver, "gap": gap})
    gaps = sorted((r["gap"] for r in rows), reverse=True)
    assert gaps[0] > gaps[1], "max count gap is tied — the note's largest-gap claim is ambiguous"
    assert len(halves) == 1, f"need exactly one exact-half mean, found {halves}"
    results = {k: sum(r["driver"] == code for r in rows) for k, code in
               (("nothing_wrong_count", "NOTHING_WRONG"), ("average_wrong_count", "AVERAGE_WRONG"),
                ("count_wrong_count", "COUNT_WRONG"))}
    results["max_count_gap"] = gaps[0]
    largest = next(r["claim_id"] for r in rows if r["gap"] == gaps[0])
    return rows, results, largest, halves[0]


def register_csv(rows) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["claim_id", "true_average", "true_count", "driver"])
    for r in rows:
        w.writerow([r["claim_id"], r["true_average"], r["true_count"], r["driver"]])
    return out.getvalue()


def cell(r):
    return {"true_average": r["true_average"], "true_count": str(r["true_count"]), "driver": r["driver"]}


def check_note_regex(name, pattern, target, driver, rows, problems):
    others = {r["claim_id"] for r in rows if r["driver"] != driver}
    excluded = set(re.findall(r"RC\\-(\d+)", pattern))
    excluded = {f"RC-{x}" for x in excluded}
    head = re.match(r"\(\?is\)\(\?:\\b(RC-\d+)", pattern)
    if not head or head.group(1) != target:
        problems.append(f"{name}: targets {head and head.group(1)}, data implies {target}")
    if f"\\b{driver}" not in pattern:
        problems.append(f"{name}: does not require {driver}")
    if excluded != others:
        problems.append(f"{name}: excludes {sorted(excluded)}, should exclude {sorted(others)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir", type=Path)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    T = a.task_dir
    rows, results, largest, half = compute(T / "environment" / "input")
    byid = {r["claim_id"]: r for r in rows}

    spec_path = T / "tests" / "verifier.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    v = {x["name"]: x for x in spec["verifiers"]}
    problems = []

    trap_name = next(n for n in v if n.startswith("register_table_trap_"))
    trap_id = trap_name.rsplit("_", 1)[1].upper().replace("RC", "RC-")
    reg = v["register_table"]["assertion"]["expected"]
    trap = v[trap_name]["assertion"]["expected"]
    want_reg_rows = {r["claim_id"]: cell(r) for r in rows if r["claim_id"] != trap_id}
    want_trap_rows = {trap_id: cell(byid[trap_id])}
    want_row_set = [r["claim_id"] for r in rows]
    fig = v["results_figures"]["assertion"]["expected"]["keys"]

    if a.check:
        if reg["rows"] != want_reg_rows: problems.append("register_table rows differ")
        if reg["row_set"] != want_row_set: problems.append("register_table row_set differs")
        if trap["rows"] != want_trap_rows: problems.append(f"{trap_name} differs")
        if {k: s["value"] for k, s in fig.items()} != results: problems.append("results_figures differ")
    else:
        reg["rows"], reg["row_set"], trap["rows"] = want_reg_rows, want_row_set, want_trap_rows
        for k, val in results.items():
            fig[k]["value"] = val

    check_note_regex("note_largest_gap", v["note_largest_gap"]["assertion"]["expected"],
                     largest, byid[largest]["driver"], rows, problems)
    check_note_regex("note_half", v["note_half"]["assertion"]["expected"],
                     half, byid[half]["driver"], rows, problems)
    for name, key in (("note_confirmed", "nothing_wrong_count"), ("note_miscounted", "count_wrong_count")):
        if f"(?:{results[key]}|{results[key]}\\.0|" not in v[name]["assertion"]["expected"]:
            problems.append(f"{name}: figure is not {results[key]}")

    sol = T / "solution" / "files"
    gold = {"claim_register.csv": register_csv(rows),
            "results.json": json.dumps(results, indent=2) + "\n"}
    for f, body in gold.items():
        if a.check and (sol / f).read_text(encoding="utf-8") != body:
            problems.append(f"solution/files/{f} differs")

    if problems:
        print("MISMATCH:", *problems, sep="\n  ")
        sys.exit(1)
    if not a.check:
        for f, body in gold.items():
            (sol / f).write_text(body, encoding="utf-8", newline="\n")
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        traj_path = T / "solution" / "golden_trajectory.json"
        traj = json.loads(traj_path.read_text(encoding="utf-8"))
        for step in traj:
            m = re.match(r"printf '%s' '.*' > (\S+)$", step["arguments"]["command"], re.S)
            if m:
                body = (sol / m.group(1)).read_text(encoding="utf-8")
                q = body.replace("'", "'\"'\"'")
                step["arguments"]["command"] = f"printf '%s' '{q}' > {m.group(1)}"
        traj_path.write_text(json.dumps(traj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{'checked' if a.check else 'built'}: {len(rows)} claims, results {results}, "
          f"largest gap {largest}, half case {half}")
    for r in rows:
        print(f"  {r['claim_id']}  {r['true_average']:>4} {r['true_count']:>5}  {r['driver']:<14} gap {r['gap']}")


if __name__ == "__main__":
    main()
