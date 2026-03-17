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

"""
Regulatory compliance framework models and constants.

Provides data structures for tracking compliance with the EU AI Act,
NIST AI RMF, ISO/IEC 42001, and related frameworks.
"""

from lcc.regulatory.constants import (
    EU_AI_ACT_ARTICLE_53_OBLIGATIONS,
    ISO_42001_CONTROL_AREAS,
    NIST_AI_RMF_FUNCTIONS,
    RAIL_RESTRICTION_CATEGORIES,
)
from lcc.regulatory.eu_ai_act import (
    EUAIActAssessor,
    get_training_data_info,
    get_use_restrictions,
    is_gpai_model,
)
from lcc.regulatory.frameworks import (
    AIRiskClassification,
    Article53Obligation,
    CopyrightComplianceStatus,
    RegulatoryAssessment,
    RegulatoryFramework,
    RegulatoryMetadata,
    RegulatoryReport,
    TransparencyRequirement,
)
from lcc.regulatory.reporter import (
    RegulatoryReporter,
    generate_compliance_pack,
)

__all__ = [
    # Enums
    "AIRiskClassification",
    "CopyrightComplianceStatus",
    "RegulatoryFramework",
    "TransparencyRequirement",
    # Dataclasses
    "Article53Obligation",
    "RegulatoryAssessment",
    "RegulatoryMetadata",
    "RegulatoryReport",
    # Constants
    "EU_AI_ACT_ARTICLE_53_OBLIGATIONS",
    "ISO_42001_CONTROL_AREAS",
    "NIST_AI_RMF_FUNCTIONS",
    "RAIL_RESTRICTION_CATEGORIES",
    # Assessors
    "EUAIActAssessor",
    # Reporters
    "RegulatoryReporter",
    "generate_compliance_pack",
    # Helpers
    "get_training_data_info",
    "get_use_restrictions",
    "is_gpai_model",
]
