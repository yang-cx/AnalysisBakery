Create the localized TRExFitter config at `/tmp/FitExampleNtuple.local.config`.

Start from the read-only official example config at `/app/FitExampleNtuple.config`.
The example ntuple ROOT inputs are mounted at:

```text
/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Ntuple
```

This task is about making the ntuple-based TRExFitter example runnable in the
pinned StatAnalysis image and then turning it into a mixed-data fit. Preserve
the analysis model, but rewrite the remote EOS input path to the local mirror,
remove syntax rejected by this image, and configure one observed-data region
and one Asimov region. A plain path-localized copy will not pass.

Requirements:
- Keep the job as `FitExampleNtuple` with POI `mu_XS_ttH`.
- Keep `ReadFrom: NTUP`, the `nominal_Loose` tree name, the two regions, the
  sample definitions, the auto-binning setup, norm factors, and systematics.
- Use the local ntuple path exactly:
  `/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Ntuple`.
- Remove `LoggingFormat: NONE` if present.
- Set `FitBlind: FALSE` in the `Fit` block.
- Configure region `ljets_5j3b_HT` with `DataType: DATA`.
- Configure region `ljets_6j4b_BDT` with `DataType: ASIMOV`.
- Do not replace the ntuple workflow with a prebuilt histogram workflow.
- Do not copy ROOT input files into `/tmp`.

Only `/tmp/FitExampleNtuple.local.config` is graded. The verifier will run:

```bash
trex-fitter n /tmp/FitExampleNtuple.local.config
trex-fitter b /tmp/FitExampleNtuple.local.config
trex-fitter w /tmp/FitExampleNtuple.local.config
trex-fitter f /tmp/FitExampleNtuple.local.config
```
