# Playbook: voice production

1. Write `video/narration.json` as spoken Korean: short clauses, no symbols or
   Latin in the beats, formulas spoken as sentences (spec 31.3).
2. Synthesize per scene, never in one long take, so a fix is local and cheap.
3. `engine.voice.provider.synthesize_scene` de-duplicates by provider, model and
   normalized request. An identical scene is never paid for twice.
4. On an ambiguous provider outcome (timeout with a possible completion): query
   the request id, recover the asset if possible, otherwise record
   `unknown_external_outcome`. Never blind-retry a paid call (spec 18.5).
5. Mechanical QA measures level and clipping. A listening reviewer records
   `reviews/voice-perceptual.json`.

Until Remaining Decision R1 selects a release-quality provider, the shipped
policy makes K13 fail by design: development adapters can render audio, but they
cannot authorize a release.
