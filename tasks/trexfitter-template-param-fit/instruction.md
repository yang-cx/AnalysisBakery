Create the localized TRExFitter config at `/tmp/FitExampleTemplate_1D.local.config`.

Start from the read-only official example config at `/app/FitExampleTemplate_1D.config`.
The template ROOT inputs are mounted at:

```text
/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Template
```

This task is about running a template-parametrized fit with a non-default
quadratic interpolation setup. Preserve the template morphing structure,
localize the input path, and remove syntax rejected by the pinned StatAnalysis
image. A plain path-localized copy will not pass.

Requirements:
- Keep the job as `FitExampleTemplate_1D` with POI `topMass`.
- Keep `Morphing: morphing`, the template sample definitions, the `topMass`
  template declarations, norm factor, and systematics intact.
- Use the local histogram path exactly:
  `/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Template`.
- Remove `LoggingFormat: NONE` if present.
- Change the morphing `FitFunction` from `LINEAR` to `QUADRATIC`.
- Add a `ParamLimits` entry for
  `Signal_1p0_172p5@SR_emu@0:0:-10:10`.
- Add a `ParamStartValue` entry for
  `Signal_1p0_172p5@SR_emu@0:0:1`.
- Do not replace the template step with a hand-written parametrization file.

Only `/tmp/FitExampleTemplate_1D.local.config` is graded. The verifier will run:

```bash
trex-fitter h /tmp/FitExampleTemplate_1D.local.config
trex-fitter t /tmp/FitExampleTemplate_1D.local.config
trex-fitter w /tmp/FitExampleTemplate_1D.local.config
trex-fitter f /tmp/FitExampleTemplate_1D.local.config
```
