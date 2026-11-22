=== report
Set: 2 of 2 changes: add-refunds, add-coupons
| Variant | Matched | Missed | Extra |
|---|---|---|---|
| without REVIEW.md | 2 | 3 | 7 |
| with REVIEW.md | 1 | 4 | 3 |
| Change | Remark | File | Without | With |
|---|---|---|---|---|
| add-coupons | every money amount in integer cents, never a float (verification.md:12) | src/shop/coupons.py | matched: coupons.py:10 money computed in binary float | matched: coupons.py:10 money worked out in float |
| add-coupons | every expired coupon refused with an error (verification.md:13) | src/shop/coupons.py | missed | missed |
| add-coupons | money is integer cents, never a float (#3, discussion_r107) | src/shop/coupons.py | missed | missed |
| add-refunds | every refund logged with its order id (verification.md:12) | src/shop/refunds.py | missed | missed |
| add-refunds | a refund never exceeds the paid amount (verification.md:13) | src/shop/refunds.py | matched: refunds.py:21 nothing checks the refund against the order total | missed |

Matched by the lead (not a reviewer): a finding matches a remark when it names the remark's file and the same problem; one finding matches at most one remark. The `coupons.py:8` findings of both variants are about the expiry day and a type error, not about an expired coupon ignored silently: no match. The `with` reviewer of add-refunds returned no finding (`Important: 0`).
=== REVIEW.md (held out)
# Review rules

The owner's review rules, collected by `/review-principles` from the owner's PR remarks and the owner lines of archived changes. The `Review:` reviewer of `spec-next` gets the rules and not `## Unconfirmed`. The owner edits, adds or moves lines by hand: a rerun keeps every rule as it stands.

## Rules

1. Never catch a bare `except:`; name the exception. — [#1](https://github.com/example/shop/pull/1#discussion_r101), [#2](https://github.com/example/shop/pull/2#discussion_r104)
2. Every function that opens a file uses `with`. — [#1](https://github.com/example/shop/pull/1), [#4](https://github.com/example/shop/pull/4#discussion_r108)
3. Every public function has a docstring. — [#2](https://github.com/example/shop/pull/2#discussion_r105), [#4](https://github.com/example/shop/pull/4#discussion_r109)

## Unconfirmed

Patterns the owner's remarks show but the owner never stated as a rule. Move a line up into `## Rules` to confirm it, delete it to reject it.

- Split a function longer than 15 lines. — [#1](https://github.com/example/shop/pull/1#discussion_r102), [#2](https://github.com/example/shop/pull/2#discussion_r103), [#4](https://github.com/example/shop/pull/4#discussion_r110), [#4](https://github.com/example/shop/pull/4#discussion_r111)

