#!/usr/bin/env python3
"""Trap battery: grade known-wrong solvers and fair paraphrases with the task's own grader.

Usage:  python3.12 tools/check_traps.py <task_dir>

An independent solver (not the gold files) reads environment/input/ and writes the three
deliverables; each MISTAKE switch reproduces one plausible wrong method. Every deliverable
set is graded by tests/score.py in a scratch workspace.

Pass criteria:
  * the solver with no mistake scores 1.0 (the task is solvable from the inputs alone)
  * every mistake scores 0.0 (each trap is load-bearing on a core check)
  * every paraphrased note with correct values scores 1.0 (no wording brittleness)

Needs the grader deps (pydantic, jsonpath-ng, tenacity) in the running Python >= 3.12.
"""
import csv
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path

MISTAKES = {
    "float_round": "round(mean, 1) on a float mean",
    "decimal_of_float": "Decimal(float_mean).quantize(0.1, HALF_UP)",
    "fstring_format": "f'{mean:.1f}'",
    "two_decimals_first": "round to 2 dp, then to 1 dp",
    "truncate": "cut the mean short at 1 dp",
    "sum_all_pulls": "sum every export row, ignoring pulled_on",
    "last_pull_wins": "dict-overwrite export rows, so the latest pull wins",
    "latest_on_or_before": "use the latest pull on or before breakdown_as_of",
    "last_snapshot_wins": "dict-overwrite snapshots, so the latest capture wins",
    "locale_misparse": "read '1.049' as a decimal (count 1)",
    "scale_misparse": "read '4.4out of 533' as 'out of 5' + 33",
    "snapshot_over_export": "prefer the snapshot wherever one exists",
    "app_only_join": "match export rows on app_id only",
}


