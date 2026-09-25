# Task

A review site I read ran a roundup of couples apps last month, and every entry quotes a star rating and how many people rated it. I was about to pay for one of them on the strength of its score, so before I do I want every figure the article quotes checked against what the stores themselves show. `input/claims.csv` is each figure the article printed and `input/site_corrections.csv` the corrections the site has since run; `input/ratings_breakdown.csv` is the stores' star-by-star export log, `input/listing_snapshot.csv` what each listing displayed when captured, `input/listing_changes.csv` the listings that moved to a new id, and `input/verification_facts.csv` the dates. Work them under `input/verification_rules.md`. Save `claim_register.csv` giving each claim the store's real figures and what, if anything, the article got wrong about it, write `verification_note.md` as something I can send to the site's corrections desk, and put the headline figures in `results.json`. File layout is in `input/submission_format.md`.

---
Save your deliverables into your current working directory using exactly these filenames:
    - `claim_register.csv` — The store's real average and count behind each claim, and which figure the article got wrong
    - `verification_note.md` — A short note for the review site's corrections desk
    - `results.json` — a JSON object with the keys `nothing_wrong_count`, `average_wrong_count`, `count_wrong_count`, `max_count_gap`
- The exact headers, key sets, allowed values and worked examples are specified in `input/submission_format.md` — follow it precisely.
- Writing those files is the required deliverable and must be your final action; confirm each one exists before you answer.

---

## Working environment

- Your current working directory is writable.
- The read-only attachments referred to as `input/` are in the `input/` folder inside it.
- Write every deliverable into your current working directory, at the exact filenames listed above.
