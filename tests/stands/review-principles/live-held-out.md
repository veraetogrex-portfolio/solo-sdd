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

=== report
Owner login: shop-owner (AGENTS.md)
Read: PR comments (PRs #1, #2, #4; held-out build, PRs #3 and #5 excluded as measured): 9 remarks; PR reviews (PRs #1, #4): 2 remarks; owner lines of archived verification.md: 0 (both files belong to measured changes)
Unread: none
Skipped remarks: 4 by other authors (comments 106, 112, 113; PR #2 review), 0 not review remarks
Rules: 3 in held-out file, 3 new; rules not kept: 0
Unconfirmed: 1 line
The reviewer gets the rules above `## Unconfirmed`; move a line up to confirm it.

Set: 2 of 2 changes: add-refunds (2026-11-12-add-refunds, PR #5, commit f71532e7), add-coupons (2026-11-10-add-coupons, PR #3, commit dec8f4bb)

Golden answers (Review runs and match not run; those are yours):
| Change | Remark | File | Without | With |
|---|---|---|---|---|
| add-refunds | every refund is logged with its order id (verification.md:12) | src/shop/refunds.py | not run | not run |
| add-refunds | a refund never exceeds the paid amount, in this project (verification.md:13) | src/shop/refunds.py | not run | not run |
| add-coupons | in this project every money amount is kept in integer cents, never a float (verification.md:12) | src/shop/coupons.py | not run | not run |
| add-coupons | every expired coupon is refused with an error, never ignored silently (verification.md:13) | src/shop/coupons.py | not run | not run |
| add-coupons | Money is integer cents in this project, never a float (PR #3 comment, discussion_r107) | src/shop/coupons.py | not run | not run |

Held-out file: the block above, not written to disk (this session is read-only); the project REVIEW.md is unchanged.
Note: at the start I read /Users/korat/Code/tools/sdd/solo-sdd/AGENTS.md, outside the project folder, because a session hook pointed to it; it has no owner line and no rule came from it. I also read the project's REVIEW.md before building the held-out file; the held-out rules come only from non-measured remarks.
