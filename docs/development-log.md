# Development Log

## 2026-10-19 - Consolidate working tree on $PSCRATCH

Context:
- Two diverged working copies of this repo existed: the CFS checkout
  (`/global/cfs/cdirs/atlas/cxyang/playground/AnalysisBakery`, Harbor tasks,
  scripts, docs) and `/pscratch/sd/c/cxyang/AnalysisBakery` (verl, harbor
  mirror, benchmarks, and the 1LMET30 Open Data skim under `dataset/`).

Changes:
- Moved `AGENTS.md`, `dev_plan.md`, `docs/`, `scripts/`, `tasks/`,
  `histograms/`, `jobs/`, and `requirements-harbor-hpc.txt` to $PSCRATCH.
- Dropped the `external/harbor` submodule in favour of `harbor/` (GitLab
  mirror, branch `perlmutter`), which carries the same Podman-HPC patches
  rebased on newer upstream. Updated `external/harbor` paths accordingly.
- Re-added `external/TRExFitter` as a submodule at `28ead371`.
- Merged `.gitignore` (ignore `/dataset`, `jobs/`, `verl_data/`) and README.
- Repointed the `harbor` conda env editable install to `harbor/` and upgraded
  `litellm` to satisfy harbor 0.23.0.

Verification:
- `pip check` in the `harbor` env reports no broken requirements.
- `pytest tests/unit/environments/test_docker.py -q` in `harbor/`: 122 passed,
  1 skipped.

## 2026-07-02 - Harden TREXFitter Harbor tasks

Context:
- The first TREXFitter Harbor task suite was too easy because most tasks could
  be solved by path-localizing official configs and deleting unsupported logging
  syntax.
- More useful LLM-training tasks should require agents to understand and edit
  TRExFitter semantics, then validate the resulting run products.

Changes:
- Hardened `trexfitter-example-histo-localize` by requiring a two-sided `JES`
  systematic and a floating `Bkg2Floating` background normalisation.
- Hardened `trexfitter-ntuple-autobin-fit` by requiring a mixed
  observed-data/Asimov region setup and collecting the resulting realistic
  Asimov RooStats file.
- Hardened `trexfitter-morphing-width-fit` by requiring `SMOOTHLINEAR`
  interpolation, a shifted Asimov `topWidth`, and a shared `bkgScale` norm
  factor.
- Hardened `trexfitter-template-param-fit` by requiring a quadratic template
  parametrization with explicit parameter limits and start values.
- Hardened `trexfitter-unfolding-schema-repair` by requiring normalized
  cross-section unfolding in addition to the `NumberOfRecoBins` compatibility
  fix.

Verification:
- `bash -n` passed for all TREXFitter oracle and verifier shell scripts.
- `python3 -m py_compile` passed for all TREXFitter Python verifier helpers.
- Parsed all TREXFitter task TOML files with Python 3.11 `tomllib`.
- `harbor run -p <task> -a oracle` passed for all five hardened tasks, each
  with one trial, zero exceptions, and reward 1.0.

## 2026-07-02 - TREXFitter Harbor task suite

Context:
- The official TREXFitter example configs and inputs are available locally
  under `/pscratch/sd/c/cxyang/AnalysisBakery/eos`.
- A useful LLM training set should cover more than one path-localization
  pattern: histogram inputs, ntuple reading, morphing, template
  parameterization, and unfolding schema repair.

Changes:
- Added `tasks/trexfitter-ntuple-autobin-fit`, based on
  `FitExampleNtuple.config`, with verifier coverage for `trex-fitter n`, `b`,
  `w`, and `f`.
- Added `tasks/trexfitter-morphing-width-fit`, based on
  `FitExampleMorphing.config`, with verifier coverage for histogram
  production, workspace creation, fit output, and the `topWidth` error
  decomposition.
- Added `tasks/trexfitter-template-param-fit`, based on
  `FitExampleTemplate_1D.config`, with verifier coverage for the template
  parameterization step and `topMass` fit artifacts.
- Added `tasks/trexfitter-unfolding-schema-repair`, based on
  `FitExampleUnfolding.config`, requiring local input paths and the
  StatAnalysis-image-compatible `NumberOfRecoBins: 11` setting.
- Kept `tasks/trexfitter-example-histo-localize` as the simpler histogram
  localization task, giving five TREXFitter Harbor tasks total.

Verification:
- `bash -n` passed for all TREXFitter oracle and verifier shell scripts.
- `python3 -m py_compile` passed for all TREXFitter Python verifier helpers.
- Parsed all TREXFitter task TOML files and checked the expected Harbor schema
  sections.
- Probed the StatAnalysis image directly for the ntuple, morphing, template,
  and unfolding official examples before task creation.
- `harbor run -p tasks/trexfitter-ntuple-autobin-fit -a codex -m gpt-5.5 --ae CODEX_FORCE_AUTH_JSON=1`
  completed one trial with zero exceptions and reward 1.0. The verifier
  recorded exit code 0 for `trex-fitter n`, `b`, `w`, and `f`.

## 2026-07-02 - VERL and Harbor single-task prototype

Context:
- The first RL prototype should keep VERL responsible for policy rollouts and
  token accounting, while Harbor grades decoded task outputs through the
  existing `hyy-rl` verifier.
- Full terminal-agent RL requires exact policy token IDs and response masks, so
  it is a later integration phase rather than the initial prototype.

Changes:
- Added `scripts/build_verl_hyy_dataset.py`, which emits a one-row VERL-style
  dataset for `tasks/hyy-rl`.
- Added `scripts/verl_harbor_reward.py`, a VERL custom reward adapter that
  wraps a generated TRExFitter config as a temporary Harbor oracle solution and
  returns Harbor verifier rewards.
