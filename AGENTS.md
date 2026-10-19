# Repository Guidelines

## Project Structure & Module Organization

This repository coordinates analysis assets and Harbor-based RL tasks. The root
`README.md` contains the current workflow notes. `scripts/` holds utility
scripts, including the CERN Open Data downloader. `dataset/` stores metadata and
download state; large downloaded ROOT files under `dataset/93929/` and
`dataset/93931/` are ignored by git. `tasks/` contains Harbor task definitions;
use `tasks/template/` as the starting layout for new tasks with
`instruction.md`, `task.toml`, `environment/`, `solution/`, and `tests/`.
External code lives under `external/`, notably the Harbor submodule.

## Build, Test, and Development Commands

Prepare the HPC Python environment before Harbor work:

```bash
module load python
mamba activate harbor
source harbor/scripts/harbor-podman-hpc-env.sh
```

Refresh CERN metadata without downloading payloads:

```bash
python3 scripts/download_cern_opendata.py --metadata-only
```

Download or resume data transfers:

```bash
python3 scripts/download_cern_opendata.py --use-cached-metadata --jobs 4
```

Run a Harbor task locally:

```bash
harbor run -p tasks/template -a oracle
```

For Harbor code changes, run focused tests inside `harbor`, for example:

```bash
pytest tests/unit/environments/test_docker.py tests/unit/environments/test_docker_utils.py -q
```

## Coding Style & Naming Conventions

Use clear, small Python modules with standard-library tools where practical.
Prefer explicit paths such as `dataset/records.yaml` and `tasks/<task-name>/`.
Name Harbor tasks with lowercase kebab-case, for example
`histogram-selection` or `plot-reproduction`. Keep shell snippets POSIX-like
unless they intentionally rely on Bash.

## Testing Guidelines

For data scripts, test metadata-only paths before large downloads. For Harbor
tasks, ensure `tests/test.sh` writes a numeric reward to
`/logs/verifier/reward.txt` or structured metrics to
`/logs/verifier/reward.json`. Keep oracle solutions in `solution/` so
`harbor run -a oracle` can validate task behavior.

## Commit & Pull Request Guidelines

Use concise imperative commit subjects, such as `Add Harbor task template` or
`Update CERN metadata downloader`. Before committing, check `git status` and
avoid staging generated datasets or unrelated submodule changes. Always update
`docs/development-log.md` with a concise summary, rationale, and verification
notes before running `git commit`. Pull requests should describe the workflow
change, list validation commands, and mention any HPC assumptions such as
Podman-HPC, modules, or required conda environments.
