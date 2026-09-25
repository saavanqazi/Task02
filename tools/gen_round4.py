#!/usr/bin/env python3
"""One-off data build for hardening round 4: claims RC-31..RC-60 with dense edge cases.

Usage:  python3 tools/gen_round4.py <task_dir>

Appends to environment/input/ (claims, export log, snapshots, moves, corrections). The
claimed figures are set FROM the truth that tools/build_gold.py computes, so every claim
lands on its designed driver and gap; the truth never depends on the claimed figures.
Deterministic (fixed seed). Run once on the round-3 inputs.
"""
import csv
import io
import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_gold  # noqa: E402

T = Path(sys.argv[1]); INP = T / "environment" / "input"
rng = random.Random(20260925)
D1, D8, D15, SNAP = "2026-09-01", "2026-09-08", "2026-09-15", "2026-08-10"
L = lambda a, b, c, d, e: {5: a, 4: b, 3: c, 2: d, 1: e}


def filler(n, skew):
    """Random complete star levels summing to n, mean not on an exact half."""
    while True:
        w = [max(0.02, rng.gauss(m, 0.04)) for m in skew]
        raw = [int(n * x / sum(w)) for x in w]
        raw[0] += n - sum(raw)
        lv = dict(zip((5, 4, 3, 2, 1), raw))
        mean = Fraction(sum(s * k for s, k in lv.items()), n)
        if not ((mean * 20).denominator == 1 and (mean * 10).denominator != 1):
            return lv


def grow(lv, pct):
    return {s: k + (int(k * pct) if k else 0) for s, k in lv.items()}


def shrink(lv, pct):
    return {s: k - int(k * pct) for s, k in lv.items()}


HIGH, MID, LOW = (0.58, 0.22, 0.09, 0.05, 0.06), (0.45, 0.24, 0.13, 0.08, 0.10), (0.33, 0.22, 0.17, 0.12, 0.16)

pulls = []          # (app, platform, day, levels)
snaps = []          # (app, platform, day, display)
moves = []          # (app, platform, day, change, new)
claims = []         # (claim_id, app, name, platform, design)


def listing(app, plat, n, skew, *, days=(D8,), snap_fmt=",", nospace=False, under=None, drop=None):
    """Export pulls under `under` (default app) plus the 08-10 snapshot under `app`."""
    base = filler(n, skew)
    for d in days:
        lv = {D1: shrink(base, 0.03), D8: base, D15: grow(base, 0.02)}[d]
        if d == D8 and drop:
            lv = {s: k for s, k in lv.items() if s not in drop}
        pulls.append((under or app, plat, d, lv))
    before = shrink(base, 0.05)
    cnt = sum(before.values())
    avg = build_gold.one_decimal_half_up(Fraction(sum(s * k for s, k in before.items()), cnt))
    sep = {",": f"{cnt:,}", ".": f"{cnt:,}".replace(",", "."), " ": f"{cnt:,}".replace(",", " ")}[snap_fmt]
    snaps.append((app, plat, SNAP, f"{avg}{'' if nospace else ' '}out of {sep} Ratings"))
    return base


# --- moves --------------------------------------------------------------------------
listing("A-41", "IOS", 1320, HIGH, days=(D1,), snap_fmt=".")                    # 3-hop chain
pulls.append(("A-72", "IOS", D1, filler(1350, HIGH)))
listing("A-41", "IOS", 1380, HIGH, days=(D8, D15), under="A-73")
snaps.pop()  # one snapshot for A-41 IOS is enough
moves += [("A-41", "IOS", "2026-08-20", "transferred", "A-71"),
          ("A-71", "IOS", "2026-08-29", "transferred", "A-72"),
          ("A-72", "IOS", "2026-09-04", "transferred", "A-73")]
claims.append(("RC-31", "A-41", "Pairwise", "IOS", ("NOTHING_WRONG", 0)))

listing("A-42", "ANDROID", 760, MID, days=(D1,), under="A-74")                  # transfer then relaunch
pulls.append(("A-75", "ANDROID", D8, filler(64, HIGH)))
moves += [("A-42", "ANDROID", "2026-08-18", "transferred", "A-74"),
          ("A-74", "ANDROID", "2026-09-02", "relaunched", "A-75")]
claims.append(("RC-32", "A-42", "Lovenote Duo", "ANDROID", ("COUNT_WRONG", 19)))
listing("A-42", "IOS", 1110, HIGH, days=(D8,))
claims.append(("RC-36", "A-42", "Lovenote Duo", "BOTH", ("NOTHING_WRONG", 0)))

listing("A-43", "IOS", 540, MID, days=(D8,))                                     # relaunch after as_of
pulls.append(("A-76", "IOS", D15, filler(22, HIGH)))
moves.append(("A-43", "IOS", "2026-09-09", "relaunched", "A-76"))
claims.append(("RC-33", "A-43", "Bramble & Bee", "IOS", ("AVERAGE_WRONG", 0)))

