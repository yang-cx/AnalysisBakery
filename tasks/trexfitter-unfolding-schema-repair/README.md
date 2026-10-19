# TRExFitter Unfolding Schema Repair

This task trains agents to adapt the official unfolding example to the pinned
StatAnalysis image. In addition to path localization, the agent must add
`NumberOfRecoBins: 11` to the unfolding region before running `u/h/w/f`.

Run the oracle locally with:

```bash
harbor run -p tasks/trexfitter-unfolding-schema-repair -a oracle
```