- Added `docs/verl-harbor-prototype.md` with the prototype workflow, smoke
  commands, and token/trace ownership notes.

Verification:
- `python3 -m py_compile scripts/verl_harbor_reward.py scripts/build_verl_hyy_dataset.py`
  passed under the default Python 3.6.15 environment.
- `python3 scripts/build_verl_hyy_dataset.py --output-dir /tmp/analysisbakery-verl-hyy-data --format jsonl`
  wrote the one-row train/test dataset.
- `python3 scripts/verl_harbor_reward.py tasks/hyy-rl/environment/hyy_config.config --extract-only`
  validated candidate extraction without launching Harbor.
- A live adapter call reached Harbor and failed closed to reward `0.0` because
  this shell's Podman-HPC runtime preflight failed before creating a container.
  The adapter now reports `harbor exited with status 1` and preserves the
  Harbor stderr tail for debugging.

## 2026-07-02 - TRExFitter Harbor example task

Context:
- The TRExFitter official example input files are mirrored locally under
  `/pscratch/sd/c/cxyang/AnalysisBakery/eos`.
- The existing `hyy-rl` task exercises custom model reconstruction, but a
  smaller task is useful for training agents on the mechanics of localizing
  official TRExFitter configs and running the StatAnalysis workflow.

Changes:
- Added `tasks/trexfitter-example-histo-localize`, a Harbor task based on the
  official `FitExample.config` histogram example.
- Mounted the official config read-only at `/app/FitExample.config` and the
  local EOS mirror read-only at `/trexinputs/eos`.
- Added an oracle solution that rewrites the `HistoPath` to the mounted local
  mirror and drops the image-incompatible `LoggingFormat` setting from the
  official checkout's newer config.
- Added verifier collection for `trex-fitter h`, `trex-fitter w`, and
  `trex-fitter f`, plus tests for the localized config, output logs, histogram
  cache, RooStats workspace, and fit artifacts.

Verification:
- Checked the mirrored input directory contains the expected Histo example ROOT
  files.
- `harbor run -p tasks/trexfitter-example-histo-localize -a oracle` passed
  with 1 trial, zero exceptions, and reward 1.0 after removing the
  image-incompatible `LoggingFormat` setting.

## 2026-07-01 - Podman short-image resolution

Context:
- `harbor run -d terminal-bench/terminal-bench-2 -l 5` failed on Podman-HPC
  because short Docker Hub image names such as `alexgshaw/overfull-hbox` were
  resolved through the host `registries.conf` search list before Docker Hub.

Changes:
- Qualified short prebuilt image names as `docker.io/...` when the configured
  container runtime is Podman-compatible.
- Preserved Docker behavior and already-qualified registry names.
- Added unit tests for Docker Hub namespace images and official library images.

Verification:
- `pytest tests/unit/environments/test_docker.py tests/unit/environments/test_docker_utils.py -q`
  passed with 112 tests passing and 1 skipped.
- `harbor run -d terminal-bench/terminal-bench-2 -l 5` completed with 5
  trials, zero exceptions, and mean reward 1.000.

## 2026-07-01 - Repository contributor guidance

Context:
- The root repository now has an `AGENTS.md` contributor guide.
- Development logs should belong to this parent repository, not the Harbor
  submodule, because they document workspace-level workflow decisions.

Changes:
- Added an explicit commit rule to `AGENTS.md`: update
  `docs/development-log.md` before every `git commit`.
- Moved the development log out of `external/harbor/docs/` and into the root
  `docs/` directory.

Verification:
- Confirmed the root `AGENTS.md` exists and the development log is present at
  `docs/development-log.md`.

## 2026-07-01 - Podman-HPC compatibility

Context:
- NERSC-style HPC hosts expose Python through environment modules and use
  `podman-hpc`/`podman-compose` instead of Docker.
- Harbor's local Docker environment previously assumed `docker compose`
  semantics throughout command construction, image helpers, and file transfer.

Changes:
- Added a small runtime configuration layer for container and compose commands.
- Kept Docker as the default runtime while allowing Podman/Podman Compose via
  `HARBOR_CONTAINER_CLI`, `HARBOR_COMPOSE_CLI`, and related environment
  variables.
- Added Podman Compose command construction without Docker Compose v2-only
  flags such as `--project-directory`.
- Added Podman-HPC setup scripts:
  - `scripts/harbor-podman-hpc-env.sh` is the user-facing environment setup.
  - `scripts/podman-hpc-podman-wrapper.sh` is needed only because
    `podman-compose --podman-path /usr/bin/podman-hpc` probes `--version`,
    which `podman-hpc` does not support.
- Used `podman-hpc cp` for Podman Compose file transfers instead of unsupported
  `podman-compose cp`, with tar-stream fallback retained.
- Added optional host-network and resource-limit overrides for constrained HPC
  runtimes where Podman bridge networks and cgroup controllers are unavailable.
- Updated Docker environment utility helpers to use the configured container
  runtime for platform detection, image inspection, manifest checks, and builds.

Review notes:
- Both new scripts are necessary: one provides reproducible user setup, and the
  other adapts `podman-compose` to the underlying HPC Podman storage/runtime
  options.
- Docker remains the default behavior; Podman-HPC behavior is opt-in through the
  setup script or equivalent environment variables.

Verification:
- `pytest tests/unit/environments/test_docker.py tests/unit/environments/test_docker_utils.py -q`
  passed with 110 tests passing and 1 skipped.
- A live Harbor run against `terminal-bench/terminal-bench-2` completed with
  one trial, zero exceptions, and reward 1.0 on Podman-HPC.
