#!/usr/bin/env python3
"""VERL custom reward adapter backed by the Harbor hyy-rl task.

VERL owns rollout generation and therefore keeps the policy token IDs, masks,
and logprobs. This adapter only grades the decoded model response by wrapping it
as a temporary Harbor oracle solution and reading Harbor's verifier reward.
"""

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK_PATH = REPO_ROOT / "tasks" / "hyy-rl"
DEFAULT_JOBS_DIR = Path("/tmp/analysisbakery-verl-harbor-jobs")
DEFAULT_TIMEOUT_SEC = 900


class HarborRewardResult:
    def __init__(
        self,
        reward,
        rewards,
        job_dir,
        trial_dir,
        candidate_sha256,
        candidate_chars,
        error=None,
        stdout_tail="",
        stderr_tail="",
    ):
        self.reward = float(reward)
        self.rewards = rewards
        self.job_dir = job_dir
        self.trial_dir = trial_dir
        self.candidate_sha256 = candidate_sha256
        self.candidate_chars = candidate_chars
        self.error = error
        self.stdout_tail = stdout_tail
        self.stderr_tail = stderr_tail

    def to_dict(self):
        return {
            "reward": self.reward,
            "rewards": self.rewards,
            "job_dir": self.job_dir,
            "trial_dir": self.trial_dir,
            "candidate_sha256": self.candidate_sha256,
            "candidate_chars": self.candidate_chars,
            "error": self.error,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
        }


def extract_candidate_config(solution_str):
    """Extract a full TRExFitter config from a model response.

    Training prompts ask the model to output only the config, but this accepts a
    fenced block too so smoke tests and early models can be less strict.
    """
    text = solution_str.strip()
    fences = re.findall(r"```(?:[A-Za-z0-9_+.-]+)?\s*\n(.*?)```", text, re.DOTALL)
    if fences:
        for fenced in fences:
            if 'Job: "hyy"' in fenced or "Job: hyy" in fenced:
                return fenced.strip() + "\n"
        return fences[0].strip() + "\n"
    return text + "\n"


def _write_candidate_solution(task_path, candidate_config):
    payload = base64.b64encode(candidate_config.encode("utf-8")).decode("ascii")
    solution_dir = task_path / "solution"
    solution_dir.mkdir(parents=True, exist_ok=True)
    solve_path = solution_dir / "solve.sh"
    solve_path.write_text(
        """#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
import base64

payload = "{payload}"
Path("/tmp/hyy_config.config").write_text(
    base64.b64decode(payload).decode("utf-8")
)
print("Wrote generated config to /tmp/hyy_config.config")
PY
""".format(payload=payload)
    )
    solve_path.chmod(0o755)


def _copy_task_with_candidate(
    base_task_path,
    candidate_config,
    keep_task,
):
    if keep_task:
        tmp_root = Path(tempfile.mkdtemp(prefix="verl-hyy-task-"))
        cleanup = None
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="verl-hyy-task-")
        tmp_root = Path(temp_dir.name)
        cleanup = temp_dir

    task_path = tmp_root / "hyy-rl"
    shutil.copytree(base_task_path, task_path)
    _write_candidate_solution(task_path, candidate_config)
    return task_path, cleanup


def _resolve_harbor_command(
    harbor_command,
):
    env_updates = {}
    if isinstance(harbor_command, list):
        return [str(part) for part in harbor_command], env_updates
    if isinstance(harbor_command, str) and harbor_command.strip():
        return shlex.split(harbor_command), env_updates

    harbor_bin = shutil.which("harbor")
    if harbor_bin:
        return [harbor_bin], env_updates

    local_src = REPO_ROOT / "external" / "harbor" / "src"
    pythonpath = os.environ.get("PYTHONPATH", "")
    env_updates["PYTHONPATH"] = (
        str(local_src) if not pythonpath else f"{local_src}{os.pathsep}{pythonpath}"
    )
    return [sys.executable, "-m", "harbor.cli.main"], env_updates


def _tail(text, max_chars=4000):
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _numeric_rewards(raw):
    if not isinstance(raw, dict):
        return {}
    rewards = {}
    for key, value in raw.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            rewards[str(key)] = float(value)
    return rewards


def _load_rewards(job_dir, score_key):
    if not job_dir.exists():
        return {}, None

    for result_path in sorted(job_dir.glob("*/result.json")):
        data = json.loads(result_path.read_text())
        verifier_result = data.get("verifier_result") or {}
        rewards = _numeric_rewards(verifier_result.get("rewards"))
        if rewards:
            return rewards, result_path.parent

    for trial_dir in sorted(path for path in job_dir.iterdir() if path.is_dir()):
        reward_json = trial_dir / "verifier" / "reward.json"
        if reward_json.exists():
            rewards = _numeric_rewards(json.loads(reward_json.read_text()))
            if rewards:
                return rewards, trial_dir
        reward_txt = trial_dir / "verifier" / "reward.txt"
        if reward_txt.exists():
            try:
                return {score_key: float(reward_txt.read_text().strip())}, trial_dir
            except ValueError:
                pass

    return {}, None


def _score_from_rewards(rewards, score_key):
    if score_key in rewards:
        return float(rewards[score_key])
    if rewards:
        first_key = sorted(rewards)[0]
        return float(rewards[first_key])
    return 0.0


