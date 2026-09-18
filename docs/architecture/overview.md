# Architecture overview

Three layers, one domain model.

## Runtime (`runtime/`)

Answers *who is working, on what, and from which state*.

- `orchestration/runstore.py` - `run.yaml`, the only durable owner of phase;
  run creation and duplicate-request semantics.
- `orchestration/phases.py` - the linear phase ladder; illegal jumps raise.
- `orchestration/integration.py` - worker results are checked against the
  dependency hashes they started from, and a late attempt can never overwrite a
  newer accepted one.
- `orchestration/orchestrator.py` - the single integration owner: runs gates,
  advances phases, seals, releases.
- `recovery/reconcile.py` - after an interruption, re-derives the resume point
  and lists receipts that no longer match the candidate.
- `tasks/graph.py` - dependency-ordered dispatch.

## Engine (`engine/`)

Answers *is this artifact actually correct*.

`source/` immutable snapshot and quote fidelity · `facts/` canonical facts with
safe generator evaluation · `research/` branch closure · `solutions/` real
execution against declared cases · `narrative/` scene graph invariants ·
`document/` structural inspection of `lesson.html` · `video/` ffprobe metadata
and storyboard cadence · `voice/` provider port, synthesis cache, mechanical
audio QA · `verification/` candidate hashes, receipts, the K1–K16 registry ·
`release/` seal and atomic publication.

## Contracts (`AGENTS.md`, `principles/`, `playbooks/`, `agents/`, `config/`)

Answers *what good means and who decides*. These are read by agents; the engine
enforces the parts that can be enforced by code.

## The load-bearing idea

Judgment decides what to build; code decides whether it may ship. A gate passes
only for the exact bytes it examined, so any later edit - to a fact, a scene, the
HTML or the video - invalidates the receipts that depended on it and the release
re-blocks automatically.
