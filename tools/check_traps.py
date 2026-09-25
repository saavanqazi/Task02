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
    "ignore_moves": "never read listing_changes.csv",
    "one_hop_moves": "follow a listing's first move only, not a chain",
    "relaunch_as_transfer": "treat a relaunched listing's new id as the claim's rows",
    "moves_ignore_date": "apply every move, even one dated after breakdown_as_of",
    "move_strict_before": "apply a move only after changed_on (< instead of <=)",
    "missing_level_zero": "read a star level missing from the pull as 0 ratings",
    "ignore_corrections": "never read site_corrections.csv",
    "corrections_file_order": "let the last correction line in the file win, not the latest date",
    "corrections_ignore_date": "apply corrections published after breakdown_as_of too",
    "both_mean_of_means": "average the two listings' means for a BOTH claim",
    "space_misparse": "read '1 482' as 482 (space not taken as a thousands separator)",
    "correction_strict_before": "apply only corrections dated before breakdown_as_of (< not <=)",
}


def listing_on(moves, app_id, platform, day, mistake):
    """app_id the claimed listing reports under on `day`; None once a relaunch ends it."""
    if mistake == "ignore_moves":
        return app_id
    for hop in range(len(moves) + 1):
        step = [m for m in moves if m["app_id"] == app_id and m["platform"] == platform
                and (mistake == "moves_ignore_date" or m["changed_on"] < day
                     or (m["changed_on"] == day and mistake != "move_strict_before"))]
        if not step or (mistake == "one_hop_moves" and hop == 1):
            return app_id
        if step[0]["change"] == "relaunched" and mistake != "relaunch_as_transfer":
            return None
        app_id = step[0]["new_app_id"]
    raise ValueError("move cycle")


def round_mean(mean: Fraction, mistake):
    x = float(mean)
    exact = Decimal(mean.numerator) / Decimal(mean.denominator)
    if mistake == "float_round":
        return f"{round(x, 1):.1f}"
    if mistake == "decimal_of_float":
        return str(Decimal(x).quantize(Decimal("0.1"), ROUND_HALF_UP))
    if mistake == "fstring_format":
        return f"{x:.1f}"
    if mistake == "two_decimals_first":
        return str(exact.quantize(Decimal("0.01"), ROUND_HALF_UP).quantize(Decimal("0.1"), ROUND_HALF_UP))
    if mistake == "truncate":
        return f"{math.floor(mean * 10) / 10:.1f}"
    return str(exact.quantize(Decimal("0.1"), ROUND_HALF_UP))


def parse_display(s, mistake):
    m = re.fullmatch(r"(\d\.\d)\s*out of\s*(\d[\d., ]*?) Ratings", s)
    avg, raw = m.group(1), m.group(2)
    if mistake == "scale_misparse" and "out of" in s and not re.search(r"\s+out of", s):
        raw = raw[1:]
    if mistake == "locale_misparse" and "." in raw:
        return avg, int(float(raw.replace(",", "")))
    if mistake == "space_misparse" and " " in raw:
        return avg, int(raw.split(" ")[-1])
    return avg, int(re.sub(r"[., ]", "", raw))


def solve(inp: Path, mistake=None):
    facts = {r["field"]: r["value"] for r in csv.DictReader(open(inp / "verification_facts.csv"))}
    as_of, snap_day = facts["breakdown_as_of"], facts["snapshots_captured_on"]
    raw = list(csv.DictReader(open(inp / "ratings_breakdown.csv")))
    day = lambda r: r.get("pulled_on", as_of)
    if mistake == "latest_on_or_before":
        best = {}
        for r in raw:
            k = (r["app_id"], r["platform"])
            if day(r) <= as_of and day(r) >= best.get(k, ""):
                best[k] = day(r)
        raw = [r for r in raw if best.get((r["app_id"], r["platform"])) == day(r)]
    elif mistake not in ("sum_all_pulls", "last_pull_wins"):
        raw = [r for r in raw if day(r) == as_of]
    export = {}
    for r in raw:
        key = r["app_id"] if mistake == "app_only_join" else (r["app_id"], r["platform"])
        lv = export.setdefault(key, {})
        s, n = int(r["stars"]), int(r["rating_count"])
        lv[s] = lv.get(s, 0) + n if mistake in ("sum_all_pulls", "app_only_join") else n
    optional = lambda name: list(csv.DictReader(open(inp / name))) if (inp / name).exists() else []
    moves = optional("listing_changes.csv")
    fixes = {}
    if mistake != "ignore_corrections":
        lines = optional("site_corrections.csv")
        if mistake != "corrections_file_order":
            lines = sorted(lines, key=lambda r: r["corrected_on"])
        for r in lines:
            if mistake == "corrections_ignore_date" or r["corrected_on"] < as_of or (
                    r["corrected_on"] == as_of and mistake != "correction_strict_before"):
                fixes.setdefault(r["claim_id"], {})[r["field"]] = r["new_value"]
    snaps = {}
    for r in csv.DictReader(open(inp / "listing_snapshot.csv")):
        if mistake == "last_snapshot_wins" or r["captured_on"] == snap_day:
            snaps[(r["app_id"], r["platform"])] = r["displayed_string"]

    def listing(app_id, platform):
        now_id = listing_on(moves, app_id, platform, as_of, mistake)
        snap_mistake = None if mistake == "moves_ignore_date" else mistake  # that mistake is in the export lookup
        key = (listing_on(moves, app_id, platform, snap_day, snap_mistake), platform)
        lv = export.get(now_id if mistake == "app_only_join" else (now_id, platform)) if now_id else None
        usable = lv and (sorted(lv) == [1, 2, 3, 4, 5] or mistake == "missing_level_zero")
        if usable and not (mistake == "snapshot_over_export" and key in snaps):
            return "export", Fraction(sum(s * n for s, n in lv.items())), sum(lv.values())
        avg, count = parse_display(snaps[key], mistake)
        return "snapshot", avg, count

    rows, halves = [], []
    for c in csv.DictReader(open(inp / "claims.csv")):
        plats = ("IOS", "ANDROID") if c["platform"] == "BOTH" else (c["platform"],)
        parts = [listing(c["app_id"], p) for p in plats]
        count = sum(x[2] for x in parts)
        if len(parts) == 1 and parts[0][0] == "snapshot":
            avg = parts[0][1]
        else:
            stars = lambda x: x[1] if x[0] == "export" else Fraction(x[1]) * x[2]
            if mistake == "both_mean_of_means" and len(parts) == 2:
                mean = sum(stars(x) / x[2] for x in parts) / 2
            else:
                mean = sum(stars(x) for x in parts) / count
            avg = round_mean(mean, mistake)
            if all(x[0] == "export" for x in parts) and (mean * 20).denominator == 1 and (mean * 10).denominator != 1:
                halves.append(c["claim_id"])
        fixed = fixes.get(c["claim_id"], {})
        claimed_avg = fixed.get("claimed_average", c["claimed_average"])
        claimed_cnt = int(fixed.get("claimed_rating_count", c["claimed_rating_count"]))
        aw = Decimal(claimed_avg) != Decimal(avg)
        cw = claimed_cnt != count
        d = "BOTH_WRONG" if aw and cw else "AVERAGE_WRONG" if aw else "COUNT_WRONG" if cw else "NOTHING_WRONG"
        rows.append((c["claim_id"], avg, count, d, abs(claimed_cnt - count)))
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
