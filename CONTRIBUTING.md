# Contributing

Bugs and ideas: open an [issue](https://github.com/veraetogrex-portfolio/solo-sdd/issues) with what you did, what you expected and what happened. For a change in behaviour, an issue first saves a pull request that goes the wrong way.

## A pull request

- Edit the sources in this repository (`skills/`, `global/`, `solo_sdd/`), never the copies in the agent folders: `python3 sync.py push` lays them out, `python3 sync.py pull <name>` brings an edit made in place back.
- A change in behaviour comes with a test that fails without it.
- All repository text is in English.
- One pull request, one change.

## Checks

```bash
python3 -m pip install --user hypothesis pyflakes==3.4.0
python3 tests/run.py --jobs 5 --tier slow < /dev/null
python3 -m pyflakes solo_sdd global scripts sync.py
python3 -m solo_sdd validate --all
```

The test tiers, the shared code blocks and the deployment from a clone: [docs/development.md](docs/development.md).
