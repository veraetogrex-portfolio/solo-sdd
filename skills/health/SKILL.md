---
name: health
description: Use only when the user explicitly invokes /health - "check if it is alive", "check that it works", "recheck the env", "does the webhook work?", "is the bucket alive?", "does the database answer?", "why is there no new data".
disable-model-invocation: true
argument-hint: [component; all by default]
---

# health: are the project's integrations alive

Argument (optional): what to check. By default everything the project depends on. The diagnosis changes nothing. Fixing is done on the user's request or through `/debug-profile`.

## What to check

1. **Project description.** If the project has its own checks, run them: `docs/health.md`, a section about liveness checks in `AGENTS.md`, a `health` script in `package.json`, `Makefile` or `scripts/`.
2. **Otherwise find them yourself.**
   - Variable names in `.env`, names only, without values: `grep -o '^[A-Za-z_][A-Za-z0-9_]*=' .env`.
   - Services in `docker-compose*.yml`, configs, API clients in the code.
   - Match them with types: a database, HTTP APIs and webhooks, file storage, LLM and STT, spreadsheets and CRM, queues and schedulers.
3. **The cheapest check for each.**
   - Database: `SELECT 1` and the time of the last record in the main table.
   - HTTP API: a status or read endpoint.
   - Webhook: a read method: profile, list, app info.
   - Storage: a bucket check or a list of one object.
   - LLM and STT: the model list. Generation and recognition are paid: only with consent, with the number of requests and the amount.
   - Read only, write nothing.
4. **Local processes.** `docker compose ps`, occupied ports, the last errors in logs, stuck or unprocessed jobs.
5. **The provider is down.** Look at its status page: is there an incident.

## Secrets

Pass keys to a command through environment variables. Mask them in the output. Do not print values and do not put them into the report.

## Report (in the user's language)

| Component | Check | Result | Last success | What to do |
|---|---|---|---|---|

Below: what is broken and why, one or two sentences per item. If the project had no description of checks, suggest in the last line saving the found list to `docs/health.md`.
