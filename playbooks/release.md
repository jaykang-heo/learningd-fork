# Playbook: release

```bash
scripts/distro.py gate    --run <id>          # every gate, on current bytes
scripts/distro.py seal    --run <id>
scripts/distro.py release --run <id>
```

`seal` writes `seal/bundle-seal.json` only when all 16 gates hold a PASS receipt
whose recorded input hashes equal the candidate's. `release` re-verifies those
hashes, stages `dist.tmp/`, re-hashes the copies, and swaps the directory
atomically; a failure anywhere leaves the previous `dist/` intact.

The two files a user receives are `lesson.html` and `explainer.mp4`. Everything
else in the run directory is evidence.

Never edit a sealed artifact. Changed bytes start a new candidate cycle; the
released bundle stays as the immutable historical output (spec 15.2).
