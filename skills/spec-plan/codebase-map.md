2a. **Codebase map.** No `docs/codebase/` (`test -d docs/codebase` fails): the map is not read, the report has `Map: none`. Otherwise each unit reads only the map files of its type row, never the whole map; a unit of several types reads the union of their rows, each file once; a type not in the table reads `ARCHITECTURE.md` only. A file already read for an earlier unit is not read again, but the report still names it for every change whose row has it.

   | Unit type | Map files in `docs/codebase/` |
   |---|---|
   | interface | CONVENTIONS, ARCHITECTURE |
   | API, backend | ARCHITECTURE, CONVENTIONS |
   | database, schemas | ARCHITECTURE, STACK |
   | tests | CONVENTIONS |
   | external integrations | STACK |
   | refactoring | CONCERNS, ARCHITECTURE |
   | configuration | STACK, ARCHITECTURE |
   | bugfix | ARCHITECTURE, CONCERNS |
   | other | ARCHITECTURE |

   Stale map: from the project root run once for the map files read (`<files read>` as paths, `docs/codebase/ARCHITECTURE.md …`): `for f in <files read>; do h=$(sed -n 's/^Commit: \([0-9a-fA-F]*\).*/\1/p;q' "$f"); if [ -n "$h" ] && git merge-base --is-ancestor "$h" HEAD 2>/dev/null; then n=$(git rev-list --count "$h..HEAD" -- . ':!docs' ':!solo-sdd'); if [ "$n" -gt 20 ]; then echo "Map stale: $f, $n commits since $h; refresh: /project-init map"; fi; else echo "Map stale: $f, unknown commits since ${h:-none}; refresh: /project-init map"; fi; done`.

   It counts the commits since the file's `Commit:` stamp that change files outside `docs/` and `solo-sdd/`; more than 20, a stamp commit that is not an ancestor of `HEAD` (rebased away, another branch, unknown) or no stamp prints the line. Every printed line goes into the report as is; planning goes on with the map, it is not refreshed here.
