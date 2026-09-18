# Playbook: source verification

Goal: the exact problem text every later claim quotes, captured once.

1. Fetch the official statement. Record origin and access method.
2. `engine.source.snapshot.capture()` writes `raw.*` plus `source.json`. It
   refuses to overwrite an existing snapshot - a second capture is a new run.
3. Build the problem key: official platform identity when it exists, otherwise
   `snapshot:<hash>`.
4. Register every constraint and official example as a canonical fact.
5. Quotes used anywhere must appear verbatim in the snapshot; K1 checks this.

If the official source is unreachable, the run blocks at `created`. Do not
substitute a remembered or third-party statement - the lesson would be about a
different problem than the one the learner opens.
