# Roadmap — `tech-b53-t4-store-rating-claim-verification`

## Status and decisions (updated)

| Item | Decision / state |
|---|---|
| CRLF line endings (**new blocker found**) | **FIXED.** Every text file in the zip had Windows line endings, so `solve.sh` died on `set -euo pipefail\r` and `test.sh` wrote into `/logs/verifier\r`: **the Oracle could not score at all.** All files are now LF, and `.gitattributes` (`* -text`) stops git from converting them back on Windows. Emulated oracle: 1.0, 14/14 checks, 22/22 pytest lanes |
| Incidental note checks (6) | **Keep.** Each maps 1:1 to a stated ask in `submission_format.md`. None is tagged `secondary`. Deleting them would leave asks with no verifier |
| `consistency/` | **Removed** (not shipped) |
| `evaluations/nop`, `evaluations/oracle` | **Removed** (R17 / no oracle evidence ships) |
| `/app` footer in `instruction.md` | **Rewritten without absolute paths.** The agent's cwd is the image `WORKDIR` (`/app`), so "your current working directory" and "`input/` inside it" mean the same thing |
| verifier.json → manifest.json | **Converter written and tested:** `tools/convert_to_manifest.py`. Run it only in Phase 6 (the last step), then re-run the Oracle |
| GLM config | `glm-harbor-config.json` (validated against harbor 0.23.0) |

Repo layout: `tech-b53-t4-store-rating-claim-verification/` is the working task folder. The
commit `Baseline: mined task package exactly as received` is the untouched original, which you
diff against for the README.

Phase-by-phase plan to take the mined package to a submittable bundle:
Oracle exactly 1.0, GLM-5.2 in the 1–3 of 4 band, clean evidence layout, README.md +
review.csv + qc_report.html at the root.

---

## 0. What the task is (read this first)

A user wants to check an article's app-rating claims against the app stores' own figures.
The inputs are in `environment/input/`:

| File | Role |
|---|---|
| `claims.csv` | 15 claims (RC-01..RC-15): app, platform, claimed average, claimed count |
| `ratings_breakdown.csv` | star-by-star store export (governs wherever it has rows) |
| `listing_snapshot.csv` | older displayed strings (`4.4 out of 1,190 Ratings`), fallback only |
| `verification_facts.csv` | dates (`breakdown_as_of` 2026-09-08, etc.) |
| `verification_rules.md` | the method: export > snapshot, weighted mean, **round half up once**, string parsing, driver codes |
| `submission_format.md` | exact output contract |

Deliverables: `claim_register.csv` (claim_id,true_average,true_count,driver),
`verification_note.md` (corrections-desk note), `results.json` (4 integer keys).

**Package type: non-connector.** There's no `environment/_app/` mirror and no
`sync_app_mirror.sh`, so the mirror rule doesn't apply. You iterate on
`tests/verifier.json` and rewrite it to `tests/manifest.json` as the **last** packaging step.

---

## 1. Audit findings (already done in this session)

### 1.1 The gold is correct
I recomputed every row from the inputs with exact `Fraction`/`Decimal` math. All 15
register rows match `solution/files/claim_register.csv`, and `results.json` matches
(6 / 4 / 3 / 500).

I also ran the shipped grader locally (Python 3.12, because the engine ships as 3.12 `.pyc`)
against the gold. `score.py` gives **reward 1.0, 14/14**, and `test_outputs.py` passes
**22/22** (positive, incomplete, corrupted-value and extra-key lanes).

### 1.2 Traps the task already contains

| # | Trap | Where | What a naive solver produces |
|---|---|---|---|
| T1 | No export rows for A-04 ANDROID, so it falls back to the snapshot `4.4out of 533 Ratings` (the space is missing) | RC-07 | Reads "out of 5" + "33". That matches the claim of 33, so it gets NOTHING_WRONG, and max_count_gap drops from 500 to 210 |
| T2 | Mean is exactly 4.25, which rounds half up to 4.3 | RC-04 | Python `round()` or banker's rounding gives 4.2, so it gets NOTHING_WRONG |
| T3 | Double-rounding traps: 4.2475 and 4.045 | RC-02, RC-13 | Rounding to 2 decimals first gives 4.3 and 4.1 (wrong) |
| T4 | Snapshot counts are stale and the export wins | 8 claims | Using the snapshot gives wrong counts and drivers |
| T5 | A-10 appears in the inputs but nobody claimed it | — | Adds an extra register row, which fails the population lock |
| T6 | Joining on app_id only | RC-07 | Uses A-04 **IOS** export (1680), which is the wrong listing |

