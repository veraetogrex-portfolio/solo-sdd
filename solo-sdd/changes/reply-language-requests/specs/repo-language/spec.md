## MODIFIED Requirements

### Requirement: Reply language check
The Stop hook SHALL check the language of the final reply only when the reply language (`reply.language` of `solo-sdd/config`, else `SOLO_SDD_REPLY_LANG`) is `ru` or `en`: `ru` rejects a reply with a Cyrillic share under 0.3, `en` rejects a reply with a Latin share under 0.7, both over at least 80 letters outside code, links, paths, `:::writing` blocks and lines starting with `>`. Unset or any other value SHALL mean no check.

#### Scenario: Not set
- **WHEN** `SOLO_SDD_REPLY_LANG` is unset and the reply is in English
- **THEN** the hook does not block the stop

#### Scenario: Owner wants Russian replies
- **WHEN** `SOLO_SDD_REPLY_LANG=ru` and the reply is in English
- **THEN** the hook asks to rewrite the reply in Russian, as before this change

#### Scenario: A draft in a writing block
- **WHEN** the reply language is `ru`, and the reply is two Russian lines and a 300-letter English draft between `:::writing` and `:::`
- **THEN** the hook does not block the stop

#### Scenario: Quoted English lines
- **WHEN** the reply language is `ru`, and the reply quotes 200 English letters in lines starting with `>` and comments them in two Russian lines
- **THEN** the hook does not block the stop

## ADDED Requirements

### Requirement: Requested translation passes
The Stop hook SHALL skip the reply language check when the last message the user wrote in the session holds, ignoring case, `translate`, `in English` or the Russian stem for "English" or for "translate". Tool results, hook messages and earlier user messages SHALL NOT count.

#### Scenario: Translation asked in Russian
- **WHEN** the reply language is `ru`, the last user message is the Russian "translate into English", and the reply is a 400-letter English text
- **THEN** the hook does not block the stop

#### Scenario: An earlier request does not count
- **WHEN** the reply language is `ru`, the translation was asked two user messages ago, the last user message is a Russian question, and the reply is in English
- **THEN** the hook asks to rewrite the reply in Russian

#### Scenario: A tool result is not the user
- **WHEN** the last user-role entry of the transcript is a tool result that holds the word `translate`, and the reply is in English under `ru`
- **THEN** the hook asks to rewrite the reply in Russian

### Requirement: Question window language
The `guard` hook SHALL check an `AskUserQuestion` call with the reply language check on its questions, option labels and option descriptions taken together; a mismatch SHALL deny the call with a line asking to rewrite the questions and options in that language. The reply language off, under 80 letters or an input it cannot read SHALL let the call through; an internal error is logged (fail-open).

#### Scenario: An English window for a Russian owner
- **WHEN** the reply language is `ru` and the window asks "Roll out the change to the agent folders now?" with the options "Yes, roll out" and "Not now" and English descriptions, over 80 letters in all
- **THEN** the call is denied and the reason asks to rewrite the questions and options in Russian

#### Scenario: A Russian window
- **WHEN** the reply language is `ru` and the questions and options are in Russian with a file path in backquotes
- **THEN** the call passes

#### Scenario: The check is off
- **WHEN** `reply.language` is `off` and `SOLO_SDD_REPLY_LANG` is unset
- **THEN** an English window passes

#### Scenario: A broken input
- **WHEN** the `questions` field of the call is a string, not a list
- **THEN** the call passes and no exception leaves the hook

### Requirement: Question guard registration
`solo-sdd install --hooks` SHALL put `AskUserQuestion` into the matcher of the `guard` entry of `PreToolUse` exactly once, keeping the tools already there; a repeated install SHALL change nothing.

#### Scenario: A repeated install
- **WHEN** `solo-sdd install --hooks` runs twice on settings without `AskUserQuestion` in the matcher
- **THEN** the `guard` matcher holds `AskUserQuestion` once and still holds `SubagentHandback` once