listing("A-44", "ANDROID", 905, MID, days=(D1,))                                 # move on as_of
listing("A-44", "ANDROID", 930, MID, days=(D8,), under="A-77")
snaps.pop()
moves.append(("A-44", "ANDROID", "2026-09-08", "transferred", "A-77"))
claims.append(("RC-34", "A-44", "Hearthside", "ANDROID", ("NOTHING_WRONG", 0)))

listing("A-45", "IOS", 1640, HIGH, days=(D8,), under="A-78", nospace=True)       # BOTH: moved + partial
moves.append(("A-45", "IOS", "2026-08-25", "transferred", "A-78"))
listing("A-45", "ANDROID", 480, LOW, days=(D1, D8), drop={4})
claims.append(("RC-35", "A-45", "Twinleaf", "BOTH", ("COUNT_WRONG", 23)))

# --- partial pulls --------------------------------------------------------------------
listing("A-46", "IOS", 2050, HIGH, days=(D1, D8, D15), drop={1})
claims.append(("RC-37", "A-46", "Softlight", "IOS", ("NOTHING_WRONG", 0)))
pulls.append(("A-46", "ANDROID", D8, L(88, 31, 7, 0, 0)))
snaps.append(("A-46", "ANDROID", SNAP, "4.6 out of 119 Ratings"))
claims.append(("RC-38", "A-46", "Softlight", "ANDROID", ("AVERAGE_WRONG", 0)))
listing("A-47", "ANDROID", 1560, MID, days=(D8,), drop={3}, snap_fmt=" ")
claims.append(("RC-39", "A-47", "Nearby Us", "ANDROID", ("BOTH_WRONG", 44)))
listing("A-48", "IOS", 820, MID, days=(D1, D8, D15), drop={2})
claims.append(("RC-40", "A-48", "Quietly Two", "IOS", ("COUNT_WRONG", 12)))

# --- corrections ----------------------------------------------------------------------
listing("A-49", "IOS", 1275, HIGH)
claims.append(("RC-41", "A-49", "Keepsake", "IOS", ("NOTHING_WRONG", 0)))
listing("A-49", "ANDROID", 690, MID)
claims.append(("RC-42", "A-49", "Keepsake", "ANDROID", ("NOTHING_WRONG", 0)))
listing("A-50", "IOS", 1440, HIGH, snap_fmt=".")
claims.append(("RC-43", "A-50", "Northstar Pair", "IOS", ("NOTHING_WRONG", 0)))
listing("A-50", "ANDROID", 610, LOW)
claims.append(("RC-44", "A-50", "Northstar Pair", "ANDROID", ("AVERAGE_WRONG", 0)))
listing("A-51", "IOS", 1300, HIGH)
claims.append(("RC-45", "A-51", "Loop & Lantern", "IOS", ("COUNT_WRONG", 10)))

# --- fillers (several BOTH) ------------------------------------------------------------
spec = [("RC-46", "A-51", "Loop & Lantern", "ANDROID", 540, MID, ("BOTH_WRONG", 31)),
        ("RC-47", "A-52", "Sundial Us", "IOS", 980, HIGH, ("AVERAGE_WRONG", 0)),
        ("RC-48", "A-52", "Sundial Us", "ANDROID", 415, LOW, ("NOTHING_WRONG", 0)),
        ("RC-49", "A-53", "Paperplane", "IOS", 1720, HIGH, ("COUNT_WRONG", 57)),
        ("RC-50", "A-53", "Paperplane", "ANDROID", 820, MID, ("NOTHING_WRONG", 0)),
        ("RC-51", "A-53", "Paperplane", "BOTH", None, None, ("AVERAGE_WRONG", 0)),
        ("RC-52", "A-54", "Tidewell", "IOS", 365, MID, ("NOTHING_WRONG", 0)),
        ("RC-53", "A-54", "Tidewell", "ANDROID", 2210, HIGH, ("BOTH_WRONG", 88)),
        ("RC-54", "A-55", "Honeycomb Two", "IOS", 1105, MID, ("AVERAGE_WRONG", 0)),
        ("RC-55", "A-55", "Honeycomb Two", "BOTH", None, None, ("NOTHING_WRONG", 0)),
        ("RC-56", "A-55", "Honeycomb Two", "ANDROID", 660, LOW, ("COUNT_WRONG", 26)),
        ("RC-57", "A-56", "Moss & Ember", "IOS", 1890, HIGH, ("NOTHING_WRONG", 0)),
        ("RC-58", "A-56", "Moss & Ember", "ANDROID", 745, MID, ("AVERAGE_WRONG", 0)),
        ("RC-59", "A-56", "Moss & Ember", "BOTH", None, None, ("COUNT_WRONG", 40)),
        ("RC-60", "A-48", "Quietly Two", "ANDROID", 300, LOW, ("NOTHING_WRONG", 0))]
for cid, app, name, plat, n, skew, design in spec:
    if n:
        listing(app, plat, n, skew, days=rng.choice([(D8,), (D1, D8), (D8, D15)]),
                snap_fmt=rng.choice([",", ",", ".", " "]) if n >= 1000 else ",")
    claims.append((cid, app, name, plat, design))

