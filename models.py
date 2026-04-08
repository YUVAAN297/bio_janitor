from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from openenv.core.env_server import Action, Observation, State


class ComplianceAction(Action):
    tool: Literal[
        "read_document",
        "check_regulation",
        "search_web",
        "ask_expert",
        "compare_clauses",
        "flag_violation",
        "suggest_fix",
        "submit_report",
    ]
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ComplianceState(State):
    episode_id: str
    step_count: int = 0
    task_id: str
    precision: float = 0.0
    recall: float = 0.0
    ground_truth_keys: List[str] = Field(default_factory=list)


class ComplianceObservation(Observation):
    done: bool = False
    reward: float = 0.0
    message: str = ""
    flagged_issues: List[dict] = Field(default_factory=list)
    available_tools: List[str] = Field(default_factory=list)
    max_steps: int = 15
    error: Optional[str] = None
