---
title: Compliance Auditor Env
emoji: "📄"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: GDPR and CCPA compliance auditor on OpenEnv.
---

# Compliance Auditor Env

Compliance Auditor Env is an OpenEnv environment where an agent audits procedurally generated privacy policies for GDPR and CCPA violations. The environment exposes a typed `reset() / step() / state()` API, supports three graded tasks, and includes a reproducible baseline in `inference.py`.

## Why This Environment Matters

This benchmark simulates a realistic legal review workflow rather than a toy game. The agent must read a policy, inspect regulations, identify concrete violations, propose remediation, and submit a structured final report. The environment uses procedural clause generation so agents cannot simply memorize a single static policy.

## Environment Design

### Workflow

A successful agent should:

1. Read the policy once.
2. Check the most relevant regulations.
3. Flag supported violations with accurate issue IDs.
4. Suggest a fix immediately after each correct flag.
5. Submit the report before the step budget is exhausted.

### Action Space

The agent can call these tools:

- `read_document`
- `check_regulation`
- `search_web`
- `ask_expert`
- `compare_clauses`
- `flag_violation`
- `suggest_fix`
- `submit_report`

### Observation Space

Each step returns a typed `ComplianceObservation` containing:

- `message`
- `reward`
- `done`
- `flagged_issues`
- `available_tools`
- `max_steps`
- `error`

### State Space

The typed `ComplianceState` tracks:

- `episode_id`
- `step_count`
- `task_id`
- `precision`
- `recall`
- `ground_truth_keys`

## Tasks and Grading

The submission includes three graded tasks:

- `easy_gdpr_obvious`: obvious GDPR failures such as missing controller contact, denied erasure, or indefinite retention.
- `medium_gdpr_subtle`: subtler GDPR issues such as invalid consent, vague retention, breach notification delay, cookie walls, and missing safeguards.
- `hard_gdpr_ccpa_multi`: mixed GDPR and CCPA conflicts, including opt-out misuse, sharing-sale disclosure issues, discrimination, authorized-agent handling, dark patterns, and other modern privacy failures.

The final environment reward on `submit_report` is the trajectory F1 score in `[0.0, 1.0]`, derived from precision and recall over flagged violations.

## Reward Shaping

The environment provides dense intermediate feedback:

- small positive reward for reading the document and targeted regulation checks
- larger reward for correct flags, with an early-action bonus
- positive reward for a fix suggestion after a correct flag
- penalties for false positives, duplicate flags, and invalid fix attempts
- final episode reward equal to report F1 score in `[0.0, 1.0]`

This makes the benchmark suitable both for baseline evaluation and for RL-style agent improvement.

## Baseline Agent

The baseline in `inference.py` is designed to satisfy the hackathon evaluator requirements:

- `inference.py` is located at the repository root
- all LLM calls go through the OpenAI client
- when evaluator variables are injected, the script uses `API_BASE_URL` and `API_KEY`
- structured stdout strictly follows `[START]`, `[STEP]`, and `[END]`
- the baseline can run a single task through `OPENENV_TASK` or all three tasks by default
- evidence quotes are validated against the actual policy text before flagging

### Baseline Strategy

The baseline uses a multi-stage approach:

1. Read the policy text.
2. Build a regulation-check blueprint.
3. Query only a limited number of relevant regulations based on difficulty.
4. Ask the model for high-confidence findings with exact supporting evidence.
5. Normalize findings to remove unsupported or duplicate issues.
6. Flag, fix, and submit with explicit step budgeting.

## Reproducibility and Stability

The baseline is intentionally constrained for reproducibility:

- `temperature=0.0`
- `top_p=1.0`
- `seed=42`
- deterministic regulation budgets by difficulty
- evidence normalization before action execution

Example local baseline runs observed during development:

- easy: `0.400`
- medium: `0.750`
- hard: `0.500`

Actual evaluator scores may vary depending on the injected model endpoint, policy generation seed, and task instance.

## Repository Structure

```text
bio_janitor_env/
+-- Dockerfile
+-- README.md
+-- __init__.py
+-- client.py
+-- environment.py
+-- inference.py
+-- models.py
+-- openenv.yaml
+-- pyproject.toml
+-- requirements.txt
+-- server/
¦   +-- __init__.py
¦   +-- app.py
¦   +-- Dockerfile
¦   +-- environment.py
+-- tasks/
¦   +-- base_knowledge.json
¦   +-- easy_gdpr_obvious.json
¦   +-- medium_gdpr_subtle.json
¦   +-- hard_gdpr_ccpa_multi.json
+-- test_environment.py
```

## Local Validation

```powershell
venv\Scripts\openenv.exe validate .
venv\Scripts\python.exe -m pytest -q
venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 7860
Invoke-WebRequest -UseBasicParsing -Method POST -Uri "http://127.0.0.1:7860/reset" -ContentType "application/json" -Body "{}"
```

## Baseline Usage

Run a single task:

```powershell
$env:ENV_URL='http://127.0.0.1:7860'
$env:API_BASE_URL='https://router.huggingface.co/v1'
$env:MODEL_NAME='Qwen/Qwen2.5-72B-Instruct'
$env:API_KEY='YOUR_EVALUATOR_OR_PROXY_KEY'
$env:OPENENV_TASK='medium_gdpr_subtle'
venv\Scripts\python.exe inference.py
```

Run all three tasks:

```powershell
$env:ENV_URL='http://127.0.0.1:7860'
$env:API_BASE_URL='https://router.huggingface.co/v1'
$env:MODEL_NAME='Qwen/Qwen2.5-72B-Instruct'
$env:API_KEY='YOUR_EVALUATOR_OR_PROXY_KEY'
Remove-Item Env:OPENENV_TASK -ErrorAction SilentlyContinue
venv\Scripts\python.exe inference.py
```

## Hugging Face Space

This environment is deployed as a Docker Space and exposes the required reset/step API for validation. The production deployment uses `MAX_CONCURRENT_ENVS=1` because this environment maintains isolated session state and is not marked as multi-session concurrent.

## Submission Checklist Mapping

This repository satisfies the key Round 1 requirements:

- real-world, non-toy environment
- full OpenEnv spec with typed models and `openenv.yaml`
- three graded tasks across easy, medium, and hard difficulty
- shaped rewards with partial progress signals
- root-level `inference.py`
- root-level `Dockerfile`
- OpenAI client usage for all LLM calls
- strict structured stdout logs
- Hugging Face Space deployment compatibility

## Notes

The policy generator includes both compliant and violating clause variants across many privacy topics, including GDPR, CCPA, CPRA, AI-training consent, biometric retention, dark-pattern deletion flows, and cross-jurisdiction consent conflicts. This makes the environment suitable for both human inspection and agent benchmarking.

