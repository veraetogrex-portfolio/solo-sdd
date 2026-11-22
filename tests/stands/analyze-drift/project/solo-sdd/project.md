# Project

Language: en
Mode: demo

Intent: `backup` keeps a copy of a file in the `backups/` folder next to it. Success means a person runs
`python3 backup.py <file>` and either has the copy or a clear message that there is none.

## Apply rules

- Readiness is proven by running `backup.py` on real input, not by green unit tests alone
- Only the Python standard library