async def _run_in_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def evaluate_candidate_config(
    candidate_config,
    task_path=DEFAULT_TASK_PATH,
    jobs_dir=DEFAULT_JOBS_DIR,
    harbor_command=None,
    timeout_sec=DEFAULT_TIMEOUT_SEC,
    score_key="reward",
    keep_task=False,
    strict=False,
):
    """Run Harbor against a generated config and return verifier rewards."""
    candidate_config = extract_candidate_config(candidate_config)
    digest = hashlib.sha256(candidate_config.encode("utf-8")).hexdigest()
    jobs_dir = jobs_dir.expanduser().resolve()
    jobs_dir.mkdir(parents=True, exist_ok=True)

    temp_cleanup = None
    task_copy_path = None
    stdout = ""
    stderr = ""
    try:
        task_copy_path, temp_cleanup = _copy_task_with_candidate(
            task_path.expanduser().resolve(),
            candidate_config,
            keep_task=keep_task,
        )
        command_base, env_updates = _resolve_harbor_command(harbor_command)
        job_name = f"verl-hyy-{uuid4().hex[:12]}"
        job_dir = jobs_dir / job_name
        command = [
            *command_base,
            "run",
            "-p",
            str(task_copy_path),
            "-a",
            "oracle",
            "--job-name",
            job_name,
            "--jobs-dir",
            str(jobs_dir),
            "--n-concurrent",
            "1",
        ]
        env = os.environ.copy()
        env.update(env_updates)
        env["PWD"] = str(REPO_ROOT)
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout_sec,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        rewards, trial_dir = _load_rewards(job_dir, score_key)
        reward = _score_from_rewards(rewards, score_key)
        error = None
        if completed.returncode != 0:
            error = f"harbor exited with status {completed.returncode}"
            if strict:
                raise RuntimeError(error)
        elif not rewards:
            error = "harbor completed but no verifier reward was found"
            if strict:
                raise RuntimeError(error)
        return HarborRewardResult(
            reward=reward,
            rewards=rewards or {score_key: reward},
            job_dir=str(job_dir),
            trial_dir=str(trial_dir) if trial_dir else None,
            candidate_sha256=digest,
            candidate_chars=len(candidate_config),
            error=error,
            stdout_tail=_tail(stdout),
            stderr_tail=_tail(stderr),
        )
    except Exception as exc:
        if strict:
            raise
        return HarborRewardResult(
            reward=0.0,
            rewards={score_key: 0.0},
            job_dir=None,
            trial_dir=None,
            candidate_sha256=digest,
            candidate_chars=len(candidate_config),
            error=str(exc),
            stdout_tail=_tail(stdout),
            stderr_tail=_tail(stderr),
        )
    finally:
        if temp_cleanup is not None:
            temp_cleanup.cleanup()
        elif keep_task and task_copy_path is not None:
            print(f"Kept temporary Harbor task at {task_copy_path}", file=sys.stderr)


async def compute_score(
    data_source,
    solution_str,
    ground_truth=None,
    extra_info=None,
):
    """VERL custom reward function entrypoint.

    VERL keeps the rollout token IDs and masks from its own generation backend.
    This function only returns the scalar verifier reward for that rollout.
    """
    del data_source, ground_truth
    extra_info = extra_info or {}
    result = await _run_in_thread(
        evaluate_candidate_config,
        solution_str,
        task_path=Path(extra_info.get("task_path", DEFAULT_TASK_PATH)),
        jobs_dir=Path(extra_info.get("jobs_dir", DEFAULT_JOBS_DIR)),
        harbor_command=extra_info.get("harbor_command"),
        timeout_sec=int(extra_info.get("harbor_timeout_sec", DEFAULT_TIMEOUT_SEC)),
        score_key=str(extra_info.get("score_key", "reward")),
        keep_task=bool(extra_info.get("keep_task", False)),
        strict=False,
    )
    return float(result.reward)


async def compute_score_with_details(
    data_source,
    solution_str,
    ground_truth=None,
    extra_info=None,
):
    """Optional VERL entrypoint when using reward-loop configs that accept maps."""
    del data_source, ground_truth
    extra_info = extra_info or {}
    result = await _run_in_thread(
        evaluate_candidate_config,
        solution_str,
        task_path=Path(extra_info.get("task_path", DEFAULT_TASK_PATH)),
        jobs_dir=Path(extra_info.get("jobs_dir", DEFAULT_JOBS_DIR)),
        harbor_command=extra_info.get("harbor_command"),
        timeout_sec=int(extra_info.get("harbor_timeout_sec", DEFAULT_TIMEOUT_SEC)),
        score_key=str(extra_info.get("score_key", "reward")),
        keep_task=bool(extra_info.get("keep_task", False)),
        strict=False,
    )
    return result.rewards


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Grade a generated hyy_config.config with Harbor."
    )
    parser.add_argument("candidate", type=Path, help="Path to generated config text.")
    parser.add_argument("--task-path", type=Path, default=DEFAULT_TASK_PATH)
    parser.add_argument("--jobs-dir", type=Path, default=DEFAULT_JOBS_DIR)
    parser.add_argument(
        "--harbor-command",
        default=None,
        help='Harbor command to run, e.g. "harbor" or "python -m harbor.cli.main".',
    )
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--score-key", default="reward")
    parser.add_argument("--keep-task", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only show the extracted candidate metadata; do not run Harbor.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    candidate = extract_candidate_config(args.candidate.read_text())
    if args.extract_only:
        print(
            json.dumps(
                {
                    "candidate_chars": len(candidate),
                    "candidate_sha256": hashlib.sha256(
                        candidate.encode("utf-8")
                    ).hexdigest(),
                    "starts_with": candidate[:120],
                },
                indent=2,
            )
        )
        return 0

    result = evaluate_candidate_config(
        candidate,
        task_path=args.task_path,
        jobs_dir=args.jobs_dir,
        harbor_command=args.harbor_command,
        timeout_sec=args.timeout_sec,
        score_key=args.score_key,
        keep_task=args.keep_task,
        strict=args.strict,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.error is None or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
