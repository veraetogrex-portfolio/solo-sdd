=== REVIEW.md
# Review rules

The owner's review rules, collected by `/review-principles` from the owner's PR remarks and the owner lines of archived changes. The `Review:` reviewer of `spec-next` gets the rules and not `## Unconfirmed`. The owner edits, adds or moves lines by hand: a rerun keeps every rule as it stands.

## Rules

1. Never catch a bare `except:`; always name the exception. — [PR #2 comment](https://github.com/example/shop/pull/2#discussion_r104), [PR #1 comment](https://github.com/example/shop/pull/1#discussion_r101)
2. Every public function has a docstring. — [PR #4 comment](https://github.com/example/shop/pull/4#discussion_r109), [PR #2 comment](https://github.com/example/shop/pull/2#discussion_r105)
3. Money is kept as integer cents, never a float. — [verification.md:12](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:12), [PR #3 comment](https://github.com/example/shop/pull/3#discussion_r107)
4. Every function that opens a file uses `with`. — [PR #4 comment](https://github.com/example/shop/pull/4#discussion_r108), [PR #1 review](https://github.com/example/shop/pull/1)
5. Every expired coupon is refused with an error, never ignored silently. — [verification.md:13](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:13)
6. Every refund is logged with its order id. — [verification.md:12](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:12)
7. A refund never exceeds the paid amount. — [verification.md:13](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13)

## Unconfirmed

Patterns the owner's remarks show but the owner never stated as a rule. Move a line up into `## Rules` to confirm it, delete it to reject it.

- Split a function longer than 15 lines. — [PR #1 comment](https://github.com/example/shop/pull/1#discussion_r102), [PR #2 comment](https://github.com/example/shop/pull/2#discussion_r103), [PR #4 comment](https://github.com/example/shop/pull/4#discussion_r110), [PR #4 comment](https://github.com/example/shop/pull/4#discussion_r111)

=== report
Owner login: shop-owner (AGENTS.md)
Read: PR review comments: 10 remarks, PR reviews: 1 remark, owner lines (solo-sdd/changes/archive/*/verification.md): 4 remarks
Unread: none
Skipped remarks: 4 by other authors (shop-agent x2, drive-by-dev, shop-agent review on PR #2), 2 not review remarks (PR #4 "Looks fine otherwise.", PR #5 approval with no text)
Rules: 7 in REVIEW.md, 7 new; rules not kept: 0
Unconfirmed: 1 line
The reviewer gets the rules above `## Unconfirmed`; move a line up to confirm it.

Note: one earlier shell command tried to write its stderr to /tmp/x. The write failed because that path is a directory, so nothing was created, and no other file was written. No REVIEW.md was written to disk, per the instructions.
