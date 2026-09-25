# Rating-claim verification — the rules

Take every claim the article makes through what follows and through nothing else. The
article's figures are in `claims.csv`, the stores' star-by-star export in
`ratings_breakdown.csv`, what each listing displayed when the article was being written
in `listing_snapshot.csv`, and the dates in `verification_facts.csv`. The verification is
taken as it stood on `breakdown_as_of` and on no other day, so nothing below depends on
when this file is read.

A claim is one row of `claims.csv`: an `app_id`, a `platform`, the `claimed_average` the
article printed for that listing and the `claimed_rating_count` it printed beside it.
Averages are one-decimal figures on a five-star scale; counts are whole numbers.

## 1. Which store figure governs a claim

**1.1** `ratings_breakdown.csv` is the stores' own export, pulled on `breakdown_as_of`:
one row per app, platform and star level, giving how many ratings sit at that level.
Wherever the export carries rows for the claim's `app_id` and `platform`, those rows are
the store's figure and nothing else is. They are read under rule 2.

**1.2** `listing_snapshot.csv` is what each listing displayed on its `captured_on` date,
before the article went up. It is older than the export, so where the export carries rows
the snapshot decides nothing — not the count and not the average, however the two
compare.

**1.3** Where the export carries no rows at all for the claim's app and platform, the snapshot is the store's only figure for that listing and it stands as the true figure, read under rule 3. There is no newer figure to prefer.

**1.4** An export row or a snapshot for an app the article makes no claim about is not
verified and earns no register row.

## 2. The true figures from the export

**2.1** `true_count` is the `rating_count` of the five star levels for that app and
platform added together.

**2.2** `true_average` is the weighted mean of the export — each star level's value
multiplied by its `rating_count`, added across the five levels, divided by
`true_count` — rounded ONCE to one decimal place with a half rounded up: a mean of 4.25 is written 4.3, and a mean of 3.85 is
written 3.9. Do not round to two decimals on the way, do not cut the mean short, and do
not round a half to the even digit. It is written with its one decimal — `4.0`, never
`4`.

## 3. Reading a displayed string

**3.1** A `displayed_string` reads `<average> out of <count> Ratings`. The leading number
is the average as the store displays it, already to one decimal, and it stands as
`true_average` with no further rounding. The trailing number, with any thousands
separator removed, is `true_count`.

**3.2** Read the string as it is printed: the trailing number is the rating count in full: the five-star scale is never printed in that string, so no digit of the trailing number belongs to a scale. A listing that has dropped the
space and reads `4.6out of 512 Ratings` displays 512 ratings, not `out of 5` followed by
twelve.

## 4. What the article got wrong

**4.1** The claim's average is wrong where `claimed_average` is not `true_average` from
rule 2 or 3, compared as one-decimal figures. Its count is wrong where
`claimed_rating_count` is not `true_count` — exactly: there is no tolerance, and a count
out by one is a wrong count.

**4.2** The `driver` is `BOTH_WRONG` where the average and the count are both wrong,
`AVERAGE_WRONG` where only the average is, `COUNT_WRONG` where only the count is, and
`NOTHING_WRONG` where neither is.

## 5. What is reported

`nothing_wrong_count`, `average_wrong_count` and `count_wrong_count` are how many claims
carry the `driver` `NOTHING_WRONG`, `AVERAGE_WRONG` and `COUNT_WRONG` exactly. A
claim carrying `BOTH_WRONG` is counted under none of the three. `max_count_gap` is the
maximum count gap on the page: each claim's gap is the difference, taken without its
sign, between its `claimed_rating_count` and its `true_count`, a claim under the true
count and a claim over it both carrying one, and the maximum is taken across every claim
whatever its `driver`. It is written as a plain whole number.
