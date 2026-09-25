# Rating-claim verification — the rules

Take every claim the article makes through what follows and through nothing else. The
article's figures are in `claims.csv`, the stores' star-by-star export log in
`ratings_breakdown.csv`, what each listing displayed on the days it was captured in
`listing_snapshot.csv`, the listings that moved to a new `app_id` in
`listing_changes.csv`, the corrections the site has published in `site_corrections.csv`,
and the dates in `verification_facts.csv`. The verification is
taken as it stood on `breakdown_as_of` and on no other day, so nothing below depends on
when this file is read.

A claim is one row of `claims.csv`: an `app_id`, a `platform` (`IOS`, `ANDROID`, or
`BOTH` for one figure quoted across the two stores), the `claimed_average` the article
printed and the `claimed_rating_count` it printed beside it.
Averages are one-decimal figures on a five-star scale; counts are whole numbers.

## 1. Which store figure governs a claim

**1.1** `ratings_breakdown.csv` is the stores' own export log. Each line of a pull gives,
for one app, platform and star level, how many ratings sat at that level on the day in
`pulled_on`. The store's figure for this verification is the pull made on
`breakdown_as_of` and that pull alone: a row pulled on any other day is not read. A pull
covers a listing only where it carries all five of that listing's star levels; a level
nobody chose is still a line, with a `rating_count` of 0, and a pull that carries some of a
listing's levels but not all five does not cover it. Wherever the `breakdown_as_of` pull
covers the claim's listing, under the `app_id` that listing reported under that day
(rule 1.5), its rows are the store's figure and nothing else is. They are read under
rule 2.

**1.2** `listing_snapshot.csv` is what each listing displayed on its `captured_on` date.
It is older than the export, so where the `breakdown_as_of` pull covers the listing the
snapshot decides nothing — not the count and not the average, however the two compare.

**1.3** Where the `breakdown_as_of` pull does not cover the claim's listing,
the listing's snapshot is the store's only figure for it and stands as the true figure,
read under rule 3. The snapshot that counts is the one captured on `snapshots_captured_on`,
while the article was being written; a capture from any other day is not read. There is no
newer figure to prefer.

**1.4** An export row or a snapshot that belongs to no claimed listing is not verified
and earns no register row.

**1.5** A listing can move. Each row of `listing_changes.csv` is one move: from
`changed_on` onwards, the listing that reported under `app_id` reports under `new_app_id`,
on the same platform. A `transferred` listing keeps its ratings, so its export rows from
that day are the rows under `new_app_id`. A `relaunched` listing starts again from
nothing: the rows under `new_app_id` are a new listing's ratings and never the claim's,
and the claim's listing has no export from that day. A move dated after
`breakdown_as_of` changes nothing for this verification. A claim names its listing by the
`app_id` the article printed; snapshots are filed under the `app_id` the listing carried
on the day they were captured.

**1.6** A `BOTH` claim quotes one figure for the app across the two stores. Its `IOS`
listing and its `ANDROID` listing are each taken through rules 1.1 to 1.5 and rule 3 on
their own. Its `true_count` is the two listings' counts added. Its `true_average` is the
mean of every rating on the two listings together, rounded once as in rule 2.2: a listing
read from the export contributes each of its ratings at its star level, and a listing read
from a snapshot contributes each of its ratings at its displayed average.

## 2. The true figures from the export

**2.1** `true_count` is the `rating_count` of the five star levels in the
`breakdown_as_of` pull for the claim's listing, added together.

**2.2** `true_average` is the weighted mean of the export — each star level's value
multiplied by its `rating_count`, added across the five levels, divided by
`true_count` — rounded ONCE to one decimal place with a half rounded up: a mean of 2.45
is written 2.5, and a mean of 1.15 is written 1.2. It is written with its one decimal — `4.0`, never
`4`.

## 3. Reading a displayed string

**3.1** A `displayed_string` reads `<average> out of <count> Ratings`. The leading number
is the average as the store displays it, already to one decimal, and it stands as
`true_average` with no further rounding. The trailing number, with its thousands
separator removed, whichever mark the storefront prints between thousands, is
`true_count`.

**3.2** Read the string as it is printed, whatever its spacing: the trailing number is the
rating count in full, and the five-star scale is never printed in that string.

## 4. What the article got wrong

**4.0** The article is taken as it stood on `breakdown_as_of`. `site_corrections.csv` is
every correction the site has published: each line replaces one figure of one claim —
`field` names which, `new_value` is the figure printed in its place — from `corrected_on`.
A correction published on or before `breakdown_as_of` stands, one published later is not
read, and where a figure was corrected more than once the latest correction that stands is
the one printed. From here on, `claimed_average` and `claimed_rating_count` mean the
figures as they stood after those corrections.

**4.1** The claim's average is wrong where `claimed_average` is not `true_average` from
rule 2, 3 or 1.6, compared as one-decimal figures. Its count is wrong where
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
