# Playbook: production run

The default playbook for "teach me this problem". The Primary Orchestrator owns
this loop; workers own single tasks inside it.

## Phases and their exits

| Phase reached | Required gates | Produced by |
|---|---|---|
| `source_locked` | K1 | source researcher |
| `knowledge_ready` | K2, K3, K4, K5 | algorithm researcher, solver, proof specialist |
| `narrative_ready` | K6 | pedagogy director |
| `document_ready` | K7, K8, K9, K10 | visual director, document producer |
| `video_ready` | K11, K12, K13 | storyboard director, video director, narration writer, voice reviewer |
| `acceptance_ready` | K14, K15 | adversarial reviewer |
| `sealed` | K16 | orchestrator |
| `released` | seal verification | orchestrator |

A phase is never advanced by judgment:

```bash
scripts/distro.py gate    --run <id> --phase knowledge_ready
scripts/distro.py advance --run <id>
```

`advance` refuses and prints the blockers when any required receipt is missing,
failed, or stale for the current bytes.

## Interruption

After any crash or restart, start with:

```bash
scripts/distro.py reconcile --run <id>
```

It re-derives the phase, the blockers and the receipts that no longer match the
candidate. Resume at the first blocker; never redo confirmed phases.

## Repair

A failed gate is repaired at its root, not at its symptom: fix the fact, the
scene, the visual or the render, then rerun the gates whose inputs changed. A
deterministic gate is never retried unchanged - the same input gives the same
verdict (spec 18.1).