### 1.3 Leakage (fix in hardening)
- **L1 (answer leak):** the example in `verification_rules.md` §2.2, "a mean of **4.25** is written 4.3", is
  *exactly* RC-04's mean. That pre-solves T2.
- **L2 (recipe):** the worked example in §3.2, `4.6out of 512 Ratings` → 512, pre-solves T1.
- **L3 (acceptable):** `submission_format.md` defines "the claim whose mean sits exactly halfway". That is
  the definition of what the note must name, so it stays. It does reveal that a half case exists.
- **L4 (done: paths removed):** the harness footer in `instruction.md` mentions `/app/input`. The guide says no
  `/app/input` paths, but this footer is the standard harness contract. Keep it unless told otherwise.

Ambiguity scan: I found no genuine two-answer readings in the current rules.

### 1.4 Verifier audit (`tests/verifier.json`, 14 checks)

| Check | Tag | Maps to instruction item |
|---|---|---|
| register_exists | core | save claim_register.csv |
| register_header | core | exact header |
| register_table | core | 14 rows × 3 cells + population and order lock |
| register_table_trap_rc07 | core | RC-07 row (the T1 trap), split out |
| results_exists / results_figures | core | results.json, 4 keys, closed key set |
| note_exists | incidental | save verification_note.md |
| note_prose_floor | incidental | ≥ 60 words |
| note_largest_gap | core | name the max-gap claim + its driver, same paragraph |
| note_half | core | name the half-case claim + its driver, same paragraph |
| note_confirmed (+ _exactly_one) | incidental | "confirmed in full" count = 6, no hedging |
| note_miscounted (+ _exactly_one) | incidental | "miscounted" count = 3, no hedging |

- None of the checks has a `"category": "secondary"` field, so nothing is auto-deleted. The package uses
  `metadata.tag` core/incidental instead. An incidental failure gives 0.929, which is *not* a full pass.
  **Decided: keep them.** The original question was whether "incidental" counts as "secondary". If yes, deleting those checks means also
  deleting the matching asks from `submission_format.md`, so that no ask is left without a verifier.
  My recommendation is to keep them, because they map 1:1 to stated asks and the platform scores 1/N.
- The regex-heavy checks are `note_*`. The co-naming regexes embed a list of claim IDs whose drivers
  differ, so they **must be regenerated programmatically** after any data change. Never hand-edit them.
- There is no LLM judge anywhere, so `JUDGE_MODEL` does not matter for grading.

### 1.5 Packaging defects to fix
- (done) `evaluations/nop/` and `evaluations/oracle/` must be **deleted**. The bundle ships no oracle evidence, and
  gate rule R17 scores `nop/` as a failed model run.
- (done) `consistency/` is mining-pipeline evidence keyed to the current `revision_key`. It becomes stale
  (misleading) after hardening. Remove it before the final zip, or regenerate it if the team has the tool.
  Confirm this with the lead.
- `tests/test.sh` writes `score.json`, `reward.txt` and `ctrf.json`, but **no `verifier_summary.json`**,
  which the `difficulty/rN/verifier/` spec requires. Check whether Harbor adds it. If not, ask the lead for
  the expected schema.
- In `task.toml`, `authors = []`. Fill it in if the team wants that. Do **not** rename `[task].name`,
  because the platform links versions by it.

---

## Phase 1 — Setup on Windows (cmd)

