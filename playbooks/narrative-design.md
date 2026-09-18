# Playbook: narrative design

Produce `narrative/master-scene-graph.json`, the single owner of order and
message for both outputs.

For each scene: the question it answers, its one primary message, the visual job,
whether the relation requires motion, its prerequisites, and the facts it cites.

Ordering rules K6 enforces: prerequisites point backwards, the breakthrough
precedes the solution, and at least one reconstruction scene exists.

Write the questions before the answers. A scene whose question is "what is a
segment tree" teaches a definition; one whose question is "why does the naive
scan redo work we already did" teaches the idea.
