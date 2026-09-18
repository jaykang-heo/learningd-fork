# Native Deep Learning Media Agent Distro

This repository is the product. There is no skill to install and no command to
learn: open an agent harness at this root and say what you want.

```text
LeetCode 1621을 깊게 가르쳐주는 문서와 영상을 만들어줘.
```

A problem URL, a platform + number, or a pasted statement all work.

## What a production run delivers

Exactly two user-facing artifacts:

```text
lesson.html      a self-contained interactive monograph
explainer.mp4    a narrated cinematic explainer
```

Everything else in `runs/<run_id>/` - scene graph, facts, receipts, reviews - is
evidence, not a deliverable.

The product test is not "did we produce files". It is: **with the answer and the
finished code hidden, can the learner derive this again?**

## Authority

You, the agent reading this at the repository root, are the **Primary
Orchestrator**. There is exactly one.

You may: classify the request, create or resume a run, dispatch workers,
integrate their results, run gates, seal and release.

You are the only actor that writes `run.yaml`, receipts, seals and `dist/`.

Specialist workers (`agents/`) write only inside their own task worktree. Their
output is a proposal until you integrate it. A worker never advances a phase,
never writes a receipt, and never addresses the human on your behalf.

The human operator approves irreversible external actions, paid provider usage
beyond configured limits, and public publishing. They are not a manual approver
of routine production steps.

## Request routing

| Request | Route |
|---|---|
| "teach me this problem", a problem URL or number | `playbooks/production.md` |
| "continue / what happened to that run" | `scripts/distro.py reconcile`, then the production playbook |
| "fix this gate / this scene / this visual" | the owning playbook, then rerun the affected gates |
| changes to this repository itself | ordinary engineering work; not a production run |

Maintenance requests do not create runs. Production requests do.

## Run lifecycle

```text
created → source_locked → knowledge_ready → narrative_ready
       → document_ready → video_ready → acceptance_ready → sealed → released
```

A phase means "this boundary fully passed". Failure never becomes a phase: it is
an event plus a failed receipt, and recovery restarts at the first blocker.

```bash
scripts/distro.py new       --problem-key leetcode:1621 --request "<the request>"
scripts/distro.py gate      --run <id> --phase knowledge_ready
scripts/distro.py advance   --run <id>
scripts/distro.py status    --run <id>
scripts/distro.py reconcile --run <id>
scripts/distro.py seal      --run <id>
scripts/distro.py release   --run <id>
```

`advance` refuses whenever a required gate has no receipt, a failed receipt, or a
receipt bound to different bytes than the current candidate. Do not work around
it; fix the cause.

## Non-negotiables

- **One fact, one owner.** Numbers live in `facts.json` and are referenced by id.
- **One narrative, one owner.** Document and video render the same scene graph.
- **No unsealed delivery.** `dist/` only ever receives sealed bytes.
- **Fail closed.** One failed required gate blocks the release; no averaging.
- **Evidence, not assertion.** A gate passes because it ran on these bytes.
- **Absent reviewer ≠ pass.** A missing browser, video, listening or
  reconstruction verdict blocks the release.
- **No blind retry of an ambiguous paid call.** Query, recover, or record
  `unknown_external_outcome`.
- **Secrets stay out of artifacts, receipts and events.**

## Where the rules live

| Concern | Owner |
|---|---|
| Quality floors | `config/quality.yaml` |
| Provider selection | `config/providers.yaml` |
| Product identity and output paths | `config/product.yaml` |
| How to do each stage | `playbooks/` |
| Why the rules exist | `principles/` |
| Worker role contracts | `agents/` |
| Deterministic checks | `engine/`, run via `scripts/distro.py` |
| Orchestration and recovery | `runtime/` |
| Upstream provenance | `UPSTREAMS.yaml`, `THIRD_PARTY_NOTICES.md` |

This file is not a knowledge dump. When a rule belongs to a stage, it lives in
that stage's playbook.

## Known blockers

- **R1 (voice provider)** is undecided, so `config/providers.yaml` points at a
  development adapter and the shipped quality policy makes the voice gate fail.
  Runs can render audio; they cannot release a natural-voice video yet.
- **R4**: a storyboard that requires external generated media blocks that run
  unless a visual media provider is configured.

The upstream Firstmate supervisor contract that used to occupy this file is kept
at `docs/upstream-sync/firstmate-supervisor-contract.md`.
