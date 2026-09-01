# Work Package Template

Copy this file, rename to `WP-###-<slug>.md`, fill every section. A package
must be self-contained: a fresh session should complete it with only
AGENTS.md + this file.

```markdown
# WP-###: <title>

status: open | in-progress | review | done
scope: <what this package covers, concretely>
priority: high | medium | low

## Objective
<One paragraph: what exists after this package is done.>

## Inputs (read these first)
- <exact files/rows/sections, with paths>

## Tasks
- [ ] <concrete task>

## Conventions that apply
- <pointers: CONTRIBUTION_STANDARDS sections, ADRs, markers>

## Acceptance criteria
- [ ] <objectively checkable criterion>

## Notes / findings
<Appended during work — decisions, surprises, follow-ups.>
```

Rules of thumb:

* **Size:** one package = one focused session. Split when in doubt.
* **Acceptance criteria** must be objectively checkable (validators, tests,
  verify_all.sh, explicit review gates) — not "make it good".
* **Status transitions** for content: `draft` -> `review` (curator done) ->
  `final` (human reviewer approved). Record who reviewed in the package.
* When a package is done: check it off in `docs/wp/INDEX.md` and update any
  ROADMAP checkbox it completes.
