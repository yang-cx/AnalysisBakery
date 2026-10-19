# TRExFitter Example Histo Localize

This Harbor task trains the smallest practical TRExFitter workflow:

- inspect an official example config,
- replace an EOS `root://` input path with a local mounted mirror,
- remove a version-incompatible non-physics config setting for the pinned
  StatAnalysis image,
- run the StatAnalysis-provided `trex-fitter` binary through `h`, `w`, and `f`,
- verify that the histogram cache, RooStats workspace, and fit result are real
  outputs rather than only syntactically valid config text.

The official example config is mounted read-only at `/app/FitExample.config`.
The mirrored input files are mounted read-only from:

```text
/pscratch/sd/c/cxyang/AnalysisBakery/eos
```

inside the task container as:

```text
/trexinputs/eos
```

Run the oracle locally with:

```bash
harbor run -p tasks/trexfitter-example-histo-localize -a oracle
```
