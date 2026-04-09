import pytest
from pydantic import ValidationError

from environment import ComplianceAuditorEnv
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
