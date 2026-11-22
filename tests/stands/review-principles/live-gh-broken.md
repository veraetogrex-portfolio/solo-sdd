=== REVIEW.md
# Review rules

The owner's review rules, collected by `/review-principles` from the owner's PR remarks and the owner lines of archived changes. The `Review:` reviewer of `spec-next` gets the rules and not `## Unconfirmed`. The owner edits, adds or moves lines by hand: a rerun keeps every rule as it stands.

## Rules

1. In this project every money amount is kept in integer cents, never a float. — [coupons verification.md:12](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:12)
2. Every expired coupon is refused with an error, never ignored silently. — [coupons verification.md:13](solo-sdd/changes/archive/2026-11-10-add-coupons/verification.md:13)
3. Every refund is logged with its order id. — [refunds verification.md:12](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:12)
4. A refund never exceeds the paid amount, in this project. — [refunds verification.md:13](solo-sdd/changes/archive/2026-11-12-add-refunds/verification.md:13)

## Unconfirmed

Patterns the owner's remarks show but the owner never stated as a rule. Move a line up into `## Rules` to confirm it, delete it to reject it.

=== report
Owner login: shop-owner (AGENTS.md)
Read: archive verification.md (2 files: 2026-11-10-add-coupons, 2026-11-12-add-refunds): 4 remarks
Unread: PR review comments (answer is not JSON: cut), PR reviews (answer is not JSON: cut)
Skipped remarks: 0 by other authors, 2 not review remarks (agent `analyze:` lines in the archive)
Rules: 4 in REVIEW.md, 4 new; rules not kept: 0
Unconfirmed: 0 lines
The reviewer gets the rules above `## Unconfirmed`; move a line up to confirm it.

Notes (outside the requested blocks):
- The GitHub answers were cut off mid-JSON, so the PR sources were not read and the rules come only from the archive. The visible part of the review comments showed more owner remarks (bare `except:`, function length over 15 lines, docstrings on public functions), so a rerun with complete `gh` output is needed to get them.
- Process slip: my first `gh` call redirected stderr to `/tmp/x` (it failed because that path is a directory, so nothing was written), and I wrote a scratch file `c.json` inside the review temp folder (not in the project). I removed `c.json` right after. No other file was written or edited, and no change was started.
- `gh` is authenticated as `shop-agent`; I did not use `gh api user`.
