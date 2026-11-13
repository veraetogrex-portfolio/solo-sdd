# ui-gate-stand

Stand for the live scenario `ui-check-gate` (`openspec/changes/ui-check-gate/verification.md`): a landing page with planted violations. Planted: `#pricing` without a section, `#999999` on `#FFFFFF`, "10K+ users", a clickable div, a form without `<label>`, the button "Get Started", a reviews placeholder, "Fast — and simple" and a Russian sentence with an em dash that the owner gives at run time. Everything else is clean. The expected verdict is `EXPECTED.md`.

## Preparation

```
cd /path/to/solo-sdd
cp -r tests/stands/ui-gate-stand /tmp/ui-gate-stand
cd /tmp/ui-gate-stand
mkdir /tmp/ui-gate-aux
mv EXPECTED.md DESIGN-step3.md stand-form.patch stand-form /tmp/ui-gate-aux/
git init
git add -A
git commit -m base
openspec init --tools claude,codex
python3 -m http.server 8765
```

`EXPECTED.md`, `DESIGN-step3.md`, `stand-form.patch` and the folder `stand-form/` (artifacts of a ready change for step 6; in the repository they lie outside `openspec/`, because `openspec/` is ignored by git) are not part of the working copy: keep them in `/tmp/ui-gate-aux/`. Before `git add`, replace the line `<!-- owner-ru -->` in `index.html` with `<p>` holding the owner's Russian sentence with an em dash (the repository holds no Russian text). Start the server as a separate background task.

## Step 3

```
cp -r /tmp/ui-gate-stand /tmp/ui-gate-stand-3
cd /tmp/ui-gate-stand-3
cp /tmp/ui-gate-aux/DESIGN-step3.md DESIGN.md
```

The `tests/` folder with `keep.txt` is already in the stand; its integrity is checked after `/ui-check`.

## Step 6

```
cp -r /tmp/ui-gate-stand /tmp/ui-gate-stand-6
cd /tmp/ui-gate-stand-6
cp -r /tmp/ui-gate-aux/stand-form openspec/changes/stand-form
git apply /tmp/ui-gate-aux/stand-form.patch
git add -A
git commit -m "stand-form"
```

## Step 7

Do not start the server or connect a browser; run `/ui-check` in the copy `/tmp/ui-gate-stand`.