def round_mean(total, count, mistake):
    x = total / count
    if mistake == "float_round":
        return f"{round(x, 1):.1f}"
    if mistake == "decimal_of_float":
        return str(Decimal(x).quantize(Decimal("0.1"), ROUND_HALF_UP))
    if mistake == "fstring_format":
        return f"{x:.1f}"
    if mistake == "two_decimals_first":
        two = (Decimal(total) / Decimal(count)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return str(two.quantize(Decimal("0.1"), ROUND_HALF_UP))
    if mistake == "truncate":
        return f"{math.floor(Fraction(total, count) * 10) / 10:.1f}"
    return str((Decimal(total) / Decimal(count)).quantize(Decimal("0.1"), ROUND_HALF_UP))


def parse_display(s, mistake):
    m = re.fullmatch(r"(\d\.\d)\s*out of\s*([\d.,]+) Ratings", s)
    avg, raw = m.group(1), m.group(2)
    if mistake == "scale_misparse" and "out of" in s and not re.search(r"\s+out of", s):
        raw = raw[1:]
    if mistake == "locale_misparse" and "." in raw:
        return avg, int(float(raw.replace(",", "")))
    return avg, int(re.sub(r"[.,]", "", raw))


def solve(inp: Path, mistake=None):
    facts = {r["field"]: r["value"] for r in csv.DictReader(open(inp / "verification_facts.csv"))}
    as_of, snap_day = facts["breakdown_as_of"], facts["snapshots_captured_on"]
    raw = list(csv.DictReader(open(inp / "ratings_breakdown.csv")))
    if mistake == "latest_on_or_before":
        best = {}
        for r in raw:
            k = (r["app_id"], r["platform"])
            if r.get("pulled_on", as_of) <= as_of and r.get("pulled_on", as_of) >= best.get(k, ""):
                best[k] = r.get("pulled_on", as_of)
        raw = [r for r in raw if best.get((r["app_id"], r["platform"])) == r.get("pulled_on", as_of)]
    elif mistake not in ("sum_all_pulls", "last_pull_wins"):
        raw = [r for r in raw if r.get("pulled_on", as_of) == as_of]
    export = {}
    for r in raw:
        key = r["app_id"] if mistake == "app_only_join" else (r["app_id"], r["platform"])
        lv = export.setdefault(key, {})
        s, n = int(r["stars"]), int(r["rating_count"])
        lv[s] = lv.get(s, 0) + n if mistake in ("sum_all_pulls", "app_only_join") else n
    snaps = {}
    for r in csv.DictReader(open(inp / "listing_snapshot.csv")):
        if mistake == "last_snapshot_wins" or r["captured_on"] == snap_day:
            snaps[(r["app_id"], r["platform"])] = r["displayed_string"]

    rows, halves = [], []
    for c in csv.DictReader(open(inp / "claims.csv")):
        key = (c["app_id"], c["platform"])
        ekey = c["app_id"] if mistake == "app_only_join" else key
        if ekey in export and not (mistake == "snapshot_over_export" and key in snaps):
            lv = export[ekey]
            count = sum(lv.values())
            total = sum(s * n for s, n in lv.items())
            avg = round_mean(total, count, mistake)
            fr = Fraction(total, count)
            if (fr * 20).denominator == 1 and (fr * 10).denominator != 1:
                halves.append(c["claim_id"])
        else:
            avg, count = parse_display(snaps[key], mistake)
        aw = Decimal(c["claimed_average"]) != Decimal(avg)
        cw = int(c["claimed_rating_count"]) != count
        d = "BOTH_WRONG" if aw and cw else "AVERAGE_WRONG" if aw else "COUNT_WRONG" if cw else "NOTHING_WRONG"
        rows.append((c["claim_id"], avg, count, d, abs(int(c["claimed_rating_count"]) - count)))
    return rows, halves


def deliverables(rows, halves, note_style="plain"):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["claim_id", "true_average", "true_count", "driver"])
    for r in rows:
        w.writerow(r[:4])
    count = lambda d: sum(r[3] == d for r in rows)
    res = {"nothing_wrong_count": count("NOTHING_WRONG"), "average_wrong_count": count("AVERAGE_WRONG"),
           "count_wrong_count": count("COUNT_WRONG"), "max_count_gap": max(r[4] for r in rows)}
    big = max(rows, key=lambda r: r[4])
    half = next((r for r in rows if r[0] in halves), None)
    nw, cw = res["nothing_wrong_count"], res["count_wrong_count"]
    half_par = (f"{half[0]} is decided by rounding alone: its weighted mean sits exactly on a half, and its "
                f"driver in the register is {half[3]}.") if half else "No claim sits exactly on a half."
    notes = {
        "plain": f"""# Rating check for the corrections desk

I checked every rating the roundup quotes against the stores' own figures and set the
results out in the attached register, one row per claim, in the article's order.

Confirmed in full: {nw}. Miscounted: {cw}. The remaining claims have a wrong average, or
a wrong average and a wrong count together, and the register names which.

The widest count gap belongs to {big[0]}, which the register codes {big[3]}; the article's
count there is out by {big[4]} ratings.

{half_par}

Please correct the figures the register marks as wrong; the rest can stand as printed.
""",
        "reversed": f"""# Corrections: couples-app roundup

Having gone through each figure the article printed against the stores' own records, the
article's figures are confirmed in full for {nw} of its claims, while it miscounts the
ratings on {cw} of them without getting their averages wrong.

Of all the counts, the one furthest from the store's is on {big[0]}. The register gives
that claim the code {big[3]}, since the gap between printed and real is {big[4]}.

{half_par}

Everything else is in the register, with the store's real average and count beside each
claim, so the desk can work through the corrections one line at a time.
""",
        "bullets": f"""# Corrections summary

The register attached to this note sets out every claim the roundup makes, with the stores'
real figures beside it. The short version for the desk is as follows.

- The article is confirmed on {nw} claims, with nothing to change.
- It miscounted {cw} claims whose averages are nonetheless right.

The largest count gap on the page is {big[0]}, coded {big[3]}, out by {big[4]} ratings.

{half_par}
""",
        "table": f"""# Rating claims — what needs correcting

I have been through each claim in the roundup and compared it with the stores' own figures.

| Finding | Claims |
|---|---|
| Confirmed in full | {nw} |
| Miscounted | {cw} |

{big[0]} carries the largest gap between the count printed and the store's count ({big[4]}),
and the register codes it {big[3]}.

{half_par} The register lists the rest with their real averages and counts, which should be
enough for the desk to correct each entry.
""",
    }
    return {"claim_register.csv": out.getvalue(), "results.json": json.dumps(res, indent=2) + "\n",
            "verification_note.md": notes[note_style]}


def grade(task: Path, files):
    with tempfile.TemporaryDirectory() as ws:
        for name, body in files.items():
            Path(ws, name).write_text(body, encoding="utf-8")
        env = dict(os.environ, HARBOR_TASK_WORKSPACE=ws, HARBOR_AGENT_LOGS_DIR=ws + "/none")
        r = json.loads(subprocess.run([sys.executable, str(task / "tests" / "score.py")], env=env,
                                      capture_output=True, text=True, check=True).stdout)
    return r["reward"], [c["name"] for c in r["checks"] if not c["passed"]]


def main():
    task = Path(sys.argv[1]).resolve()
    inp = task / "environment" / "input"
    ok = True
    print("correct solver + paraphrased notes (want 1.0):")
    rows, halves = solve(inp)
    for style in ("plain", "reversed", "bullets", "table"):
        reward, failed = grade(task, deliverables(rows, halves, style))
        ok &= reward == 1.0
        print(f"  {'PASS' if reward == 1.0 else 'FAIL'}  {style:<10} reward {reward}  {failed or ''}")
    print("mistakes (want 0.0):")
    for m, desc in MISTAKES.items():
        try:
            rows, halves = solve(inp, m)
            reward, failed = grade(task, deliverables(rows, halves))
        except Exception as e:  # a crash on a trap is a caught mistake too
            reward, failed = 0.0, [f"solver crashed: {type(e).__name__}"]
        ok &= reward == 0.0
        print(f"  {'PASS' if reward == 0.0 else 'FAIL'}  {m:<21} reward {reward:<5} {desc}; failed: {', '.join(failed)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
