# One fact, one owner

Any number, formula, constraint or example output that appears in more than one
place is a canonical fact in `facts.json`, referenced by id.

A number that can be computed owns a `generator` expression; the stored `value`
is a cache of that expression, and `distro gate --gate K2` recomputes it.

**Do not** write a number into prose, a caption, a narration beat or an SVG
label. Reference the fact id and let the renderer substitute it. Two hand-typed
copies of the same number are two truths, and one of them will be wrong.

Breaking this shows up as a document that says 1716 while the video says 1470.
