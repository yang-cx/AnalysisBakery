Create the localized TRExFitter config at `/tmp/FitExampleMorphing.local.config`.

Start from the read-only official example config at `/app/FitExampleMorphing.config`.
The morphing ROOT inputs are mounted at:

```text
/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Morph
```

This task is about running a histogram-based morphing fit for the top-width
parameter, with a deliberate interpolation and background-normalisation change.
Preserve the morphing model and fit structure, but make the config use the
local input mirror and the syntax accepted by the pinned StatAnalysis image. A
plain path-localized copy will not pass.

Requirements:
- Keep the job as `FitExampleMorphing` with POI `topWidth`.
- Keep the morphing samples, ghost/reference samples, norm factors, and
  systematics intact.
- Use the local histogram path exactly:
  `/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Morph`.
- Remove `LoggingFormat: NONE` if present.
- Change `TemplateInterpolationOption` from `LINEAR` to `SMOOTHLINEAR`.
- Change the Asimov POI setting to `POIAsimov: topWidth@1.5`.
- Add a floating norm factor named `bkgScale` with nominal `1`, range
  `[0.5, 1.5]`, and `Samples: Bkg_SR,Bkg_CR`.
- Do not rewrite the task into a non-morphing fit.

Only `/tmp/FitExampleMorphing.local.config` is graded. The verifier will run:

```bash
trex-fitter h /tmp/FitExampleMorphing.local.config
trex-fitter w /tmp/FitExampleMorphing.local.config
trex-fitter f /tmp/FitExampleMorphing.local.config
```
