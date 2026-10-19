# `lbl/hyy-rl`

This task asks the agent to complete a partially written TRExFitter configuration for an ATLAS H→γγ category model.

The input histograms are expected to be prepared locally and mounted into the container under `/histograms/hyy/Histograms/`. The task is not to derive histograms from ntuples during a run. Instead, the agent must finish the analysis-description layer in a writable working config at `/tmp/hyy_config.config`, starting from the read-only template mounted at `/app/template_hyy_config.config`, so the model can read the histogram cache, build a workspace, run a fit, and evaluate significance.

## What The Agent Must Do

The agent creates and edits only `/tmp/hyy_config.config`.

Conceptually, the missing work is:

- switch the job from ntuple-style input to histogram input
- reconstruct the full set of signal-category regions from the cache naming
- restore the expected sample list for this H→γγ model
- keep the norm-factor structure consistent with the regions and samples

The intended completed config should be able to run:

```bash
trex-fitter w /tmp/hyy_config.config
trex-fitter f /tmp/hyy_config.config
trex-fitter s /tmp/hyy_config.config
```

## Expected User Setup

From the perspective of a fresh user of this repository, the setup order for this task is:

1. install local prerequisites such as Docker and a dataset transfer tool
2. download the GAMGAM skim files into `datasets/`
3. prepare the local histogram cache under `histograms/hyy/Histograms/`
4. run `harbor run -p hyy-rl -a oracle`

This task assumes steps 1-3 are already complete.

## Histogram Cache Provenance

The task uses prebuilt histogram inputs. The agent is not expected to regenerate them during a run.

These histograms are produced with TRExFitter's ntuple-reading step, `trex-fitter n`, using the ntuple-based H→γγ config at:

- [../histograms/hyy/ntuple_hyy_config.config](/Users/cxyang/Work/agent/harbor-atlas/histograms/hyy/ntuple_hyy_config.config)

The downloaded Open Data samples are mounted under `/datasets` in the StatAnalysis container. The resulting cache is treated as a local prerequisite for this task rather than a committed repository asset.

The cache consumed by the task lives under:

- `/histograms/hyy/Histograms/` inside the container
- [histograms/hyy/Histograms](/Users/cxyang/Work/agent/harbor-atlas/histograms/hyy/Histograms) in the repository workspace

Representative files include:

- `hyy_cat_2jet_histos.root`
- `hyy_cat_central_lowptt_histos.root`
- `hyy_cat_central_highptt_histos.root`
- `hyy_cat_rest_lowptt_histos.root`
- `hyy_cat_rest_highptt_histos.root`
- `hyy_cat_transition_histos.root`

From the repository root, generate the cache with:

```bash
./histograms/build_hyy_histograms.sh
```

That helper wraps this StatAnalysis Docker workflow:

```bash
docker run --rm --platform linux/amd64 \
  -v "$PWD/datasets:/datasets:ro" \
  -v "$PWD/histograms:/workdir" \
  --workdir /workdir \
  --entrypoint bash \
  gitlab-registry.cern.ch/atlas/statanalysis:0-4 \
  -lc '
    . /opt/lcg/gcc/13.1.0-b3d18/x86_64-el9/setup.sh
    . /usr/StatAnalysis/0.4.4/InstallArea/x86_64-el9-gcc13-opt/setup.sh
    trex-fitter n /workdir/hyy/ntuple_hyy_config.config
  '
```

The task itself still starts from an already materialized local histogram cache; agents are not asked to regenerate histograms during a Harbor run.

## Environment

- Docker image: `gitlab-registry.cern.ch/atlas/statanalysis:0-4`
- Histogram cache mount: `/histograms/`
- Read-only starter template: `/app/template_hyy_config.config`
- Writable config produced by the agent: `/tmp/hyy_config.config`

The container already provides the TRExFitter runtime through the StatAnalysis environment used by the verifier.

## What The Verifier Runs

The verifier does more than static file checks.

After the agent finishes, the collect hook:

1. sources the required GCC and StatAnalysis setup scripts
2. creates writable output directories under `/tmp/hyy`
3. runs `trex-fitter w /tmp/hyy_config.config`
4. if workspace creation succeeds, runs `trex-fitter f /tmp/hyy_config.config`
5. if workspace creation succeeds, runs `trex-fitter s /tmp/hyy_config.config`
6. copies selected outputs into `/logs/artifacts`

## Collected Artifacts

The verifier collects these files from the TRExFitter run:

- `trexfitter_w.log`
- `trexfitter_f.log`
- `trexfitter_s.log`
- `trexfitter_w.exitcode`
- `trexfitter_f.exitcode`
- `trexfitter_s.exitcode`
- `trexfitter_outputs.txt`
- `significance_summary.txt`
- `hyy_config.config`
- `hyy_combined_hyy_model.root`
- `hyy_fit_results.root`
- `hyy_significance_workspace.root`
- `hyy_significance_parameter.root`

## What The Verifier Checks

The verifier checks both config content and runtime behavior.

Config-level checks:

- histogram-mode settings are present
- ntuple-only fields such as `NtuplePaths`, `NtupleFiles`, and `Selection` are absent
- the full region set is defined coherently
- the required samples are defined coherently
- norm factors match the reconstructed model

Runtime checks:

- `trex-fitter w` exits with code `0`
- `trex-fitter f` exits with code `0`
- `trex-fitter s` exits with code `0`
- the workspace ROOT file is produced and non-empty
- the fit results ROOT file is produced and non-empty
- the significance ROOT outputs are produced and non-empty
- the logs show successful config reading, histogram loading, workspace creation, fit completion, and significance extraction
- the run does not fail with missing input-file errors or HistFactory exceptions

## Expected Outcome

A successful solution produces a valid histogram-based TRExFitter config for the H→γγ category model and passes the verifier by completing workspace creation, fitting, and significance extraction inside the container.
