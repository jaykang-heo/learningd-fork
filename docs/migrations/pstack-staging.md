# Migration: retiring `vendor-staging/pstack/`

`vendor-staging/pstack/` holds the imported pstack history verbatim (spec 5.3
step 5). It is a staging path, not a second product, and it is removed once
everything this distro needs has moved into the native layout.

## Migrated so far

| pstack material | Landed as |
|---|---|
| `skills/principle-minimize-reader-load` | `principles/minimize-reader-load.md` |
| `skills/principle-prove-it-works` | `principles/prove-it-works.md` |
| `skills/principle-experience-first` | `principles/experience-first.md` |
| playbook-per-task structure (`skills/poteto-mode/playbooks/`) | `playbooks/` |
| specialist agent + blind review pattern (`skills/interrogate`, `skills/reflect`) | `agents/`, semantic gates in `engine/verification/acceptance.py` |

## Still to migrate

- `skills/why` investigation structure → a research playbook extension for
  decision-critical branch closure.
- `skills/technical-writing`, `skills/unslop` → document anti-padding guidance
  that today lives only as a numeric ceiling in `config/quality.yaml`.
- `scripts/watch-pr`, `scripts/orch` → evaluate against the Firstmate runtime
  before importing; duplicated orchestration is not migrated, it is dropped.

## Removal criterion

The staging path is deleted when no item above is outstanding and no file
outside `vendor-staging/` refers to it. Deleting it earlier would lose material
that has not been re-owned; keeping it after that point would leave two homes for
the same rules.
