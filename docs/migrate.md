# Moving from OpenSpec

A project that keeps its process in `openspec/` moves with one command, history included:

1. `solo-sdd import openspec`: prints the plan (the counts of specs, open and archived changes, every file it would create) and writes nothing.
2. `solo-sdd import openspec . --write`: creates `solo-sdd/`. `specs/` and `changes/` with the archive are copied byte for byte without the `.openspec.yaml` files; `project.md` gets the `context` of `openspec/config.yaml` with the `Language:` and `Mode:` lines first; `openspec/analyze.md` becomes `solo-sdd/analyze.md`; a change whose `.openspec.yaml` has `skip_specs: true` gets `Specs: none` under `## Capabilities`; `CLAIM` and `WAITING` stay.
3. `solo-sdd validate --all`, then delete `openspec/` yourself: the import never touches it.

A repeat prints `nothing to import`. A non-empty `solo-sdd/` that differs from the plan (a changed, extra or missing file) is refused with exit code 1 and the first differing path, nothing written; so is a linked folder inside `openspec/` or a file that is not UTF-8 text where the import reads it. The `operations` of `config.yaml` and the `openspec` words inside the texts are not converted.
