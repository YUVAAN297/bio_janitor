"""FastAPI application for the OpenEnv Compliance Auditor."""

import os

try:
    from openenv.core.env_server.http_server import create_app
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "openenv-core is required to run the server. Install dependencies first."
    ) from exc

try:
    from ..models import ComplianceAction, ComplianceObservation
    from .environment import ComplianceAuditorEnv
except ImportError:
    from models import ComplianceAction, ComplianceObservation
    from server.environment import ComplianceAuditorEnv


app = create_app(
    ComplianceAuditorEnv,
    ComplianceAction,
    ComplianceObservation,
    env_name="compliance_auditor_env",
    max_concurrent_envs=1,
)


def main(host: str = "0.0.0.0", port: int = 7860) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
