# Playbook: document production

`lesson.html` is one self-contained file: no remote scripts, no external
stylesheet, no network at read time (K8, spec 45.4).

Render one `data-scene` section per scene, in graph order. Mark each substantive
visual with `data-visual` and its roles; give every dynamic artifact
`data-static-fallback="true"` plus reduced-motion, keyboard, reset and step
behaviour (K7, K10).

Facts are rendered through `data-fact="<id>"`, never typed in.

Structure: the Guided Visual Story carries the mainline; Deep Dive sections carry
the proofs, alternatives and edge cases that would break the reading rhythm.
Depth belongs in the Deep Dive, not in longer mainline paragraphs.
