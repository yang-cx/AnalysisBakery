# VERL Harbor Prototype

This prototype trains on one Harbor task, `tasks/hyy-rl`, with a strict split:

- VERL generates the model rollout and owns token IDs, response IDs, logprobs,
  and response masks.
- Harbor receives the decoded candidate config, runs the task verifier, and
  returns a scalar reward.

The first prototype is single-shot config generation, not full terminal-agent
training. That keeps token accounting correct because VERL's own rollout backend
produces the trajectory.

## Build the one-row dataset

For adapter smoke tests without VERL dependencies:

```bash
python3 scripts/build_verl_hyy_dataset.py --format jsonl
```

For a VERL run, create parquet in the VERL environment:

```bash
python3 scripts/build_verl_hyy_dataset.py --format parquet
```

Each row uses the standard VERL fields: `data_source`, chat-template `prompt`,
`ability`, `reward_model.ground_truth`, and `extra_info`.

## Reward adapter

Use `scripts/verl_harbor_reward.py` as VERL's custom reward function:

```text
reward.custom_reward_function.path=scripts/verl_harbor_reward.py
reward.custom_reward_function.name=compute_score
```

`compute_score` accepts VERL's decoded `solution_str`, extracts a generated
TRExFitter config, wraps it as a temporary Harbor oracle solution, runs:

```bash
harbor run -p <temporary-hyy-task> -a oracle
```

and returns Harbor's `verifier_result.rewards["reward"]`.

The adapter fails closed to `0.0` on Harbor, container, timeout, or reward parse
errors. It writes Harbor jobs under `/tmp/analysisbakery-verl-harbor-jobs` by
default. Override that through `extra_info.jobs_dir`.

## Local smoke checks

Check response extraction without launching Harbor:

```bash
python3 scripts/verl_harbor_reward.py \
  tasks/hyy-rl/environment/hyy_config.config \
  --extract-only
```

Grade a generated config through Harbor:

```bash
module load python
mamba activate harbor
source harbor/scripts/harbor-podman-hpc-env.sh
python3 scripts/verl_harbor_reward.py path/to/generated_hyy_config.config
```

The command prints JSON containing the scalar reward, all Harbor reward keys,
and the Harbor job/trial directories for debugging.

On NERSC-style hosts, Harbor must pass its container-runtime preflight before
the reward adapter can launch a verifier. If the adapter returns `0.0` with
`Container runtime preflight failed`, fix the Podman-HPC runtime state first;
the adapter intentionally treats that as a failed rollout instead of crashing
the VERL trainer.

## Token and trace handling

Do not train VERL from ordinary `harbor run -a codex` traces for this
prototype. Those logs are useful for debugging, but they do not guarantee exact
policy token IDs and masks.

For this prototype:

1. VERL samples the `hyy-rl` prompt.
2. VERL generates the config with its rollout backend.
3. VERL keeps `prompt_ids`, `response_ids`, logprobs, and `response_mask`.
4. The reward adapter grades the decoded response with Harbor.
5. VERL attaches the Harbor reward to the trajectory it already recorded.

Full terminal-agent RL is a later phase. That requires either a VERL
`AgentLoopBase` implementation that calls Harbor/container tools while using
VERL's `LLMServerClient.generate()`, or a Harbor agent that returns exact
`token_ids` and `mask_ids` in `agent_result.metadata`.
