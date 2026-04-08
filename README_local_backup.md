---
title: Bio Janitor Env
emoji: "📄"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# OpenEnv Compliance Auditor

OpenEnv Compliance Auditor is a real-world legal auditing environment where an agent reviews privacy policies for GDPR, CCPA, and CPRA violations. The environment procedurally generates realistic policy documents, exposes a typed OpenEnv interface, and rewards partial progress during review before scoring the final audit with an F1-based report score.

## Environment Summary

- Domain: privacy-policy compliance auditing
- Interface: typed OpenEnv `reset()`, `step()`, and `state()`
- Core tools: `read_document`, `check_regulation`, `search_web`, `ask_expert`, `compare_clauses`, `flag_violation`, `suggest_fix`, `submit_report`
- Reward style: dense intermediate rewards plus final normalized score in `[0, 1]`
- Deployment target: Hugging Face Spaces via an OpenEnv-compatible FastAPI server

## Tasks

| Task | Focus | Default violations | Default max steps |
| --- | --- | ---: | ---: |
| `easy_gdpr_obvious` | obvious GDPR disclosure and rights failures | 3 | 15 |
| `medium_gdpr_subtle` | subtler GDPR consent, retention, and transfer issues | 4 | 20 |
| `hard_gdpr_ccpa_multi` | mixed GDPR + CCPA/CPRA conflicts and modern privacy risks | 6 | 25 |

Each task is procedurally generated from a clause library, so the agent sees fresh documents rather than one static policy.

## Action Space

The action model is defined in `models.py` through `ComplianceAction`.

| Tool | Purpose |
| --- | --- |
| `read_document` | retrieve the privacy policy text |
| `check_regulation` | inspect relevant GDPR / CCPA / CPRA references |
| `search_web` | simulate external legal guidance lookup |
| `ask_expert` | simulate expert hint retrieval |
| `compare_clauses` | compare policy clause behavior |
| `flag_violation` | report a suspected issue with explanation |
| `suggest_fix` | propose remediation for a flagged issue |
| `submit_report` | finalize the audit and receive the final score |

## Observation Space

The observation model is defined in `models.py` through `ComplianceObservation`.

Each step returns:

- `message`: current observation or tool feedback
- `reward`: incremental reward from the last action
- `done`: whether the episode is finished
- `flagged_issues`: issues flagged so far
- `available_tools`: tools the agent may call
- `max_steps`: task-specific step budget
- `error`: raw tool error if the previous action failed

## Reward Design

The environment provides shaped rewards to encourage useful audit behavior:

- reading the document early gives a small positive reward
- regulation checks and research tools give small exploration rewards
- correct `flag_violation` actions give larger positive rewards
- early correct flags earn a bonus
- repeated or false-positive flags are penalized
- valid `suggest_fix` actions earn a small positive reward
- `submit_report` returns the final F1 score based on precision and recall

This gives the agent partial progress signals while keeping the final objective aligned with accurate auditing.

## Baseline Inference

The bundled `inference.py` is an LLM-driven baseline that:

- uses the OpenAI client with `API_BASE_URL`, `MODEL_NAME`, and `HF_TOKEN`
- emits the required structured logs in `[START]`, `[STEP]`, `[END]` format
- reads the document once, plans regulation checks, flags issues, suggests fixes, and submits a report
- supports `LOCAL_IMAGE_NAME` when using `from_docker_image()`

## Verified Local Checks

Validated locally on April 8, 2026:

- `openenv validate .` -> pass
- `pytest -q` -> pass
- `POST /reset` on the local server -> HTTP `200`

## Measured LLM Baseline Scores

Measured locally on April 8, 2026 against the local server using the Hugging Face router with `Qwen/Qwen2.5-72B-Instruct`.

| Task | Final score | Notes |
| --- | ---: | --- |
| `easy_gdpr_obvious` | `0.400` | strong start, one false positive before submit |
| `medium_gdpr_subtle` | `0.750` | solid multi-flag run with good step discipline |
| `hard_gdpr_ccpa_multi` | `0.500` | finds several real issues but still overflags some compliant clauses |

## Local Run Instructions

Start the server:

```powershell
venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 7860
```

Check the reset endpoint:

```powershell
Invoke-WebRequest -UseBasicParsing -Method POST -Uri "http://127.0.0.1:7860/reset" -ContentType "application/json" -Body "{}" | Select-Object StatusCode, Content
```

Run the baseline agent:

```powershell
$env:ENV_URL='http://127.0.0.1:7860'
$env:API_BASE_URL='https://router.huggingface.co/v1'
$env:MODEL_NAME='Qwen/Qwen2.5-72B-Instruct'
$env:HF_TOKEN='YOUR_TOKEN'
$env:OPENENV_TASK='medium_gdpr_subtle'
venv\Scripts\python.exe inference.py
```

Run tests:

```powershell
venv\Scripts\python.exe -m pytest -q
```

Run OpenEnv validation:

```powershell
venv\Scripts\openenv.exe validate .
```

## Deployment Notes

- OpenEnv entry point: `server.app:app`
- Root `Dockerfile` is the submission-safe Docker build target
- `server/environment.py` re-exports the environment and grader functions referenced by `openenv.yaml`
- `client.py` and `models.py` remain at the package root to match the OpenEnv scaffold
