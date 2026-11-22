=== REVIEW.md
# Review rules

The owner's review rules, collected by `/review-principles` from the owner's PR remarks and the owner lines of archived changes. The `Review:` reviewer of `spec-next` gets the rules and not `## Unconfirmed`. The owner edits, adds or moves lines by hand: a rerun keeps every rule as it stands. A deleted rule comes back on a rerun while its remarks stand: reword it rather than delete it.

## Rules

1. A refund is logged with its order id, every time. — [verification.md](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:12)
2. A refund never exceeds the paid amount, in this project. — [verification.md](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13)
3. Every expired coupon is refused with an error, never ignored silently. — [verification.md](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:13)
4. In this project every money amount is kept in integer cents, never a float. — [verification.md](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:12)

## Unconfirmed

Patterns the owner's remarks show but the owner never stated as a rule. Move a line up into `## Rules` to confirm it. A rerun writes this section anew from the remarks, so a deleted line comes back while its remarks stand; it is never applied either way.

=== report
Owner login: none (AGENTS.md has no `Owner GitHub login:` line)
Read: solo-sdd/changes/archive/*/verification.md: 4 remarks
Unread: PR comments and reviews (no owner login in the project rules)
Skipped remarks: 0 by other authors, 2 not review remarks (the two `analyze:` agent decision lines)
Rules: 4 in REVIEW.md, 4 new; rules not kept: 0
Unconfirmed: 0 lines
The reviewer gets the rules above `## Unconfirmed`; move a line up to confirm it.

Notes: the REVIEW.md block above is text only; nothing was written to the project. The project has no REVIEW.md yet, so all four rules are new. Add `Owner GitHub login: <login>` to AGENTS.md and rerun to read the PR comments and reviews.
