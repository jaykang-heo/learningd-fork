"""Builders for a complete synthetic candidate.

The golden fixtures are deliberately mechanical: they exist to exercise gate
logic, not to donate prose or visuals to a real run (spec 52.5).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from engine.atomic import write_text
from engine.source import snapshot as snapshot_module

SOURCE_TEXT = (
    "Given an integer array nums and an integer k, return the number of ways to "
    "choose k disjoint segments. 1 <= nums.length <= 500."
)

TEST_POLICY = """schema_version: 1
visuals:
  minimum_substantive_visuals: 4
  minimum_dynamic_artifacts: 2
  minimum_recap_visuals: 1
  minimum_contrast_visuals: 1
  minimum_proof_visuals: 1
  maximum_core_viewports_without_meaningful_visual_event: 2
  core_inference_visual_coverage: 1.0
document:
  minimum_scene_sections: 3
  minimum_text_chars: 50
  maximum_text_chars: 190000
  require_static_fallback_for_dynamic: true
  allow_remote_scripts: false
video:
  minimum_width: 320
  minimum_height: 180
  minimum_fps: 24
  require_audio_stream: true
  minimum_duration_seconds: 1
  maximum_duration_seconds: 3600
  maximum_seconds_without_visual_event: 6.0
  require_captions: true
audio:
  maximum_true_peak_db: -1.0
  minimum_mean_db: -40.0
  require_release_quality_provider: false
  require_perceptual_review: true
