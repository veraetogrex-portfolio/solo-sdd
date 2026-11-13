# Extra spec-analyze checks for <project>

They run together with the common passes of the `spec-analyze` skill. Only checks that come from
defects of this project go here; the common rules are already in the skill.

## File ownership

Needed if the `tasks.md` sections run in parallel waves.

- Every section has the lists "Own files" and "Foreign files". A section without them is HIGH.
- One file or glob in the "Own files" of two sections is CRITICAL.
- A file a task must change that is only in "Foreign files" is a debt without an owner, HIGH.

## <Name of the defect class>

<What to check in the artifacts, at what level and why: which defect of the project this rule would have caught.>

## What a person sees

<Where the Live Scenario must reach in this project: the built panel, a screen, a service answer.
A scenario that ends in a unit test is HIGH.>
