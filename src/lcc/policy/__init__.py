# Copyright 2025 Ajay Pundhir
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Policy utilities package."""

from .base import (  # noqa: F401
    Policy,
    PolicyAlternative,
    PolicyDecision,
    PolicyError,
    PolicyManager,
    evaluate_policy,
)
from .compatibility import (  # noqa: F401
    CompatibilityIssue,
    CompatibilityReport,
    LicenseCompatibilityChecker,
    classify_license,
    evaluate_license_compatibility,
)
from .compatibility_integration import (  # noqa: F401
    policy_has_compatibility,
    run_compatibility_check,
)
from .decision_recorder import DecisionRecorder  # noqa: F401
from .opa_client import OPAClient, OPAClientError  # noqa: F401

__all__ = [
    "Policy",
    "PolicyAlternative",
    "PolicyDecision",
    "PolicyManager",
    "PolicyError",
    "evaluate_policy",
    "CompatibilityIssue",
    "CompatibilityReport",
    "LicenseCompatibilityChecker",
    "classify_license",
    "evaluate_license_compatibility",
    "policy_has_compatibility",
    "run_compatibility_check",
    "DecisionRecorder",
    "OPAClient",
    "OPAClientError",
]
