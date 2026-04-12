import pytest
from pydantic import ValidationError

from environment import ComplianceAuditorEnv, grade_easy_gdpr_obvious
from models import ComplianceAction

def test_environment_initialization():
    env = ComplianceAuditorEnv()
    obs = env.reset(task_name="easy_gdpr_obvious")
    
    assert obs.done is False
    assert "Initialized audit" in obs.message
    assert len(env.ground_truth) > 0 # Proves procedural engine generated violations
    assert env.state.step_count == 0

def test_read_document_action():
    env = ComplianceAuditorEnv()
    env.reset()
    action = ComplianceAction(tool="read_document", parameters={})
    obs = env.step(action)
    
    assert "DOCUMENT TEXT" in obs.message
    assert obs.reward > 0.0 # Proves multi-stage grading works
    assert env.state.step_count == 1

def test_invalid_tool():
    with pytest.raises(ValidationError):
        ComplianceAction(tool="fake_tool", parameters={})


def test_reset_is_deterministic_for_same_task():
    env = ComplianceAuditorEnv()
    env.reset(task_name="medium_gdpr_subtle")
    first_policy = env.policy_text
    first_truth = dict(env.ground_truth)

    env.reset(task_name="medium_gdpr_subtle")

    assert env.policy_text == first_policy
    assert env.ground_truth == first_truth


def test_submit_report_score_is_strictly_between_zero_and_one():
    env = ComplianceAuditorEnv()
    env.reset(task_name="easy_gdpr_obvious")
    env.step(ComplianceAction(tool="read_document", parameters={}))

    for issue_id in env.ground_truth.keys():
        env.step(
            ComplianceAction(
                tool="flag_violation",
                parameters={"issue_id": issue_id, "explanation": "Valid"},
            )
        )

    obs = env.step(ComplianceAction(tool="submit_report", parameters={}))

    assert 0.0 < obs.reward < 1.0


def test_false_positive_penalty():
    env = ComplianceAuditorEnv()
    env.reset(task_name="easy_gdpr_obvious")
    env.step(ComplianceAction(tool="read_document", parameters={}))

    obs = env.step(
        ComplianceAction(
            tool="flag_violation",
            parameters={"issue_id": "not_a_real_issue", "explanation": "Wrong"},
        )
    )

    assert obs.reward < 0.0
    assert obs.error == "False positive."


def test_step_limit_timeout(monkeypatch):
    monkeypatch.setenv("MAX_STEPS", "1")
    env = ComplianceAuditorEnv()
    env.reset(task_name="easy_gdpr_obvious")

    obs = env.step(ComplianceAction(tool="read_document", parameters={}))

    assert obs.done is True
    assert "WARNING: Step limit reached." in obs.message


def test_check_regulation_returns_relevant_text():
    env = ComplianceAuditorEnv()
    env.reset(task_name="medium_gdpr_subtle")

    obs = env.step(
        ComplianceAction(
            tool="check_regulation",
            parameters={"query": "GDPR Article 17"},
        )
    )

    assert "REGULATION TEXT" in obs.message
    assert "GDPR Article 17" in obs.message


def test_duplicate_flag_penalty():
    env = ComplianceAuditorEnv()
    env.reset(task_name="easy_gdpr_obvious")
    env.step(ComplianceAction(tool="read_document", parameters={}))
    issue_id = next(iter(env.ground_truth.keys()))

    env.step(
        ComplianceAction(
            tool="flag_violation",
            parameters={"issue_id": issue_id, "explanation": "Valid"},
        )
    )
    obs = env.step(
        ComplianceAction(
            tool="flag_violation",
            parameters={"issue_id": issue_id, "explanation": "Duplicate"},
        )
    )

    assert obs.reward < 0.0
    assert obs.error == "Issue already flagged."


def test_grader_recovers_ground_truth_from_earlier_step():
    early_state_trajectory = [
        {
            "info": {
                "state": {
                    "ground_truth_keys": ["right_to_erasure"],
                }
            }
        },
        {
            "action": {
                "tool": "read_document",
                "parameters": {},
            }
        },
        {
            "action": {
                "tool": "check_regulation",
                "parameters": {"query": "GDPR Article 17"},
            }
        },
        {
            "action": {
                "tool": "flag_violation",
                "parameters": {"issue_id": "right_to_erasure"},
            }
        },
        {
            "action": {
                "tool": "submit_report",
                "parameters": {},
            },
            "info": {},
        },
    ]

    final_state_trajectory = [
        step if index != 0 else {"info": {}}
        for index, step in enumerate(early_state_trajectory)
    ]
    final_state_trajectory[-1] = {
        "action": {
            "tool": "submit_report",
            "parameters": {},
        },
        "info": {
            "state": {
                "ground_truth_keys": ["right_to_erasure"],
            }
        },
    }

    recovered_score = grade_easy_gdpr_obvious(early_state_trajectory)
    reference_score = grade_easy_gdpr_obvious(final_state_trajectory)

    assert 0.0 < recovered_score < 1.0
    assert recovered_score == pytest.approx(reference_score)


def test_grader_penalizes_skipping_investigation():
    trajectory = [
        {
            "info": {
                "state": {
                    "ground_truth_keys": ["right_to_erasure"],
                }
            }
        },
        {
            "action": {
                "tool": "flag_violation",
                "parameters": {"issue_id": "right_to_erasure"},
            }
        },
        {
            "action": {
                "tool": "submit_report",
                "parameters": {},
            }
        },
    ]

    score = grade_easy_gdpr_obvious(trajectory)

    assert 0.0 < score < 0.9
