=== REVIEW.md
# Review rules

The owner's review rules, collected by `/review-principles` from the owner's PR remarks and the owner lines of archived changes. The `Review:` reviewer of `spec-next` gets the rules and not `## Unconfirmed`. The owner edits, adds or moves lines by hand: a rerun keeps every rule as it stands.

## Rules

1. Every money amount is kept in integer cents, never as a float. — [add-coupons](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:12)
2. Every expired coupon is refused with an error, never ignored silently. — [add-coupons](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:13)
3. Every refund is logged with its order id. — [add-refunds](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:12)
4. A refund never exceeds the paid amount. — [add-refunds](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13)

## Unconfirmed

Patterns the owner's remarks show but the owner never stated as a rule. Move a line up into `## Rules` to confirm it, delete it to reject it.

=== report
Owner login: shop-owner (AGENTS.md)
Read: owner lines of archived verification.md (add-coupons): 2 remarks, owner lines of archived verification.md (add-refunds): 2 remarks
Unread: PR review comments (no GitHub remote), PR reviews (no GitHub remote)
Skipped remarks: 0 by other authors, 2 not review remarks
Rules: 4 in REVIEW.md, 4 new; rules not kept: 0
Unconfirmed: 0 lines
The reviewer gets the rules above `## Unconfirmed`; move a line up to confirm it.
