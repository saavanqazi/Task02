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


def load_moves(inp: Path):
    path = inp / "listing_changes.csv"
    return list(csv.DictReader(open(path, newline=""))) if path.exists() else []


def listing_on(moves, app_id, platform, day):
    """app_id the claimed listing reports under on `day`, following every move dated on or
    before it (chains included); None once a relaunch has ended the listing."""
    for _ in range(len(moves) + 1):
        step = [m for m in moves if m["app_id"] == app_id and m["platform"] == platform
                and m["changed_on"] <= day]
        if not step:
            return app_id
        assert len(step) == 1, f"two moves out of {app_id} {platform}"
        if step[0]["change"] == "relaunched":
            return None
        assert step[0]["change"] == "transferred", step[0]
        app_id = step[0]["new_app_id"]
    raise ValueError("move cycle")


def load_corrections(inp: Path, as_of: str):
    """claim_id -> {field: value} as the article stood on as_of (latest correction wins)."""
    path = inp / "site_corrections.csv"
    if not path.exists():
        return {}
    latest = {}
    for r in csv.DictReader(open(path, newline="")):
        assert r["field"] in ("claimed_average", "claimed_rating_count"), r
        if r["corrected_on"] > as_of:
            continue
        key = (r["claim_id"], r["field"])
        assert key not in latest or latest[key][0] != r["corrected_on"], f"same-day corrections {key}"
        if key not in latest or r["corrected_on"] > latest[key][0]:
            latest[key] = (r["corrected_on"], r["new_value"])
    out = {}
    for (cid, field), (_, value) in latest.items():
        out.setdefault(cid, {})[field] = value
    return out


def compute(inp: Path):
    moves = load_moves(inp)
    facts = {r["field"]: r["value"] for r in csv.DictReader(open(inp / "verification_facts.csv", newline=""))}
    as_of, snap_day = facts["breakdown_as_of"], facts["snapshots_captured_on"]
    corrections = load_corrections(inp, as_of)
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

    def listing(app_id, platform):
        """('export', total_stars, count) or ('snapshot', avg_str, count) for one listing."""
        on = listing_on(moves, app_id, platform, as_of)
        lv = export.get((on, platform)) if on is not None else None
        if lv is not None and sorted(lv) == [1, 2, 3, 4, 5]:  # a partial pull covers nothing
            return "export", sum(s * n for s, n in lv.items()), sum(lv.values())
        avg, count = parse_display(snaps[(listing_on(moves, app_id, platform, snap_day), platform)])
        return "snapshot", avg, count

    rows, halves = [], []
    for c in csv.DictReader(open(inp / "claims.csv", newline="")):
        parts = [listing(c["app_id"], p) for p in (("IOS", "ANDROID") if c["platform"] == "BOTH" else (c["platform"],))]
        count = sum(x[2] for x in parts)
        if len(parts) == 1 and parts[0][0] == "snapshot":
            avg = parts[0][1]
        else:
            stars = sum(Fraction(x[1]) if x[0] == "export" else Fraction(x[1]) * x[2] for x in parts)
            mean = stars / count
            avg = one_decimal_half_up(mean)
            if all(x[0] == "export" for x in parts) and (mean * 20).denominator == 1 and (mean * 10).denominator != 1:
                halves.append(c["claim_id"])
        fixed = corrections.get(c["claim_id"], {})
        claimed_avg = fixed.get("claimed_average", c["claimed_average"])
        claimed_cnt = int(fixed.get("claimed_rating_count", c["claimed_rating_count"]))
        avg_wrong = Fraction(claimed_avg) != Fraction(avg)
        cnt_wrong = claimed_cnt != count
        driver = CODES[0] if avg_wrong and cnt_wrong else CODES[1] if avg_wrong else CODES[2] if cnt_wrong else CODES[3]
        rows.append({"claim_id": c["claim_id"], "true_average": avg, "true_count": count,
                     "driver": driver, "gap": abs(claimed_cnt - count),
                     "sources": [x[0] for x in parts]})
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


NUMBER_WORDS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()
FIGURE_GROUP = re.compile(r"\(\?:(\d+)\|\1\\\.0\|\1\\\.00\|\\b([a-z]+)\\b\)")  # "(?:6|6\.0|6\.00|\bsix\b)"


def figure_group(n: int) -> str:
    return rf"(?:{n}|{n}\.0|{n}\.00|\b{NUMBER_WORDS[n]}\b)"


def coname_regex(target, driver, rows) -> str:
    """Same-paragraph co-naming of `target` and `driver`, with no other driver code and no
    claim id carrying another driver in between (the mined pipeline's exact layout)."""
    bound = lambda s: f"(?<![A-Za-z0-9]){re.escape(s)}(?![A-Za-z0-9])"
    others = sorted(r["claim_id"] for r in rows if r["driver"] != driver)
    stops = "|".join([bound(i) for i in others] + [bound(c) for c in CODES if c != driver])
    gap = rf"(?:(?!(?:\n[ \t]*\n|\[Slide \d)|{stops}).){{0,900}}?"
    return rf"(?is)(?:\b{target}\w*\b{gap}\b{driver}|\b{driver}\w*\b{gap}\b{target})"


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

    want_note = {
        "note_largest_gap": coname_regex(largest, byid[largest]["driver"], rows),
        "note_half": coname_regex(half, byid[half]["driver"], rows),
    }
    for name, key in (("note_confirmed", "nothing_wrong_count"), ("note_miscounted", "count_wrong_count")):
        old = v[name]["assertion"]["expected"]
        if len(FIGURE_GROUP.findall(old)) != 2:
            problems.append(f"{name}: unexpected regex layout, cannot place the figure")
        want_note[name] = FIGURE_GROUP.sub(lambda m, n=results[key]: figure_group(n), old)
    for name, pattern in want_note.items():
        if a.check and v[name]["assertion"]["expected"] != pattern:
            problems.append(f"{name}: regex does not match the data")
        elif not a.check:
            v[name]["assertion"]["expected"] = pattern
    check_note_regex("note_largest_gap", want_note["note_largest_gap"],
                     largest, byid[largest]["driver"], rows, problems)
    check_note_regex("note_half", want_note["note_half"], half, byid[half]["driver"], rows, problems)

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