# --- write inputs with placeholder claims, compute truth, then set claimed figures -------
def append_csv(name, header, rows):
    path = INP / name
    old = path.read_text().rstrip("\n").split("\n") if path.exists() else [",".join(header)]
    out = io.StringIO(); w = csv.writer(out, lineterminator="\n")
    for r in rows:
        w.writerow(r)
    path.write_text("\n".join(old) + "\n" + out.getvalue())


def export_rows():
    for app, plat, day, lv in pulls:
        for s in (5, 4, 3, 2, 1):
            if s in lv:
                yield (app, plat, day, s, lv[s])


append_csv("ratings_breakdown.csv", None, export_rows())
append_csv("listing_snapshot.csv", None, snaps)
append_csv("listing_changes.csv", None, moves)
claims.sort(key=lambda c: int(c[0][3:]))
base_claims = (INP / "claims.csv").read_text()
append_csv("claims.csv", None, [(c[0], c[1], c[2], c[3], "0.0", "0") for c in claims])

# truth does not depend on the claimed figures, so compute it from the placeholder rows
truth = {r["claim_id"]: r for r in build_gold.compute(INP, strict=False)[0]}


def shift(avg, d):
    tenths = int(Fraction(avg) * 10) + d
    return f"{tenths // 10}.{tenths % 10}"


E, P = {}, {}      # effective (after standing corrections) and printed figures
for cid, app, name, plat, (driver, gap) in claims:
    ta, tc = truth[cid]["true_average"], truth[cid]["true_count"]
    ea = shift(ta, rng.choice((-1, 1))) if driver in ("AVERAGE_WRONG", "BOTH_WRONG") else ta
    ec = tc + gap * rng.choice((-1, 1)) if driver in ("COUNT_WRONG", "BOTH_WRONG") else tc
    E[cid] = {"avg": ea, "cnt": ec}
    P[cid] = {"avg": ea, "cnt": ec}
T = {cid: {"avg": truth[cid]["true_average"], "cnt": truth[cid]["true_count"]} for cid in E}
A, C = "claimed_average", "claimed_rating_count"
fix_rows = []
# RC-31 (3-hop chain): count corrected to the effective figure
P["RC-31"]["cnt"] = E["RC-31"]["cnt"] - 57
fix_rows.append(("RC-31", "2026-09-01", C, E["RC-31"]["cnt"]))
# RC-35 (BOTH): printed the true count; the correction made it wrong
P["RC-35"]["cnt"] = T["RC-35"]["cnt"]
fix_rows.append(("RC-35", "2026-08-28", C, E["RC-35"]["cnt"]))
# RC-41: three count corrections out of date order; 09-05 is the latest and stands
P["RC-41"]["cnt"] = T["RC-41"]["cnt"] - 60
fix_rows += [("RC-41", "2026-08-18", C, T["RC-41"]["cnt"] - 40),
             ("RC-41", "2026-09-05", C, E["RC-41"]["cnt"]),
             ("RC-41", "2026-08-30", C, T["RC-41"]["cnt"] - 15)]
# RC-42: average corrected on breakdown_as_of itself (stands); count corrected the day after (not read)
P["RC-42"]["avg"] = shift(E["RC-42"]["avg"], 1)
fix_rows += [("RC-42", "2026-09-08", A, E["RC-42"]["avg"]),
             ("RC-42", "2026-09-09", C, T["RC-42"]["cnt"] + 30)]
# RC-43: both figures corrected
P["RC-43"]["avg"], P["RC-43"]["cnt"] = shift(E["RC-43"]["avg"], -1), E["RC-43"]["cnt"] + 35
fix_rows += [("RC-43", "2026-08-21", A, E["RC-43"]["avg"]),
             ("RC-43", "2026-08-27", C, E["RC-43"]["cnt"])]
# RC-44: an early correction had the average right; the latest put the printed (wrong) one back
fix_rows += [("RC-44", "2026-09-03", A, E["RC-44"]["avg"]),
             ("RC-44", "2026-08-20", A, T["RC-44"]["avg"])]
# RC-45: printed count far off (would be the largest gap); corrected to within 10
P["RC-45"]["cnt"] = T["RC-45"]["cnt"] - 280
fix_rows.append(("RC-45", "2026-08-31", C, E["RC-45"]["cnt"]))
# RC-12: a correction published after breakdown_as_of (not read)
fix_rows.append(("RC-12", "2026-09-12", C, 1450))

text = base_claims.rstrip("\n").split("\n")
for cid, app, name, plat, _ in claims:
    text.append(",".join([cid, app, name if "," not in name else f'"{name}"', plat,
                          P[cid]["avg"], str(P[cid]["cnt"])]))
(INP / "claims.csv").write_text("\n".join(text) + "\n")
append_csv("site_corrections.csv", None, fix_rows)
print("wrote", len(claims), "claims,", len(pulls), "pulls,", len(snaps), "snapshots,",
      len(moves), "moves,", len(fix_rows), "corrections")
