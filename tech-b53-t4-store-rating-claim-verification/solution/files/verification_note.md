# The couples-app roundup, checked against the stores

Every rating figure the article quotes has been recomputed from the stores' own
star-by-star export as pulled on 8 September, following each listing that has since moved
to a new store id. Where that pull does not cover a listing — no lines for it at all, or
only some of its five star levels — the figure is read off the listing itself as it was
displayed on 10 August, while the article was being written. The article is taken with
the corrections the site had already published by 8 September; a correction published
after that day is not counted. The register delivered with this note gives each claim the
store's real average and count and names the figure the article got wrong, where it got
one wrong at all.

Confirmed in full: 25. On each of those the average and the number of ratings the article
quotes are the store's own figures to the decimal, and there is nothing to correct.

Miscounted: 15. On each of those the article's average is the store's but its number of
ratings is not.

RC-12 is the claim with the widest gap on the page, and its `driver` is `COUNT_WRONG`.
The article quotes 1,240 ratings for that listing where the store's export shows 1,450,
so the count is short by 210. The average quoted beside it is the store's own.

RC-04 is the closest call in the article, and its `driver` is `AVERAGE_WRONG`.
The store's ratings for that listing work out to exactly 4.35, which the store's own rule
rounds up to 4.4; the article's 4.3 is the figure you get by cutting the mean short, or by
rounding a stored approximation of it that sits a hair under the half. It is out by the
narrowest margin a one-decimal figure allows, and it is still out.

The remaining claims are on the register with the store's figures beside them. Where an
average is wrong on its own, the cause is a rounding the article did differently from the
store; where the count and the average are wrong together, the article seems to have been
working from figures that were never the store's at all.