Folder layout:
```
C:\Users\amitb\Task02\
  glm.env                      your key file (never inside repo\, never zipped)
  original\                    the mined zip + its extraction: read-only reference, never run
  repo\                        git clone of this branch: the ONLY copy you run and edit
    tech-b53-t4-store-rating-claim-verification\
    tools\   glm-harbor-config.json   ROADMAP.md
  jobs\                        harbor output (created automatically)
```

One-time install (Docker Desktop must be running, WSL2 backend):
```bat
py -3.12 -m pip install --upgrade harbor
harbor --version
docker version
cd /d C:\Users\amitb\Task02
git clone -b claude/peaceful-mayer-w7be20 https://github.com/saavanqazi/task02 repo
```
Harbor needs Python ≥ 3.12. Without git, use GitHub's "Download ZIP" on the branch and extract it
to `repo\`.

**Never** open and save `.sh` files in Notepad, and never run the task from `original\`. The
original has the CRLF bug.

`glm.env` needs no quotes and no spaces around `=`. Harbor reads it with `--env-file`, so you don't
need to `set` anything in cmd. If your harbor build has no `--env-file`, load it into the session:
```bat
for /f "usebackq tokens=1,* delims==" %a in ("C:\Users\amitb\Task02\glm.env") do set "%a=%b"
```
(Inside a `.bat` file, write `%%a` / `%%b`.)

## Phase 2 — Baseline Oracle and GLM battery (≈ 1–2 h wall clock)
All commands run from `C:\Users\amitb\Task02\repo`:
```bat
cd /d C:\Users\amitb\Task02\repo

:: Oracle, twice (must be 1.0 both times). No LLM judge in this task, so no --ve is needed.
harbor run -p tech-b53-t4-store-rating-claim-verification -a oracle -o ..\jobs --job-name oracle-b53t4-base-1 -n 1 -y
harbor run -p tech-b53-t4-store-rating-claim-verification -a oracle -o ..\jobs --job-name oracle-b53t4-base-2 -n 1 -y

:: Budget check, then a 1-run smoke test, then the 4-run battery
docker ps --format "{{.Names}}"
harbor run -c glm-harbor-config.json --env-file ..\glm.env --job-name b53t4-glm-smoke -y
harbor run -c glm-harbor-config.json --env-file ..\glm.env --job-name b53t4-glm-base -k 4 -n 3 -y

