"""The K1..K16 acceptance gates (spec 37).

Each gate is a pure function of a `Candidate`. Deterministic gates compute their
verdict here; semantic gates (proof, video semantics, perceptual voice,
reconstruction) read a reviewer verdict file, and refuse to pass when the
reviewer that was supposed to produce it is absent - an unavailable reviewer is
a blocked release, never an implied pass (spec 32.5, 36.1, 42.8).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.narrative import scene_graph as scene_graph_module
from engine.research import map as research_module
from engine.solutions.execute import run_python_solution
from engine.source import snapshot as snapshot_module
from engine.verification.context import Candidate
from engine.verification.cross_output import check as cross_output_check
from engine.verification.gates import Gate, GateRegistry, GateResult
from engine.video import storyboard as storyboard_module
from engine.video.media import ProbeUnavailable, probe
from engine.voice.audio_qa import AudioProbeUnavailable, check as audio_check, measure


def _problems(problems: list[str], **extra: Any) -> GateResult:
    if problems:
        return GateResult.failed(problems[0], problems=problems, **extra)
    return GateResult.ok(**extra)


# --- K1 ---------------------------------------------------------------------
def k1_source_integrity(c: Candidate) -> GateResult:
    try:
        snap = snapshot_module.verify(c.source_dir)
    except (FileNotFoundError, snapshot_module.SourceMutated) as exc:
        return GateResult.failed(str(exc))
    quotes = [
        q
        for scene in c.scene_graph.scenes
        for q in scene.get("source_quotes", [])
    ]
    unfaithful = snapshot_module.quotes_are_faithful(
        snap.raw_path.read_text(encoding="utf-8", errors="replace"), quotes
    )
    if unfaithful:
        return GateResult.failed(
            "quoted source text does not appear in the snapshot", quotes=unfaithful
        )
    return GateResult.ok(source_sha256=snap.sha256, quotes_checked=len(quotes))


# --- K2 ---------------------------------------------------------------------
def k2_fact_integrity(c: Candidate) -> GateResult:
    mismatched = c.facts.recompute()
    if mismatched:
        return GateResult.failed(
            "derived facts disagree with their generators", facts=mismatched
        )
    unreferenced_ids = set(c.facts.by_id) - scene_graph_module.fact_references(c.scene_graph)
    return GateResult.ok(
        facts=len(c.facts.facts), unused_facts=sorted(unreferenced_ids)
    )


# --- K3 ---------------------------------------------------------------------
def k3_research_closure(c: Candidate) -> GateResult:
    return _problems(research_module.validate(c.research), branches=len(c.research.branches))


# --- K4 ---------------------------------------------------------------------
def k4_solution_execution(c: Candidate) -> GateResult:
    if not c.solution_path.exists():
        return GateResult.failed("no primary solution to execute")
    report = run_python_solution(c.solution_path, c.cases_path)
    if not report.passed:
        return GateResult.failed(
            "primary solution did not reproduce its declared outputs",
            failures=report.failures() or [report.stderr],
        )
    return GateResult.ok(cases=len(report.cases))


# --- K5, K12, K13(perceptual), K15: reviewer-owned verdicts ------------------
def _semantic_gate(name: str, description: str):
    def check(c: Candidate) -> GateResult:
        verdict = c.review(name)
        if verdict is None:
            return GateResult.failed(
                f"{description}: no reviewer verdict recorded; the gate cannot pass "
                "without a reviewer"
            )
        if verdict.get("status") != "pass":
            return GateResult.failed(
                f"{description}: reviewer verdict is {verdict.get('status')!r}",
                findings=verdict.get("findings", []),
            )
        if not verdict.get("reviewer"):
            return GateResult.failed(f"{description}: verdict does not name its reviewer")
        return GateResult.ok(reviewer=verdict["reviewer"], notes=verdict.get("notes", ""))

    return check


# --- K6 ---------------------------------------------------------------------
def k6_scene_graph(c: Candidate) -> GateResult:
    return _problems(scene_graph_module.validate(c.scene_graph), scenes=len(c.scene_graph.scenes))


# --- K7 ---------------------------------------------------------------------
def k7_visual_coverage(c: Candidate) -> GateResult:
    policy = c.policy.section("visuals")
    graph = c.scene_graph
    document = c.document
    problems: list[str] = []

    covered = [s for s in graph.core_inference_scenes() if s.get("visuals")]
    total_core = len(graph.core_inference_scenes())
    coverage = (len(covered) / total_core) if total_core else 0.0
    if total_core == 0:
        problems.append("no core inference scenes are declared")
    elif coverage < float(policy["core_inference_visual_coverage"]):
        uncovered = [
            s["scene_id"] for s in graph.core_inference_scenes() if not s.get("visuals")
        ]
        problems.append(f"core inference scenes without a visual: {', '.join(uncovered)}")

    counts = {
        "substantive": len(document.substantive_visuals()),
        "dynamic": len(document.dynamic_visuals()),
        "recap": len(document.with_role("recap")),
        "contrast": len(document.with_role("contrast")),
        "proof": len(document.with_role("proof")),
    }
    floors = {
        "substantive": policy["minimum_substantive_visuals"],
        "dynamic": policy["minimum_dynamic_artifacts"],
        "recap": policy["minimum_recap_visuals"],
        "contrast": policy["minimum_contrast_visuals"],
        "proof": policy["minimum_proof_visuals"],
    }
    for name, floor in floors.items():
        if counts[name] < int(floor):
            problems.append(f"{name} visuals: {counts[name]} < floor {floor}")

    if c.policy.get("document", "require_static_fallback_for_dynamic"):
        missing = [v.scene_id for v in document.dynamic_visuals() if not v.has_static_fallback]
        if missing:
            problems.append(
                f"dynamic visuals without a static fallback in scenes: {', '.join(str(m) for m in missing)}"
            )
    return _problems(problems, counts=counts, core_inference_coverage=coverage)


# --- K8 ---------------------------------------------------------------------
def k8_document_content(c: Candidate) -> GateResult:
    policy = c.policy.section("document")
    document = c.document
    problems: list[str] = []
    if len(document.scenes) < int(policy["minimum_scene_sections"]):
        problems.append(
            f"document renders {len(document.scenes)} scene sections, "
            f"floor is {policy['minimum_scene_sections']}"
        )
    if document.text_chars < int(policy["minimum_text_chars"]):
        problems.append(f"document body is {document.text_chars} chars, floor is {policy['minimum_text_chars']}")
    if document.text_chars > int(policy["maximum_text_chars"]):
        problems.append(
            f"document body is {document.text_chars} chars, above the anti-padding ceiling "
            f"{policy['maximum_text_chars']}"
        )
    if not policy.get("allow_remote_scripts", False) and document.remote_script_sources():
        problems.append(
            "lesson.html loads remote scripts; it must be self-contained: "
            + ", ".join(document.remote_script_sources())
        )
    return _problems(problems, text_chars=document.text_chars, scenes=len(document.scenes))


# --- K9, K10: browser-owned verdicts ----------------------------------------
k9_browser = _semantic_gate("browser-qa", "browser matrix QA")
k10_interaction = _semantic_gate("interaction-qa", "interaction QA")


# --- K11 --------------------------------------------------------------------
def k11_video_technical(c: Candidate) -> GateResult:
    policy = c.policy.section("video")
    if not c.video_path.exists():
        return GateResult.failed("no rendered video")
    try:
        info = probe(c.video_path)
    except ProbeUnavailable as exc:
        return GateResult.failed(str(exc))
    problems: list[str] = []
    if info.width < int(policy["minimum_width"]) or info.height < int(policy["minimum_height"]):
        problems.append(f"resolution {info.width}x{info.height} is below the floor")
    if info.fps < float(policy["minimum_fps"]):
        problems.append(f"{info.fps:.2f} fps is below the floor {policy['minimum_fps']}")
    if policy.get("require_audio_stream", True) and not info.has_audio:
        problems.append("video has no audio stream")
    if info.duration_seconds < float(policy["minimum_duration_seconds"]):
        problems.append(f"duration {info.duration_seconds:.0f}s is below the floor")
    if info.duration_seconds > float(policy["maximum_duration_seconds"]):
        problems.append(f"duration {info.duration_seconds:.0f}s exceeds the ceiling")
    if policy.get("require_captions", True) and not c.captions_path.exists():
        problems.append("captions file is missing")
    board_problems = storyboard_module.validate(
        c.storyboard,
        c.scene_graph.scene_ids(),
        max_seconds_without_event=float(policy["maximum_seconds_without_visual_event"]),
    )
    problems.extend(board_problems)
    drift = abs(c.storyboard.total_duration() - info.duration_seconds)
    if drift > 2.0:
        problems.append(
            f"storyboard duration {c.storyboard.total_duration():.1f}s and rendered "
            f"{info.duration_seconds:.1f}s disagree"
        )
    return _problems(problems, duration_seconds=info.duration_seconds, fps=info.fps)


k12_video_semantic = _semantic_gate("video-semantic", "video semantic review")


# --- K13 --------------------------------------------------------------------
def k13_voice(c: Candidate) -> GateResult:
    policy = c.policy.section("audio")
    problems: list[str] = []
    if not c.video_path.exists():
        return GateResult.failed("no rendered video to measure audio from")
    try:
        stats = measure(c.video_path)
    except AudioProbeUnavailable as exc:
        return GateResult.failed(str(exc))
    problems.extend(
        audio_check(
            stats,
            max_peak_db=float(policy["maximum_true_peak_db"]),
            min_mean_db=float(policy["minimum_mean_db"]),
        )
    )
    narration = c.narration
    if policy.get("require_release_quality_provider", True):
        if not narration.get("provider", {}).get("release_quality"):
            problems.append(
                "narration was produced by a provider that is not release quality "
                "(Remaining Decision R1)"
            )
    if policy.get("require_perceptual_review", True):
        verdict = c.review("voice-perceptual")
        if verdict is None:
            problems.append(
                "no perceptual listening verdict; mechanical audio QA alone cannot "
                "pass the voice gate"
            )
        elif verdict.get("status") != "pass":
            problems.append(f"perceptual listening verdict is {verdict.get('status')!r}")
    return _problems(problems, peak_db=stats.peak_db, mean_db=stats.mean_db)


# --- K14 --------------------------------------------------------------------
def k14_cross_output(c: Candidate) -> GateResult:
    narration_scene_ids = [str(s.get("scene_id")) for s in c.narration.get("scenes", [])]
    return _problems(
        cross_output_check(c.scene_graph, c.document, c.storyboard, c.facts, narration_scene_ids)
    )


k15_reconstruction = _semantic_gate("reconstruction", "answer-hidden reconstruction review")


# --- K16 --------------------------------------------------------------------
def k16_bundle_seal(c: Candidate) -> GateResult:
    """Everything the seal binds must exist as real bytes before sealing."""
    missing = [
        str(p)
        for p in (c.lesson_path, c.video_path, c.scene_graph_path, c.facts_path)
        if not Path(p).exists()
    ]
    if missing:
        return GateResult.failed("bundle is incomplete", missing=missing)
    return GateResult.ok()


REGISTRY = GateRegistry(
    [
        Gate("K1", "source-integrity", "source_locked", ("source_sha256", "scene_graph_sha256"), k1_source_integrity),
        Gate("K2", "fact-integrity", "knowledge_ready", ("facts_sha256", "scene_graph_sha256"), k2_fact_integrity),
        Gate("K3", "research-closure", "knowledge_ready", ("research_sha256",), k3_research_closure),
        Gate("K4", "solution-execution", "knowledge_ready", ("solution_sha256",), k4_solution_execution),
        Gate("K5", "proof-review", "knowledge_ready", ("solution_sha256", "reviews_sha256"), _semantic_gate("proof", "proof review"), semantic=True),
        Gate("K6", "scene-graph-integrity", "narrative_ready", ("scene_graph_sha256",), k6_scene_graph),
        Gate("K7", "visual-coverage", "document_ready", ("scene_graph_sha256", "lesson_html_sha256", "quality_policy_sha256"), k7_visual_coverage),
        Gate("K8", "document-content", "document_ready", ("lesson_html_sha256", "quality_policy_sha256"), k8_document_content),
        Gate("K9", "browser-qa", "document_ready", ("lesson_html_sha256", "reviews_sha256"), k9_browser, semantic=True),
        Gate("K10", "interaction-qa", "document_ready", ("lesson_html_sha256", "reviews_sha256"), k10_interaction, semantic=True),
        Gate("K11", "video-technical", "video_ready", ("explainer_video_sha256", "storyboard_sha256", "captions_sha256", "quality_policy_sha256"), k11_video_technical),
        Gate("K12", "video-semantic", "video_ready", ("explainer_video_sha256", "reviews_sha256"), k12_video_semantic, semantic=True),
        Gate("K13", "voice", "video_ready", ("explainer_video_sha256", "narration_sha256", "reviews_sha256", "quality_policy_sha256"), k13_voice),
        Gate("K14", "cross-output", "acceptance_ready", ("lesson_html_sha256", "explainer_video_sha256", "scene_graph_sha256", "facts_sha256", "narration_sha256", "storyboard_sha256"), k14_cross_output),
        Gate("K15", "reconstruction", "acceptance_ready", ("lesson_html_sha256", "explainer_video_sha256", "reviews_sha256"), k15_reconstruction, semantic=True),
        Gate("K16", "bundle-seal", "sealed", ("lesson_html_sha256", "explainer_video_sha256", "scene_graph_sha256", "facts_sha256", "quality_policy_sha256"), k16_bundle_seal),
    ]
)

REQUIRED_GATE_NAMES = REGISTRY.names()
