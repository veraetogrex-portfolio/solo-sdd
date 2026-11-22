=== report
Set: 2 of 2 changes: add-refunds, add-coupons
| Variant | Matched | Missed | Extra |
|---|---|---|---|
| without REVIEW.md | 3 | 2 | 2 |
| with REVIEW.md | 3 | 2 | 1 |
| Change | Remark | File | Without | With |
|---|---|---|---|---|
| add-coupons | money in integer cents (line) | src/shop/coupons.py | matched: coupons.py:10 float discount | matched: coupons.py:10 float discount |
| add-coupons | expired coupon refused | src/shop/coupons.py | matched: coupons.py:8 expired coupon ignored silently | matched: coupons.py:8 expired coupon ignored |
| add-coupons | money in integer cents (#3) | src/shop/coupons.py | missed | missed |
| add-refunds | refund logged with order id | src/shop/refunds.py | missed | missed |
| add-refunds | refund never exceeds paid | src/shop/refunds.py | matched: refunds.py:6 no check against paid | matched: refunds.py:6 amount not checked |
=== REVIEW.md (held out)
# Review rules

The owner's review rules.

## Rules

1. Never catch a bare `except:`; name the exception. — [#1](https://github.com/example/shop/pull/1#discussion_r101), [#2](https://github.com/example/shop/pull/2#discussion_r104)
2. Every function that opens a file uses `with`. — [#1 review](https://github.com/example/shop/pull/1), [#4](https://github.com/example/shop/pull/4#discussion_r108)
3. Every public function has a docstring.
4. A refund never exceeds the paid amount. - solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13 — [#2](https://github.com/example/shop/pull/2#discussion_r105), [#4](https://github.com/example/shop/pull/4#discussion_r109)

## Unconfirmed

- Split a function over 15 lines. — [#1](https://github.com/example/shop/pull/1#discussion_r102), [#2](https://github.com/example/shop/pull/2#discussion_r103), [#4](https://github.com/example/shop/pull/4#discussion_r110), [#4](https://github.com/example/shop/pull/4#discussion_r111)

