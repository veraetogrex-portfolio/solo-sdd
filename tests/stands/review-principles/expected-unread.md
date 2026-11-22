=== REVIEW.md
# Review rules

## Rules

1. Every money amount is kept in integer cents, never a float. — solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:13
2. An expired coupon is refused with an error, never ignored silently. — solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:14
3. Every refund is logged with its order id. — solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13
4. A refund never exceeds the paid amount. — solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:14

## Unconfirmed

=== report
Owner login: shop-owner (AGENTS.md)
Read: owner lines: 4 remarks
Unread: PR comments and reviews (gh exit 1: error connecting to api.github.com)
Skipped remarks: 0 by other authors, 0 not review remarks
Rules: 4 in REVIEW.md, 4 new; rules not kept: 0
Unconfirmed: 0 lines
