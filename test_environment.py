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
