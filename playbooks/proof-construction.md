# Playbook: proof construction

1. State exactly what is being proven, including the edge case the naive reading
   gets wrong.
2. Build the argument as steps a learner could reproduce; each step names what it
   uses from the previous one.
3. Check the boundary the problem actually allows. When endpoints may coincide,
   a proof that assumes distinct endpoints is a proof of a different claim
   (spec 53.21).
4. A proof specialist other than the author reviews it and records
   `reviews/proof.json` with `status`, `reviewer` and findings.

K5 reads that verdict. There is no automatic pass: an unreviewed proof blocks
`knowledge_ready`.
