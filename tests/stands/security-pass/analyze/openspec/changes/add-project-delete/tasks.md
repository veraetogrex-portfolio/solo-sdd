## 1. Endpoint

- [ ] 1.1 `DELETE /projects/{id}` in `app/routes/projects.py` by Delete a project; check: `tests/test_projects.py::test_delete` fails on the current code

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate add-project-delete --strict`, sync delta specs and archive the change with `openspec archive add-project-delete --yes`
