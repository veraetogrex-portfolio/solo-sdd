## 1. Fix

- [ ] 1.1 `get_order` returns the stored order; check — `python3 -m unittest -v test_handlers.Handlers.test_get_order` passes

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate fix-second-handler --strict`, sync delta specs and archive the change with `openspec archive fix-second-handler --yes`
