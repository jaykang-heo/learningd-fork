# Playbook: solution discovery

1. Establish the brute-force reading and why it fails at the stated constraints.
2. Find the representation change that removes the obstacle. Write down the
   obstacle first; it becomes the breakthrough scene's question.
3. Implement the primary solution in `solutions/primary.py` with an entrypoint
   and `cases.json`.
4. Write an independent oracle (different method, small inputs) and compare.
   Agreement between two implementations of the same idea proves nothing.
5. K4 runs the solution. Published outputs are the ones it produced here.

Alternatives are recorded when they change what the learner understands - a
different complexity class, a different invariant, a different failure mode -
not to pad a list.
