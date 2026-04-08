"""Server-side environment exports for the Compliance Auditor."""

try:
    from ..environment import (
        ComplianceAuditorEnv,
        grade_easy_gdpr_obvious,
        grade_hard_gdpr_ccpa_multi,
        grade_medium_gdpr_subtle,
    )
except ImportError:
    from environment import (
        ComplianceAuditorEnv,
        grade_easy_gdpr_obvious,
        grade_hard_gdpr_ccpa_multi,
        grade_medium_gdpr_subtle,
    )

__all__ = [
    "ComplianceAuditorEnv",
    "grade_easy_gdpr_obvious",
    "grade_medium_gdpr_subtle",
    "grade_hard_gdpr_ccpa_multi",
]
