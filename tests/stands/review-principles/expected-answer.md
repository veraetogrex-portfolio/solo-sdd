=== REVIEW.md
# Review rules

The owner's review rules.

## Rules

1. Never catch a bare `except:`; name the exception. — [#1](https://github.com/example/shop/pull/1#discussion_r101), [#2](https://github.com/example/shop/pull/2#discussion_r104)
2. Every function that opens a file uses `with`. — [#1 review](https://github.com/example/shop/pull/1), [#4](https://github.com/example/shop/pull/4#discussion_r108)
3. Every public function has a docstring. — [#2](https://github.com/example/shop/pull/2#discussion_r105), [#4](https://github.com/example/shop/pull/4#discussion_r109)
4. Every money amount is kept in integer cents, never a float. — solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:13, [#3](https://github.com/example/shop/pull/3#discussion_r107)
5. An expired coupon is refused with an error, never ignored silently. — solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:14
6. Every refund is logged with its order id. — solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13
7. A refund never exceeds the paid amount. — solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:14

## Unconfirmed

- Split a function over 15 lines. — [#1](https://github.com/example/shop/pull/1#discussion_r102), [#2](https://github.com/example/shop/pull/2#discussion_r103), [#4](https://github.com/example/shop/pull/4#discussion_r110), [#4](https://github.com/example/shop/pull/4#discussion_r111)

=== report
Owner login: shop-owner (AGENTS.md)
Read: PR review comments: 9 remarks, PR reviews: 3 remarks, owner lines: 4 remarks
Unread: none
Skipped remarks: 3 by other authors, 1 not review remarks
Rules: 7 in REVIEW.md, 7 new; rules not kept: 0
Unconfirmed: 1 lines
