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
Regulatory framework constants and reference data.

Contains the canonical obligation lists, control areas, and restriction
categories used by the framework assessors:
- EU AI Act Article 53 GPAI obligations
- NIST AI RMF 1.0 core functions
- ISO/IEC 42001 key control areas
- RAIL / OpenRAIL standard restriction categories
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# EU AI Act -- Article 53 GPAI provider obligations
# ---------------------------------------------------------------------------

EU_AI_ACT_ARTICLE_53_OBLIGATIONS: list[dict[str, Any]] = [
    {
        "article": "Art.53(1)(a)",
        "title": "Technical documentation",
        "description": (
            "Draw up and keep up-to-date the technical documentation of the "
            "model, including its training and testing process and the results "
            "of its evaluation, which shall contain, at a minimum, the "
            "information set out in Annex XI for the purpose of providing it, "
            "upon request, to the AI Office and national competent authorities."
        ),
    },
    {
        "article": "Art.53(1)(b)",
        "title": "Information and documentation for downstream providers",
        "description": (
            "Draw up and keep up-to-date information and documentation and "
            "make it available to providers of AI systems who intend to "
            "integrate the general-purpose AI model into their AI systems. "
            "The information and documentation shall enable downstream "
            "providers to understand the capabilities and limitations of the "
            "GPAI model and comply with their own obligations."
        ),
    },
    {
        "article": "Art.53(1)(c)",
        "title": "Copyright policy compliance",
        "description": (
            "Put in place a policy to comply with Union copyright law, and in "
            "particular to identify and comply with, including through "
            "state-of-the-art technologies, a reservation of rights expressed "
            "pursuant to Article 4(3) of Directive (EU) 2019/790."
        ),
    },
    {
        "article": "Art.53(1)(d)",
        "title": "Training data summary",
        "description": (
            "Draw up and make publicly available a sufficiently detailed "
            "summary about the content used for training of the general-purpose "
            "AI model, according to a template provided by the AI Office."
        ),
    },
    {
        "article": "Art.53(2)",
        "title": "Systemic risk additional obligations",
        "description": (
            "Providers of GPAI models with systemic risk shall, in addition to "
            "the obligations referred to in paragraph 1: perform model "
            "evaluations, assess and mitigate possible systemic risks, keep "
            "track of serious incidents, and ensure an adequate level of "
            "cybersecurity protection."
        ),
    },
]

# ---------------------------------------------------------------------------
# NIST AI RMF 1.0 -- Core functions and categories
# ---------------------------------------------------------------------------

NIST_AI_RMF_FUNCTIONS: list[dict[str, str]] = [
    {
        "function": "Govern",
        "description": (
            "Cultivate and implement a culture of risk management within "
            "organisations designing, developing, deploying, or using AI "
            "systems. Cross-cutting function that informs and is informed by "
            "the other three functions."
        ),
    },
    {
        "function": "Map",
        "description": (
            "Establish the context to frame risks related to an AI system. "
            "Identify and document risks and potential impacts so that they "
            "can be measured, managed, and communicated."
        ),
    },
    {
        "function": "Measure",
        "description": (
            "Employ quantitative, qualitative, or mixed-method tools, "
            "techniques, and methodologies to analyse, assess, benchmark, "
            "and monitor AI risk and related impacts."
        ),
    },
    {
        "function": "Manage",
        "description": (
            "Allocate risk resources to mapped and measured risks on a "
            "regular basis and as defined by the Govern function. Includes "
            "plans and approaches for risk response, recovery, and "
            "communication."
        ),
    },
]

# ---------------------------------------------------------------------------
# ISO/IEC 42001 -- Key control areas for AI management systems
# ---------------------------------------------------------------------------

