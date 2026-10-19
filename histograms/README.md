# Histogram Caches

This directory stores shared histogram products used by Harbor tasks in this repository.

The binary ROOT files in this directory are intentionally not committed to Git. They are local derived artifacts built from the downloaded inputs under [`datasets/`](/Users/cxyang/Work/agent/harbor-atlas/datasets).

## Hyy Cache

For the current `hyy-rl` task, the expected local cache layout is:

- `hyy/Histograms/hyy_cat_2jet_histos.root`
- `hyy/Histograms/hyy_cat_central_lowptt_histos.root`
- `hyy/Histograms/hyy_cat_central_highptt_histos.root`
- `hyy/Histograms/hyy_cat_rest_lowptt_histos.root`
- `hyy/Histograms/hyy_cat_rest_highptt_histos.root`
- `hyy/Histograms/hyy_cat_transition_histos.root`

The accompanying binning text files under `hyy/Histograms/Binnings/` are lightweight metadata and can be kept in Git.

## Histogramming Config

The ntuple-based H→γγ TRExFitter config is:

- `hyy/ntuple_hyy_config.config`

It is configured for the repository dataset layout:

- host `datasets/GAMGAM_DATA/` is mounted into the container as `/datasets/GAMGAM_DATA/`
- host `datasets/GAMGAM_MC/` is mounted into the container as `/datasets/GAMGAM_MC/`
- the config uses `NtuplePaths: "/datasets/"`
- the data sample uses `NtuplePathSuff: "GAMGAM_DATA"`
- the MC samples use `NtuplePathSuff: "GAMGAM_MC"`

## Build Histograms

After initializing `datasets/`, run histogramming from the repository root:

```bash
./histograms/build_hyy_histograms.sh
```

The helper uses the ATLAS StatAnalysis image by default:

```bash
gitlab-registry.cern.ch/atlas/statanalysis:0-4
```

It runs:

```bash
trex-fitter n /workdir/hyy/ntuple_hyy_config.config
```

and writes outputs under:

```bash
histograms/hyy/Histograms/
```

The helper preflights every DATA file listed by `datasets/GAMGAM_DATA_urls.txt` plus the MC ROOT files used by `hyy/ntuple_hyy_config.config`. If you intentionally want to bypass that check:

```bash
SKIP_PREFLIGHT=1 ./histograms/build_hyy_histograms.sh
```

## Direct Docker Command

The helper is equivalent to this Docker workflow:

```bash
docker run --rm --platform linux/amd64 \
  -v "$PWD/datasets:/datasets:ro" \
  -v "$PWD/histograms:/workdir" \
  --workdir /workdir \
  --entrypoint bash \
  gitlab-registry.cern.ch/atlas/statanalysis:0-4 \
  -lc '
    set -e
    for gcc_setup in /opt/lcg/gcc/13.1.0*/x86_64-*/setup.sh; do
      if [ -f "$gcc_setup" ]; then
        . "$gcc_setup"
        break
      fi
    done
    SETUP=/usr/StatAnalysis/0.4.4/InstallArea/x86_64-el9-gcc13-opt/setup.sh
    if [ -f "$SETUP" ]; then
      . "$SETUP"
    fi
    trex-fitter n /workdir/hyy/ntuple_hyy_config.config
  '
```

Use `PLATFORM=linux/amd64` on Apple Silicon or other non-amd64 hosts. You can override the image with:

```bash
IMAGE=gitlab-registry.cern.ch/atlas/statanalysis:0-4 ./histograms/build_hyy_histograms.sh
```

## Workflow Position

The intended user workflow for this repository is:

1. initialize `datasets/`
2. generate the histogram cache locally with `./histograms/build_hyy_histograms.sh`
3. run Harbor tasks

For `hyy-rl`, the histogram step sits between raw-data download and task execution.

## Tracked Data Policy

The generated ROOT histogram files are intentionally ignored by Git.

Keep these in Git:

- `hyy/ntuple_hyy_config.config`
- `hyy/Histograms/Binnings/*.txt`
- helper scripts and README files

Do not commit:

- `hyy/Histograms/*.root`
- temporary TRExFitter outputs
