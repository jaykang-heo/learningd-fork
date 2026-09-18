# learningd

A GitHub-native agent distro that turns one natural-language request about a
technical problem into two verified artifacts:

```text
lesson.html      a self-contained interactive monograph
explainer.mp4    a narrated cinematic explainer
```

Both render the same Master Scene Graph and the same canonical facts, and
neither is delivered until every acceptance gate passes on those exact bytes.

## Use it

Open an agent harness at this repository root and ask:

```text
LeetCode 1621을 깊게 가르쳐주는 문서와 영상을 만들어줘.
```

The root `AGENTS.md` routes the request. No skill install, no slash command.

## Drive a run by hand

```bash
scripts/distro.py new       --problem-key leetcode:1621 --request "..."
scripts/distro.py gate      --run <id> --phase document_ready
scripts/distro.py advance   --run <id>
scripts/distro.py seal      --run <id>
scripts/distro.py release   --run <id>
```

Requires Python 3.11+ (standard library only) and, for the media gates, `ffmpeg`
and `ffprobe` on PATH.

## Tests

```bash
python3 -m unittest discover -s tests -t . -v
```

The suite covers phase transitions, duplicate and stale worker results, derived
facts, scene-graph invariants, receipts and sealing, the voice cache, a full
`created → released` run, and the spec's negative regression cases.

## Layout

```text
AGENTS.md      product contract and orchestrator authority
config/        quality floors, providers, harnesses, product identity
principles/    why the rules exist
playbooks/     how each stage is executed
agents/        specialist worker contracts
engine/        deterministic toolchain (facts, scene graph, gates, seal)
runtime/       run state, task graph, integration, recovery
scripts/       the `distro` CLI
tests/         unit, integration and regression suites
runs/          per-run durable state (gitignored)
```

## Provenance

Base lineage: [Firstmate](https://github.com/kunchenguid/firstmate). Imported
history: the `pstack/` subtree of
[cursor/plugins](https://github.com/cursor/plugins), staged under
`vendor-staging/pstack/`. Exact commits live in `UPSTREAMS.yaml`; licenses in
`THIRD_PARTY_NOTICES.md`.

## Status

Implemented and tested: run state machine, duplicate/stale/late-result handling,
recovery reconciliation, canonical facts with generators, scene-graph
invariants, document and media inspection, the K1–K16 gate registry with
dependency-bound receipts, voice provider boundary with synthesis de-duplication,
bundle seal and atomic release.

Open decisions (spec §57): **R1** a release-quality voice provider (blocks a
natural-voice release), **R3** the final repository license, **R4** an optional
external visual media provider.
