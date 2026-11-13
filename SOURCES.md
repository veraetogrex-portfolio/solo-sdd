# Sources

The third-party code and text the repository ships: pinned copies under `integrations/`, shipped as bundled integrations, each updated only by replacing the copy. Everything else in the repository is solo-sdd's own work.

## anti-slop

[anti-slop](https://github.com/miqdadbadjuber/anti-slop), release v3.2.24, commit 3005235, 29.10.2026, MIT license. The pinned copy lies in `integrations/antislop/`.

**Taken:** the core rules R-01…R-40 and the Delivery Gate, the dials of Part 3, the skills `antislop-ui`, `antislop-human`, `antislop-layoutmobile`, `contrast-check.py`, the After mode as an audit with numbered findings; the `antislop-copywriting` skill for `copy-check`: the "draft → audit → final" loop with two audit questions, the "do not flag" list, signs of human writing, calibration by the author's sample.

**Changed:** no setup wizard, no questions to the owner and no modes; R-02 only for English text; the placeholder `[data needed]` counts as `[REAL DATA]`; gate: the whole Hard Gate with proofs, the other blocks FAIL only; R-35 is FAIL if the interface was not run; the audit file is `docs/ui-audit-NNN-YYYY-MM-DD.md`. In texts: a language other than English is checked by a style skill for that language, if the agent has one, instead of the English patterns, R-15 for both languages, the owner's sample wins over R-02 without a question to the owner, the deviation goes into the report.

**Not taken:** the installer and plugins, `contrast-mcp.py`, `antislop-code`, the settings file `~/.config/antislop/settings.json`.

## security-audit-skill

[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill), commit c1c8a8c, 14.09.2026, MIT license. The pinned copy lies in `integrations/security-audit/`, its `VERSION` holds the commit and the hashes of the files.

**Taken:** the guidance mode for the security pass of `spec-audit`: a finding needs a crossed trust boundary, an affected principal or resource and an outcome; the severity anchors; the smallest fix at the last trusted decision point; target code only in a sandbox with every control, otherwise `needs validation` with a plan; no live probing. The attack class references and, on the user's request, the full audit mode with its validators.

**Changed:** deployed into `<root>/spec-audit/security/`, the upstream `SKILL.md` as `METHOD.md`, so that it is not loaded as a skill of its own; the severity maps onto the P0–P2 of `spec-audit`. The trust boundary check of `spec-analyze` is our own, before code.

**Not taken:** the validators' own tests (`validate-*.test.cjs`).