"""

SCENES = [
    ("S01", "contract", False, False),
    ("S02", "breakthrough", True, True),
    ("S03", "solution", True, False),
    ("S04", "reconstruction", False, False),
]


def write_policy(path: Path) -> Path:
    return write_text(path, TEST_POLICY)


def scene_graph_payload() -> dict:
    scenes = []
    for index, (scene_id, phase, core_inference, dynamic) in enumerate(SCENES):
        visuals = []
        if core_inference or index == 0:
            visuals.append(
                {
                    "visual_id": f"{scene_id}-v1",
                    "kind": "dynamic" if dynamic else "static",
                    "roles": ["contrast"] if index == 0 else ["proof"],
                    "entities": ["endpoint:e1", "endpoint:e2"],
                }
            )
        scenes.append(
            {
                "scene_id": scene_id,
                "title": f"scene {scene_id}",
                "phase": phase,
                "core": True,
                "core_inference": core_inference,
                "goal": "goal",
                "primary_message": f"message for {scene_id}",
                "question": "why?",
                "visual_job": "show the relation",
                "requires_dynamic": dynamic,
                "visuals": visuals,
                "narration": [f"{scene_id} beat"],
                "conclusion": "so far so good",
                "transition_question": "and then?",
                "facts": ["formula.primary"] if index == 1 else [],
                "prerequisites": [SCENES[index - 1][0]] if index else [],
                "deep_dive_refs": [],
                "source_quotes": ["1 <= nums.length <= 500"] if index == 0 else [],
            }
        )
    return {"schema": 1, "kind": "master-scene-graph", "narrative_id": "fixture", "scenes": scenes}


def lesson_html(scene_ids: list[str]) -> str:
    body = []
    for index, scene_id in enumerate(scene_ids):
        visuals = [
            f'<figure data-visual="static" data-visual-role="recap">recap {scene_id}</figure>',
            f'<figure data-visual="dynamic" data-visual-role="contrast" data-static-fallback="true"'
            f' data-interactive="step,reset">contrast {scene_id}</figure>',
        ]
        if index == 1:
            visuals.append(
                '<figure data-visual="static" data-visual-role="proof">proof sketch</figure>'
            )
        body.append(
            f'<section data-scene="{scene_id}"><h2>{scene_id}</h2>'
            + "".join(visuals)
            + f'<p data-fact="formula.primary">본문 {scene_id} ' + ("설명 " * 20) + "</p></section>"
        )
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
        "<title>lesson</title></head><body>" + "".join(body) + "</body></html>"
    )


def build_candidate(run_root: Path, *, scene_ids: list[str] | None = None, with_media: bool = True) -> Path:
    """Materialize every canonical artifact of a passing candidate."""
    scene_ids = scene_ids or [s[0] for s in SCENES]
    for sub in ("source", "solutions", "narrative", "document", "video/assets", "reviews", "receipts", "seal", "dist"):
        (run_root / sub).mkdir(parents=True, exist_ok=True)

    if not (run_root / "source" / "source.json").exists():
        snapshot_module.capture(
            run_root / "source",
            raw=SOURCE_TEXT.encode("utf-8"),
            origin="https://example.test/problem",
            access_method="fixture",
            platform="fixture",
            identifier="1",
            extension="txt",
        )

    write_text(
        run_root / "facts.json",
        json.dumps(
            {
                "schema_version": 1,
                "facts": [
                    {
                        "id": "formula.primary",
                        "kind": "formula",
                        "value": "C(n+k-1, 2k)",
                        "provenance": ["proof.forward"],
                        "verification": ["oracle.small"],
                    },
                    {
                        "id": "example.comb.digits",
                        "kind": "derived_number",
                        "generator": "digits(comb(499500,500))",
                        "value": 1716,
                    },
                ],
            },
            indent=2,
        ),
    )
    write_text(
        run_root / "research.json",
        json.dumps(
            {
                "schema_version": 1,
                "branches": [
                    {
                        "id": "B1",
                        "question": "does the closed form hold for k=1?",
                        "decision_critical": True,
                        "status": "closed",
                        "evidence": ["oracle.small"],
                    }
                ],
            },
            indent=2,
        ),
    )
    write_text(
        run_root / "narrative" / "master-scene-graph.json",
        json.dumps(scene_graph_payload(), indent=2, ensure_ascii=False),
    )
    write_text(run_root / "document" / "lesson.html", lesson_html(scene_ids))
    write_text(
        run_root / "solutions" / "primary.py",
        "def ways(n: int, k: int) -> int:\n"
        "    from math import comb\n"
        "    return comb(n + k - 1, 2 * k)\n",
    )
    write_text(
        run_root / "solutions" / "cases.json",
        json.dumps(
            {
                "entrypoint": "ways",
                "cases": [
                    {"name": "small", "args": [4, 1], "expected": 6},
                    {"name": "larger", "args": [5, 1], "expected": 10},
                ],
            },
            indent=2,
        ),
    )
    write_text(
        run_root / "video" / "storyboard.json",
        json.dumps(
            {
                "schema_version": 1,
                "shots": [
                    {
                        "shot_id": f"{scene_id}-shot",
                        "scene_id": scene_id,
                        "duration_seconds": 2.0,
                        "visual_events": [
                            {"at_seconds": 0.5, "kind": "reveal"},
                            {"at_seconds": 1.5, "kind": "transform"},
                        ],
                    }
                    for scene_id in scene_ids
                ],
            },
            indent=2,
        ),
    )
    write_text(
        run_root / "video" / "narration.json",
        json.dumps(
            {
                "schema_version": 1,
                "provider": {"name": "fixture", "release_quality": False},
                "scenes": [
                    {
                        "scene_id": scene_id,
                        "intent": "discovery",
                        "pace": "conversational",
                        "beats": ["여기 하나가 걸립니다."],
                        "emphasis": ["등호"],
                        "pronunciation_refs": [],
                    }
                    for scene_id in scene_ids
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    write_text(run_root / "video" / "captions.vtt", "WEBVTT\n\n00:00.000 --> 00:02.000\n자막\n")
    for name in ("proof", "browser-qa", "interaction-qa", "video-semantic", "reconstruction", "voice-perceptual"):
        write_text(
            run_root / "reviews" / f"{name}.json",
            json.dumps({"status": "pass", "reviewer": "fixture-reviewer", "notes": "fixture"}, indent=2),
        )
    if with_media:
        render_placeholder_video(run_root / "video" / "explainer.mp4", seconds=len(scene_ids) * 2)
    return run_root


def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def render_placeholder_video(path: Path, *, seconds: int = 8, width: int = 640, height: int = 360) -> Path:
    """A real mp4 with a real audio stream, so media gates measure actual bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate=30:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-filter:a", "volume=-12dB",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path
