# Extra spec-analyze checks for tip

They run together with the common passes of the `spec-analyze` skill.

## What a person sees

The Live Scenario reaches what `python3 tip.py ...` prints in a terminal: each step names the command and what a person checks in its output (the stdout lines, the exit code or stderr, where they matter), quoting exactly any text it quotes. A step that only runs the unit tests may close the scenario, but it does not replace a step that runs `tip.py`.
