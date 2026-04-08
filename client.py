from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import ComplianceAction, ComplianceObservation, ComplianceState
except ImportError:
    from models import ComplianceAction, ComplianceObservation, ComplianceState


class ComplianceAuditorClient(
    EnvClient[ComplianceAction, ComplianceObservation, ComplianceState]
):
    """Typed OpenEnv client for the compliance auditor environment."""

    def _step_payload(self, action: ComplianceAction) -> dict:
        return action.model_dump()

    def _parse_result(self, payload: dict) -> StepResult[ComplianceObservation]:
        observation_payload = payload.get("observation", {})
        observation = ComplianceObservation(**observation_payload)
        return StepResult(
            observation=observation,
            reward=payload.get("reward", observation.reward),
            done=payload.get("done", observation.done),
        )

    def _parse_state(self, payload: dict) -> ComplianceState:
        return ComplianceState(**payload)
