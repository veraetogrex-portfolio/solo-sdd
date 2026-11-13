# security-pass Specification

## Purpose
Adds security to the two quality gates of the process: a trust boundary check of the artifacts before code and a source-first security review of the code, both on a pinned copy of a published defensive audit method.

## Requirements

### Requirement: Pinned security references
`integrations/security-audit/` SHALL hold the upstream files of `cloudflare/security-audit-skill` at one recorded commit with its `LICENSE` and an `integration` description, without the validators' own test files. `targets.json` SHALL deploy them into `<root>/spec-audit/security/` of every agent root, the upstream `SKILL.md` as `METHOD.md`, and SHALL NOT deploy them as a skill: no file named `SKILL.md` under that folder. A test SHALL fail when a vendored file differs from the recorded hashes.

#### Scenario: Deployed copy
- **WHEN** `python3 sync.py push` runs on a clean temporary home
- **THEN** `~/.claude/skills/spec-audit/security/METHOD.md` exists, no `SKILL.md` lies under `~/.claude/skills/spec-audit/security/`, and `~/.claude/skills/security-audit/` does not

#### Scenario: A local edit of the copy
- **WHEN** one vendored reference file is edited by hand
- **THEN** `tests/test_vendor_security_audit.py` fails and names the file

### Requirement: Security pass in spec-audit
`spec-audit` SHALL run a security pass over the audited code by the vendored method in guidance mode: the trust boundaries the code crosses, and per finding the `file:line`, the affected principal or resource, the severity and the smallest fix. A candidate without a concrete affected principal, resource or outcome SHALL NOT be reported as a finding.

#### Scenario: A planted path traversal
- **WHEN** `spec-audit` runs on a stand whose file command joins a user path without a containment check
- **THEN** the report has a security finding with that `file:line`, the readable files outside the folder as the outcome, and a fix

#### Scenario: A clean stand
- **WHEN** the same stand has the containment check
- **THEN** no security finding of severity high or above

### Requirement: Security pass stays local and read-only
The security pass SHALL read source only and SHALL run target code only under the sandbox rules of the vendored method; without them it SHALL report the check as `needs validation`. It SHALL NOT probe deployed services or write report artifacts unless the user asks for a full security audit.

#### Scenario: No sandbox
- **WHEN** a finding needs running the target and no sandbox with the method's controls is available
- **THEN** the finding is reported as `needs validation` with a safe validation plan, and no target code runs

### Requirement: Trust boundary check in spec-analyze
`spec-analyze` SHALL report HIGH when a change adds a trust boundary (network input, authentication or authorization, secrets, a command or path built from user input, data of several users or tenants) and its spec has no requirement saying who may act and what is refused.

#### Scenario: An endpoint without an authorization rule
- **WHEN** a change adds `DELETE /projects/{id}` and its spec names no rule on who may delete
- **THEN** `spec-analyze` reports HIGH with the boundary and adds the missing requirement to the spec
