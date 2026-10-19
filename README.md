# AnalysisBakery
Automate analysis with Claude Code


# Environement setup before running the analysis

module load python && mamba activate harbor

mamba env create 

mamba create -n harbor python=3.12

mamba activate harbor

pip3 install podman-compose

# Run the analysis
mamba activate harbor

package external/harbor requires podman-compose


For RL, think of a Harbor task as one rollout environment: an agent gets instruction.md, acts inside a container, then tests/test.sh computes a numeric
  reward. Harbor’s RL docs say RL needs rollouts plus recorded tokens and rewards, usually through TrialConfig/JobConfig and TaskConfig batches. Source:
  https://www.harborframework.com/docs/training-workflows/rl

  Harbor Task Shape
  A task directory should contain:

  tasks/<task-id>/
    instruction.md
    task.toml
    environment/
      Dockerfile          # or use [environment].docker_image
    solution/
      solve.sh            # oracle sanity check
    tests/
      test.sh             # writes reward

  Docs: https://www.harborframework.com/docs/tasks

  For RL, the critical file is tests/test.sh: it must write a reward to /logs/verifier/reward.txt or /logs/verifier/reward.json. Use reward.json when we
  want partial or multi-metric rewards, for example:

  { "reward": 0.7, "selection_accuracy": 1.0, "runtime_penalty": -0.3 }

  Harbor reads those reward files as the verifier result. Source: https://www.harborframework.com/docs/tasks

  Recommended First Step For This Repo
  Create a local Harbor task set under something like:

  tasks/
    histogram-selection/
    cut-optimization/
    config-repair/
    plot-reproduction/

  Each task should map to one RL episode. For example:

  - instruction.md: “Given this analysis config and sample data, produce a corrected selection that maximizes signal significance.”
  - environment: image with analysis dependencies, or a prebuilt image in task.toml.
  - solution/solve.sh: reference solution for oracle validation.
  - tests/test.sh: runs the analysis, computes score, writes /logs/verifier/reward.json.

  module load python
  mamba activate harbor
  source external/harbor/scripts/harbor-podman-hpc-env.sh

  Then scaffold a task:

  harbor init --task "berkeley/template"

  Run locally:

  harbor run -p tasks/histogram-selection -a oracle

  For RL training, group tasks into a dataset directory and use those task paths as TaskConfig(path="tasks/...") entries. Harbor docs describe datasets as
  collections of tasks used for evals/training: https://www.harborframework.com/docs/datasets

  Design Rule
  Start with deterministic verifiers and numeric rewards. Add rewardkit later if we need multi-criterion grading, LLM judges, or structured partial credit.
  Reward Kit writes Harbor-compatible reward.json: https://www.harborframework.com/docs/rewardkit
