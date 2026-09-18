# Playbook: cinematic video

The video is not the document read aloud. It uses the same scenes, its own
visual timing, and a spoken script written separately.

1. `video/storyboard.json`: shots in scene-graph order, each with duration and
   the visual events it performs. A shot with no event is a slide.
2. Render with the lightest tool that does the job: HTML/SVG for layout and
   state, Manim for mathematical transforms, Remotion for composition, ffmpeg
   for the final mux. Render to a temp path and rename on success (spec 18.2).
3. Captions are produced from the narration artifact, not transcribed by ear.
4. K11 probes the rendered file with ffprobe and checks event cadence; K12 is a
   reviewer verdict on whether the video actually shows rather than narrates.

Long static stretches, full-paragraph screens and reading the slide are the
failure modes this playbook exists to prevent.
