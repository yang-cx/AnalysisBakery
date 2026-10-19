Create the localized TRExFitter config at `/tmp/FitExampleUnfolding.local.config`.

Start from the read-only official example config at `/app/FitExampleUnfolding.config`.
The unfolding ROOT input is mounted at:

```text
/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Unfolding
```

This task is about adapting an official unfolding example to the pinned
StatAnalysis image and changing it to a normalized cross-section unfolding. The
current image requires each unfolding region to specify the reconstructed-bin
count explicitly. Preserve the unfolding model, localize all input paths, remove
unsupported logging syntax, add the required region metadata, and enable the
normalized unfolding configuration. A plain path-localized copy will not pass.

Requirements:
- Keep the job as `FitExampleUnfolding` and keep `FitType: UNFOLDING`.
- Localize every unfolding input path to:
  `/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Unfolding`.
- Remove `LoggingFormat: NONE` if present.
- Add `NumberOfRecoBins: 11` to region `SR1`; the mounted input has 11 reco
  bins in the data and migration histograms.
- Add `PruningType: COMBINEDSIGNAL` in the `Job` block.
- Enable normalized cross-section unfolding with `UnfoldNormXSec: TRUE` and
  `UnfoldNormXSecBinN: 2` in the `Unfolding` block.
- Keep the unfolding truth-bin setup, truth samples, unfolding sample,
  background sample, and systematics intact.

Only `/tmp/FitExampleUnfolding.local.config` is graded. The verifier will run:

```bash
trex-fitter u /tmp/FitExampleUnfolding.local.config
trex-fitter h /tmp/FitExampleUnfolding.local.config
trex-fitter w /tmp/FitExampleUnfolding.local.config
trex-fitter f /tmp/FitExampleUnfolding.local.config
```
