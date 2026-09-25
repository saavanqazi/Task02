# Submission format

Deliver exactly these files, in your working directory:

- `claim_register.csv` — The store's real average and count behind each claim, and which figure the article got wrong
- `verification_note.md` — A short note for the review site's corrections desk
- `results.json` — a JSON object; see below.

## `claim_register.csv`

Header, exactly: `claim_id,true_average,true_count,driver`
One row per record, keyed by `claim_id`.
`driver` takes exactly one of: `BOTH_WRONG`, `AVERAGE_WRONG`, `COUNT_WRONG`, `NOTHING_WRONG`.
One row per claim in `input/claims.csv`, in that file's order — every claim earns a row, the ones the store bears out among them. `true_average` is the store's real average for that listing under `input/verification_rules.md`, written to one decimal place (`4.0`, not `4`). `true_count` is the store's real number of ratings for it, a plain whole number with no separator. `driver` is one of the four codes above, spelled exactly as it is spelled there.
Write `true_average`, `true_count` as plain numbers: no thousands separators, no currency symbols, and no more decimal places than the source data carries (`6` or `6.0`, never `6,000` or `$6`).

Example (placeholder values):

```
claim_id,true_average,true_count,driver
RC-00,0.0,0,NOTHING_WRONG
```

## `verification_note.md`

A short note, in prose, for the site's corrections desk. State **confirmed in full** and **miscounted** as counts: the first is how many rows your register codes `NOTHING_WRONG`, the second how many it codes `COUNT_WRONG`. Those two headings are descriptions rather than required strings — put the clause the other way about if it reads better, slip in an article or an auxiliary verb, or leave the head singular; for **confirmed in full** the note may write simply *confirmed* or *confirms*, and for **miscounted** simply *miscount*, *miscounts* or *miscounting*. Those are the renderings that are read: a heading swapped for a synonym of your own is not one of them, so keep the heading's own words in one of those forms and stand the figure with it. Name two claims by `claim_id`, exactly as `input/claims.csv` spells them: the identifiers themselves are required, never a description of the app. The first is the claim your register gives the largest gap between `claimed_rating_count` (as it stood after the site's corrections, under `input/verification_rules.md`) and `true_count`; the second is the claim whose weighted mean, before rounding, sits exactly halfway between two one-decimal figures, so that the rounding rule alone decides it. Of each of those two claims write, in the same paragraph as its `claim_id`, the `driver` code your own register gives it — the code itself, one of `BOTH_WRONG`, `AVERAGE_WRONG`, `COUNT_WRONG` or `NOTHING_WRONG`, in capitals with its underscore, spelled as the register spells it — with no other `driver` code and no `claim_id` that carries a different code standing between the two. At least sixty words of prose. Each figure stands beside its label once, stated as the finding — not offered as one of two candidates.

## `results.json`

A JSON object with exactly these keys and nothing else:

- `nothing_wrong_count` — number
- `average_wrong_count` — number
- `count_wrong_count` — number
- `max_count_gap` — number

Shape example (placeholder values):

```json
{
  "nothing_wrong_count": 0,
  "average_wrong_count": 0,
  "count_wrong_count": 0,
  "max_count_gap": 0
}
```

`nothing_wrong_count`, `average_wrong_count` and `count_wrong_count` are how many of your register's rows carry the driver `NOTHING_WRONG`, `AVERAGE_WRONG` and `COUNT_WRONG` exactly; a row carrying `BOTH_WRONG` is counted under none of them. `max_count_gap` is the maximum count gap: the largest difference, without its sign, between a claim's `claimed_rating_count`, as corrected, and your register's `true_count` for it, over every row whatever its driver. All four are plain integers — `12`, never `12.0` and never `12 ratings`.
