=== REVIEW.md
# Review rules

The owner's review rules, collected by `/review-principles` from the owner's PR remarks and the owner lines of archived changes. The `Review:` reviewer of `spec-next` gets the rules and not `## Unconfirmed`. The owner edits, adds or moves lines by hand: a rerun keeps every rule as it stands.

## Rules

1. Never catch a bare `except:`; name the exception. - [#1](https://github.com/example/shop/pull/1#discussion_r101), [#2](https://github.com/example/shop/pull/2#discussion_r104)
2. Split every function longer than 15 lines into smaller ones. - [#1](https://github.com/example/shop/pull/1#discussion_r102), [#4](https://github.com/example/shop/pull/4#discussion_r110)
3. A refund never exceeds the paid amount, in this project. — [add-refunds 13](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13)
4. Every refund is logged with its order id. — [add-refunds 12](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:12)
5. Money amounts are integer cents, never floats, in this project. — [add-coupons 12](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:12), [#3](https://github.com/example/shop/pull/3#discussion_r107)
6. Every expired coupon is refused with an error, never ignored silently. — [add-coupons 13](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:13)
7. Every public function has a docstring. — [#4](https://github.com/example/shop/pull/4#discussion_r109), [#2](https://github.com/example/shop/pull/2#discussion_r105)
8. Every function that opens a file uses `with`. — [#4](https://github.com/example/shop/pull/4#discussion_r108), [#1 review](https://github.com/example/shop/pull/1)

## Unconfirmed

Patterns the owner's remarks show but the owner never stated as a rule. Move a line up into `## Rules` to confirm it, delete it to reject it.

=== report
Owner login: shop-owner (AGENTS.md)
Read: PR review comments: 10 remarks, PR reviews: 2 remarks, owner lines (archived verification.md): 4 remarks
Unread: none
Skipped remarks: 4 by other authors (3 review comments by shop-agent and drive-by-dev, 1 review by shop-agent), 1 not review remarks (owner approval on PR 5, no text)
Rules: 8 in REVIEW.md, 6 new; rules not kept: 0
Unconfirmed: 0 lines
The reviewer gets the rules above `## Unconfirmed`; move a line up to confirm it.

Note: the first command redirected stderr to `/tmp/x`, which is a directory, so the redirect failed and no file was written. I also read `<home>/Code/tools/sdd/solo-sdd/AGENTS.md`, outside the project folder, before the project's own AGENTS.md, because the session's start-up context named it. Its contents were not used for the owner login or the rules.