ISO_42001_CONTROL_AREAS: list[dict[str, str]] = [
    {
        "control_id": "A.2",
        "title": "AI policy",
        "description": (
            "Establish, communicate, and maintain an AI policy that is "
            "appropriate to the organisation's purpose and provides a "
            "framework for setting AI objectives."
        ),
    },
    {
        "control_id": "A.3",
        "title": "Internal organisation for AI",
        "description": (
            "Define roles, responsibilities, and authorities for AI "
            "governance, ensuring accountability and oversight of AI "
            "systems throughout their lifecycle."
        ),
    },
    {
        "control_id": "A.4",
        "title": "Resources for AI systems",
        "description": (
            "Determine and provide the resources, including data, tooling, "
            "computing infrastructure, and human resources needed for the "
            "AI management system."
        ),
    },
    {
        "control_id": "A.5",
        "title": "Assessing impacts of AI systems",
        "description": (
            "Conduct impact assessments that consider the effects of AI "
            "systems on individuals, groups, and society, including ethical, "
            "legal, and safety considerations."
        ),
    },
    {
        "control_id": "A.6",
        "title": "AI system lifecycle",
        "description": (
            "Establish processes for the full AI system lifecycle including "
            "design, data management, model building, verification, "
            "deployment, operation, and retirement."
        ),
    },
    {
        "control_id": "A.7",
        "title": "Data for AI systems",
        "description": (
            "Manage data quality, provenance, privacy, and appropriate use "
            "throughout the data lifecycle. Ensure training and evaluation "
            "data meets defined requirements."
        ),
    },
    {
        "control_id": "A.8",
        "title": "Information for interested parties",
        "description": (
            "Provide transparency and appropriate disclosure to interested "
            "parties about AI systems, including capabilities, limitations, "
            "intended use, and potential risks."
        ),
    },
    {
        "control_id": "A.9",
        "title": "Use of AI systems",
        "description": (
            "Define policies for the responsible use of AI systems, "
            "including monitoring, human oversight requirements, and "
            "conditions for acceptable deployment contexts."
        ),
    },
    {
        "control_id": "A.10",
        "title": "Third-party and supplier relationships",
        "description": (
            "Manage risks from third-party AI components, services, and "
            "data sources. Ensure suppliers meet the organisation's AI "
            "management requirements."
        ),
    },
]

# ---------------------------------------------------------------------------
# RAIL / OpenRAIL -- Standard use-based restriction categories
# ---------------------------------------------------------------------------

RAIL_RESTRICTION_CATEGORIES: list[dict[str, str]] = [
    {
        "id": "no-harm",
        "title": "No harm",
        "description": (
            "The model or its derivatives shall not be used to harm, "
            "injure, or damage individuals, groups, or the environment."
        ),
    },
    {
        "id": "no-illegal-activity",
        "title": "No illegal activity",
        "description": (
            "The model shall not be used to engage in, promote, generate, "
            "contribute to, encourage, plan, incite, or further illegal "
            "activity or content."
        ),
    },
    {
        "id": "no-discrimination",
        "title": "No discrimination",
        "description": (
            "The model shall not be used to discriminate against individuals "
            "or groups based on legally protected characteristics."
        ),
    },
    {
        "id": "no-personal-data-exploitation",
        "title": "No personal data exploitation",
        "description": (
            "The model shall not be used to collect, process, disclose, "
            "generate, or infer personal data in ways that violate privacy "
            "laws or individuals' reasonable expectations of privacy."
        ),
    },
    {
        "id": "no-misinformation",
        "title": "No misinformation",
        "description": (
            "The model shall not be used to generate or disseminate "
            "verifiably false or misleading information with the intent to "
            "deceive or cause harm."
        ),
    },
    {
        "id": "no-impersonation",
        "title": "No impersonation",
        "description": (
            "The model shall not be used to impersonate real individuals "
            "without their consent, or to create deceptive synthetic media."
        ),
    },
    {
        "id": "no-deception",
        "title": "No deception",
        "description": (
            "The model shall not be used to deceive, mislead, or "
            "manipulate individuals in ways that could cause harm or "
            "undermine informed decision-making."
        ),
    },
    {
        "id": "no-automated-legal-advice",
        "title": "No automated legal advice",
        "description": (
            "The model shall not be used to provide fully automated legal, "
            "financial, or medical advice without qualified human oversight."
        ),
    },
    {
        "id": "attribution-required",
        "title": "Attribution required",
        "description": (
            "Users must provide appropriate credit and attribution when "
            "using or distributing the model or its outputs."
        ),
    },
    {
        "id": "user-threshold",
        "title": "User threshold",
        "description": (
            "Commercial use is restricted beyond a specified monthly active "
            "user threshold; a separate commercial licence is required above "
            "that limit."
        ),
    },
    {
        "id": "acceptable-use-policy",
        "title": "Acceptable use policy",
        "description": (
            "Users must adhere to the provider's acceptable use policy, "
            "which may impose additional restrictions beyond the licence "
            "terms."
        ),
    },
]
