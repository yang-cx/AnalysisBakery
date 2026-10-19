Create the localized TRExFitter config at `/tmp/FitExample.local.config`.

Start from the read-only official example config at `/app/FitExample.config`.
The example ROOT inputs have already been mirrored from EOS and are mounted at:

```text
/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Histo
```

This task is about making an EOS-backed TRExFitter example runnable in the
StatAnalysis container without network access to EOS, while also making a small
analysis-model change that exercises TRExFitter systematics and floating
background normalisations. A plain path-localized copy will not pass.

Requirements:
- Keep the job as `FitExample` with POI `SigXsecOverSM`.
- Keep the histogram-input workflow, regions, samples, signal norm factor, and
  existing systematics from the starter config.
- Use the local mounted histogram input path exactly:
  `/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Histo`.
- Do not leave any `root://eosuser.cern.ch` or `/eos/project/...` remote-style
  input reference in the final config.
- Remove the non-physics `LoggingFormat: NONE` setting if it is present; the
  StatAnalysis image used here rejects that setting.
- Convert the `JES` systematic to a real two-sided systematic by enabling the
  `_jesDown` down variation and using `Symmetrisation: TWOSIDED`.
- Add a floating background normalisation to sample `Bkg2`:
  `NormFactor: "Bkg2Floating",1,0.5,1.8`.
- Do not copy ROOT input files into `/tmp`; TRExFitter should read them from
  the mounted local mirror.

Only `/tmp/FitExample.local.config` is graded. You may validate your config with:

```bash
trex-fitter h /tmp/FitExample.local.config
trex-fitter w /tmp/FitExample.local.config
trex-fitter f /tmp/FitExample.local.config
```