:: Read the rewards (one line per trial)
for /d %d in (..\jobs\b53t4-glm-base\*) do @(echo %~nxd & type "%d\verifier\reward.txt" & echo.)
harbor view ..\jobs
```
`-n` is `3 − (containers already running)`. If native-Windows harbor errors on paths or compose,
run the same commands in WSL Ubuntu against the same folder (`/mnt/c/Users/amitb/Task02/repo`),
with `\` → `/`.

1. Both Oracle runs must be **1.0**.
2. The smoke test must finish with a reward and a `trajectory.json`. A 0.0 with `exception.txt` is infra,
   not difficulty.
3. Record all 4 rewards and read every check in each failing run's `verifier\score.json` (this task's
   per-check detail). Classify each failure as MODEL, ambiguity, verifier bug or infra.
4. The expected outcome is **4/4**: the rules text spells out T1 and T2 (L1, L2), and the other traps are
   mechanical. Keep these runs as baseline evidence for README and review.csv. They do **not** ship.
5. If the baseline is already 1–3/4 with MODEL-class failures, skip to Phase 5 (verify) and Phase 6.

## Phase 3 — Hardening design (only if the baseline is 4/4)
Apply one lever family per round, cheapest first. Every new edge must have **exactly one reading** under
the rules, stated as a general rule and never demonstrated with a value that is in the data.

**Round A — remove leakage (instruction and rules only)**
- §2.2: replace the examples 4.25→4.3 and 3.85→3.9 with values that are in no listing, e.g. `2.35 → 2.4`,
  `1.65 → 1.7`. Keep "half rounded up, once, no intermediate rounding" explicit.
- §3.2: delete the `4.6out of 512` demo string. Keep the general sentence: "the trailing number is the count
  in full; no digit of it belongs to a scale."
- Re-run the Oracle and the 4-run battery. Stop if the result lands in 1–3/4.

**Round B — coupled data edges (the main lever). Use only if Round A still gives 4/4.**
- **Date-scoped export (chained plus state across steps).** Add a `pulled_on` column to
  `ratings_breakdown.csv`. Most rows are dated `2026-09-08`. Add a later re-pull (e.g. `2026-09-15`) for
  2–3 claimed listings with different counts, which must be excluded. Also give one more claimed listing
  export rows **only** on the later date, so it falls back to the snapshot. That couples the date filter,
  rule 1.3 and the string parser, and it moves `max_count_gap`.
  Update rules §1.1 and §1.3 to "rows pulled on `breakdown_as_of`", and update `export_note` in
  `verification_facts.csv` to match. Otherwise the export note and the rules contradict each other.
- **Snapshot history (cross-source).** Give the fallback listings a second capture dated after
  `article_published`. The rules must say which capture governs: the one on `snapshots_captured_on`.
- **Optional:** one listing missing a star-level row. Add the rule "a level with no row has no ratings".
- **Invariants to hold after the data change:** exactly **one** exact-half mean; a **unique** max count gap;
  every driver class has at least 2 members; no ties; the IDs the note must name stay unambiguous.

Avoid these levers: platform-casing tricks, "1.2K"-style abbreviations, and hidden rules. Any of them turns
the task ambiguous or unfair rather than harder.

## Phase 4 — Rebuild gold and verifiers in lockstep (after every data or rules change)
1. Write a generator script (e.g. `solution/build_gold.py`) that computes from the inputs with
   Fraction/Decimal and emits:
   - `solution/files/claim_register.csv`, `results.json` and `verification_note.md` (rewrite the prose to
     the new facts: largest-gap claim, half-case claim, the counts)
   - `solution/golden_trajectory.json` (the `printf` steps carry the file bodies)
   - every expected value in `tests/verifier.json`: the register_table rows, the trap-row check (rename it
     if the trap claim moves), results_figures, and the note regexes (figure values, target ID and the
     "different-driver" ID exclusion lists)
2. Fast local checks on Python 3.12:
   - gold scores 1.0 (14/14) and pytest passes every lane
   - **wrong-answer mutants each score 0**: banker's rounding, 2-decimal pre-rounding, summing all
     `pulled_on` dates, misparsing `…out of 533`, snapshot-over-export, app-only join
   - **fair-paraphrase notes each score 1.0**: 3–4 differently worded correct notes (clause order swapped,
     bullets, a table). This guards against strict regex.
   - reward-hack shapes are still caught (label soup, hedging, duplicate rows, cross product; see
     `consistency/attacks.json`)
3. Run the official Oracle **twice**. Both must be exactly 1.0.

## Phase 5 — GLM re-battery and calibration loop
1. Budget check, 1 smoke run, then the 4-run battery. Record the 4 individual rewards.
2. Interpret:
   - **1–3/4** with MODEL failures: stop hardening.
   - **4/4**: move to the next lever (Round B, then the optional edge).
   - **Bimodal results**, or every failure on the same new rule: that is an ambiguity. Fix the wording and
     re-run all 4.
   - **0/4**: check fairness first. It can still be submitted, but Turing re-runs it on another model.
3. A verifier-only change can be re-graded against the existing rollouts. A change to the instruction, rules
   or data invalidates them, so re-run all 4.

## Phase 6 — Final packaging
1. **Convert:** `py -3.12 tools\convert_to_manifest.py tech-b53-t4-store-rating-claim-verification`.
   This writes `tests\manifest.json` (the verifier list), repoints `score.py` and `test_outputs.py`,
   and deletes `verifier.json`. It self-checks that the gold still scores 1.0 with identical per-check
   verdicts. It needs the grader deps in that Python
   (`py -3.12 -m pip install pytest==8.4.1 pytest-json-ctrf==0.3.5 pydantic==2.12.5 "jsonpath-ng>=1.6,<2" "tenacity>=9,<10"`).
   Then re-run the **Oracle (1.0)** with harbor.
2. Already done: `evaluations/nop/`, `evaluations/oracle/` and `consistency/` are removed.
   Delete any `__pycache__` folders before zipping.
3. `evaluations/difficulty/r1..r4/`: copy the four trial folders **unflattened**. Each needs
   `agent/trajectory.json`, `result.json`, `verifier/reward.json`, `verifier/verifier_summary.json` and
   `config.json`. No job-level `config.json`, `lock.json`, `job.log` or job-root `result.json`.
4. Each `result.json` needs `"model": "GLM-5.2"`, a boolean `overall_pass`, `final_answer`, `reward`, and
   judge provenance. Here that is "no LLM judge; deterministic checks only".
5. `evaluations/solvability/r1/`: a copy of one **passing** GLM rollout, never the Oracle.
6. Do not add `stability/` (unless you have real repeats) or `platform/`. Nothing loose under `evaluations/`.

## Phase 7 — README.md and review.csv (written by you)
**README.md** is short and cumulative. It covers:
- the baseline and its first battery result
- each hardening round, what changed and why
- why the task is hard (the trap chain in 1.2 plus any Round B edges)
- any gate flag left open and why (for example R3 stability, which Turing runs)

**review.csv** must be written through the review form by you. A model-written review is exactly what the
client rejects. The header is `review_check,status,review_notes,change_made,what_to_record`. Expected shape:

| Area | Likely status | Evidence to cite |
|---|---|---|
| Layer 1 · Package consistency | FIXED_AND_VERIFIED | removed evaluations/nop and oracle; converted to manifest.json; oracle re-run |
| Layer 1 · Clarity and scope | PASS or FIXED_AND_VERIFIED | rules edits in Rounds A/B |
| Layer 1 · Realism and leakage | FIXED_AND_VERIFIED | L1 and L2 removed; re-battery |
| Layer 2 Difficulty | FIXED_AND_VERIFIED | baseline 4/4 → final x/4, all 4 rewards listed |
| Layer 2 Solvability | PASS | evaluations/solvability/r1 |
| Layer 2 Stability | blank or "Turing runs this" | — |
| Layer 3 Oracle Mode | PASS | oracle 1.0 on repeated runs after the final change |
| Layer 4 · Environment and files | PASS or FIXED_AND_VERIFIED | Dockerfile copies input/ only, read-only, Python 3.12 matches the `.pyc` |
| Layer 4 · Connectors, MCPs, and CLIs | N/A | non-connector, `mcp_servers = []` |
| Layer 4 · Deliverables and artifact quality | FIXED_AND_VERIFIED | gold regenerated |
| Layer 5 · Verifier coverage and fairness | FIXED_AND_VERIFIED | forward and backward map, paraphrase tests |
| Layer 5 · LLM judge consistency | N/A (give the reason) | no judged rubric; all 14 checks deterministic |
| Layer 5 · Reward hacking and exploitability | PASS | attack mutants all caught |
| Cross-trial · Calibration | blank or "Turing runs this" | — |

## Phase 8 — Delivery Gate and submission
1. Zip **the task folder only**. On Windows, from `repo\`: `tar -a -c -f ..\b53t4.zip tech-b53-t4-store-rating-claim-verification`
   (built-in bsdtar keeps bytes and LF endings as they are). Upload it to the QC platform and run the Delivery Gate.
2. Triage the findings. R3 (stability) is expected: mark it reviewed with "Turing runs stability".
3. Download `qc_report.html` and put it at the task root next to `review.csv`. Re-zip and upload it as a
   **new version** of the same task, then run the Gate again.
4. Before you submit, check all five conditions: it is a Harbor bundle, the Gate passes, the score is at or
   above the floor, review.csv is present and every row is resolved, and this version has not been submitted.
   Then submit.

---

### Who does what
- **Can be done in a Claude session:** Phase 3 edits, the Phase 4 generator and regenerated gold and
  verifiers, the fast local grader checks and mutant/paraphrase tests, the Phase 6 file restructuring, and
  a README draft.
- **Needs your machine or account:** harbor Oracle and GLM runs (your key and proxy), the QC platform,
  the review form (review.csv must be human-written), and the Delivery Gate and submission.
