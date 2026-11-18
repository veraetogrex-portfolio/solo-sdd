# Proposal

## Why

Reproduction (review finding of 2026-11-18, read in code the same day):
1. `fit("กั"*5, 5)` in `solo_sdd/settings_ui.py` (Thai, five terminal columns).
2. Expected: all 10 characters fit.
3. Got: 5 characters, so a value in Thai or Indic script is cut or shown with "..." earlier than the width allows.

Cause: `solo_sdd/settings_ui.py:43`, `w = 2 if unicodedata.east_asian_width(c) in "WF" else 0 if unicodedata.combining(c) else 1`. `combining()` returns the canonical combining class, which is 0 for 1131 printable Mn and Me characters in the Unicode 17.0 data of Python 3.15 (1003 in the 13.0 data of Python 3.9): variation selectors U+FE00-FE0F and U+E0100-E01EF, U+034F, Thai U+0E31, Devanagari U+0941, Me U+20DD-20E0. Hangul medial jamo U+1160-11FF are also width 0. Cf characters never reach `fit`, as `shown()` escapes them.

## What Changes

- `fit` counts a character of category Mn or Me, and Hangul medial jamo U+1160-11FF, as zero columns, so lines are cut at the real width.
- U+FE0F keeps one column: it turns a narrow emoji such as U+2764 into a two-column one, so a zero width would let the line run one column past the screen.

## Capabilities

### New Capabilities

### Modified Capabilities
- `settings-ui`: MODIFIED requirement Safe display (a new scenario Zero-width marks).

## Impact

- `solo_sdd/settings_ui.py`
- `tests/test_settings_ui.py`

## Out of Scope

- A lone mark at the start of a reversed tail (`solo_sdd/settings_ui.py:706`, `:960`): a separate cosmetic case.
- Full grapheme clustering or a width library: no new dependency.
- An exact width for an emoji presentation sequence after a wide character (U+1F600 U+FE0F counts three columns): an over-count only cuts early, never breaks the layout.
- Neighbouring changes of this plan: `dispatch-skill-ci-and-return`, `fix-venv-exclude-line`, `fix-stop-gates-ignored-config`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create them" (on the list of new review findings after the 2026-11-18 dispatcher run, item: settings_ui `fit` counts some zero-width marks as one column)
