# Upstream sync

`UPSTREAMS.yaml` is the only place that owns upstream repositories and imported
commits. Nothing else - README, scripts, release notes - keeps its own copy.

## Firstmate

```bash
git remote add upstream-firstmate https://github.com/kunchenguid/firstmate.git
git fetch upstream-firstmate main
```

Review the diff before taking anything. Upstream features that do not serve this
product's job are not imported merely because they exist (spec G10), and no
automatic merge runs.

## pstack

pstack history was imported once, filtered from `cursor/plugins`:

```bash
git clone https://github.com/cursor/plugins.git
git filter-repo --path pstack/ --path-rename pstack/:vendor-staging/pstack/
git merge --allow-unrelated-histories pstack-filtered/main
```

Re-import is a repeat of the same filter into a fresh branch, followed by a
reviewed merge - never a blind fast-forward.

## Firstmate's own contract

The supervisor contract that Firstmate ships at its repository root is preserved
here as `firstmate-supervisor-contract.md`. This repository's root `AGENTS.md` is
the product contract and takes precedence for anything running in this tree.
