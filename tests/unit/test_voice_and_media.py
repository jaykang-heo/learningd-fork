import tempfile
import unittest
from pathlib import Path

from engine.voice.adapters import NullProvider, build
from engine.voice.provider import (
    SynthesisCache,
    SynthesisRequest,
    VoiceUnavailable,
    synthesize_scene,
)
from tests import fixtures


class VoiceBoundary(unittest.TestCase):
    def setUp(self):
        self.cache = SynthesisCache(Path(tempfile.mkdtemp()))
        self.provider = NullProvider()
        self.request = SynthesisRequest(scene_id="S01", text="여기 하나가 걸립니다.", voice_id="v", locale="ko-KR")

    def test_identical_request_is_never_paid_for_twice(self):
        _, called_first = synthesize_scene(self.provider, self.request, self.cache)
        _, called_again = synthesize_scene(self.provider, self.request, self.cache)
        self.assertTrue(called_first)
        self.assertFalse(called_again)
        self.assertEqual(len(self.provider.calls), 1)

    def test_changed_text_is_a_different_paid_request(self):
        synthesize_scene(self.provider, self.request, self.cache)
        changed = SynthesisRequest(scene_id="S01", text="다른 문장입니다.", voice_id="v", locale="ko-KR")
        synthesize_scene(self.provider, changed, self.cache)
        self.assertEqual(len(self.provider.calls), 2)

    def test_whitespace_only_change_reuses_the_cached_take(self):
        synthesize_scene(self.provider, self.request, self.cache)
        respaced = SynthesisRequest(scene_id="S01", text="여기  하나가\n걸립니다.", voice_id="v", locale="ko-KR")
        synthesize_scene(self.provider, respaced, self.cache)
        self.assertEqual(len(self.provider.calls), 1)

    def test_unconfigured_provider_is_an_explicit_block(self):
        with self.assertRaises(VoiceUnavailable):
            build("some-vendor-we-have-not-chosen")

    def test_development_adapters_are_not_release_quality(self):
        self.assertFalse(build("null").release_quality)
        self.assertFalse(build("local-say").release_quality)


@unittest.skipUnless(fixtures.ffmpeg_available(), "ffmpeg/ffprobe not installed")
class MediaProbe(unittest.TestCase):
    def test_probe_reads_the_real_file(self):
        from engine.video.media import probe

        path = fixtures.render_placeholder_video(Path(tempfile.mkdtemp()) / "v.mp4", seconds=2)
        info = probe(path)
        self.assertGreater(info.duration_seconds, 1.0)
        self.assertTrue(info.has_audio)
        self.assertEqual((info.width, info.height), (640, 360))

    def test_audio_measurement_detects_level(self):
        from engine.voice.audio_qa import measure

        path = fixtures.render_placeholder_video(Path(tempfile.mkdtemp()) / "v.mp4", seconds=2)
        stats = measure(path)
        self.assertGreater(stats.duration_seconds, 1.0)
        self.assertLess(stats.peak_db, 0.0)
