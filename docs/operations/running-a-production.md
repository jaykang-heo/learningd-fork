# Operations: running a production

## Start

```bash
scripts/distro.py new --problem-key leetcode:1621 --request "<the user's words>"
```

An identical unfinished request resumes its run. Several unfinished matches are
refused - pick one explicitly, because merging two half-finished runs silently is
how a mixed bundle happens.

## Where is this run stuck?

```bash
scripts/distro.py status --run <id>
```

prints the phase and the exact blockers: missing receipt, failed gate, or a
receipt that is stale because named inputs changed.

## Did an invariant break?

```bash
scripts/distro.py gate --run <id>
```

runs all 16 gates and writes fresh receipts. Non-zero exit means at least one
failed; each line carries the reason.

## Did a paid external call actually happen?

`runs/<id>/events.jsonl` records provider calls, recovered assets and
`unknown_external_outcome` entries. The synthesis cache under
`runs/<id>/video/assets/` holds every take already paid for, keyed by provider,
model and normalized request.

## Recovery after a crash

```bash
scripts/distro.py reconcile --run <id>
```

Nothing is trusted from the previous process: the phase comes from `run.yaml`,
the evidence from receipts, the candidate from the bytes on disk.

## Release

```bash
scripts/distro.py seal --run <id> && scripts/distro.py release --run <id>
```

If `release` refuses, `dist/` is untouched and still holds the last good bundle.
