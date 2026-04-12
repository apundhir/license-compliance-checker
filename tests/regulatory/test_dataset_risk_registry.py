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

"""Tests for the dataset risk registry and _classify_dataset_risk helper."""

from __future__ import annotations

import pytest

from lcc.regulatory.eu_ai_act import (
    ARTICLE_53_SCOPE_NOTE,
    DATASET_RISK_REGISTRY,
    EUAIActAssessor,
    _classify_dataset_risk,
)
from lcc.models import Component, ComponentFinding, ComponentType


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

def _make_finding(
    name: str = "test-model",
    version: str = "1.0.0",
    comp_type: ComponentType = ComponentType.AI_MODEL,
    resolved_license: str | None = None,
    metadata: dict | None = None,
) -> ComponentFinding:
    return ComponentFinding(
        component=Component(
            type=comp_type,
            name=name,
            version=version,
            metadata=metadata or {},
        ),
        resolved_license=resolved_license,
    )


# ------------------------------------------------------------------ #
#  _classify_dataset_risk — required test cases                        #
# ------------------------------------------------------------------ #

def test_openai_api_data_flagged_as_critical():
    result = _classify_dataset_risk("openai_api_outputs")
    assert result["risk"] == "critical"


def test_wikipedia_is_safe():
    result = _classify_dataset_risk("wikipedia")
    assert result["commercial_use"] is True
    assert result["risk"] == "low"


def test_sharegpt_flagged():
    result = _classify_dataset_risk("ShareGPT_v4")
    assert result["risk"] in ("high", "critical")


# ------------------------------------------------------------------ #
#  _classify_dataset_risk — additional coverage                        #
# ------------------------------------------------------------------ #

def test_chatgpt_is_critical():
    result = _classify_dataset_risk("chatgpt")
    assert result["risk"] == "critical"
    assert result["commercial_use"] is False


def test_alpaca_is_high_risk():
    result = _classify_dataset_risk("alpaca")
    assert result["risk"] == "high"
    assert result["commercial_use"] is False


def test_dolly_is_low_risk():
    result = _classify_dataset_risk("dolly")
    assert result["risk"] == "low"
    assert result["commercial_use"] is True


def test_c4_is_low_risk():
    result = _classify_dataset_risk("c4")
    assert result["risk"] == "low"
    assert result["commercial_use"] is True


def test_common_crawl_is_low_risk():
    result = _classify_dataset_risk("common_crawl")
    assert result["risk"] == "low"


def test_unknown_dataset_returns_unknown():
    result = _classify_dataset_risk("my_custom_proprietary_dataset_xyz")
    assert result["risk"] == "unknown"
    assert result["commercial_use"] is None
    assert result["license"] == "unknown"
    assert result["dataset"] == "my_custom_proprietary_dataset_xyz"


def test_dataset_name_preserved_in_result():
    result = _classify_dataset_risk("Wikipedia")
    assert result["dataset"] == "Wikipedia"


def test_case_insensitive_match():
    """Registry lookup must be case-insensitive."""
    result = _classify_dataset_risk("WIKIPEDIA")
    assert result["risk"] == "low"


def test_hyphen_normalised():
    """Hyphens in dataset names should be normalised to underscores."""
    result = _classify_dataset_risk("common-crawl")
    assert result["risk"] == "low"


def test_books3_is_high_risk():
    result = _classify_dataset_risk("books3")
    assert result["risk"] == "high"
    assert result["commercial_use"] is False


def test_orca_is_high_risk():
    result = _classify_dataset_risk("orca")
    assert result["risk"] == "high"


def test_the_pile_is_high_risk():
    result = _classify_dataset_risk("the_pile")
    assert result["risk"] == "high"


# ------------------------------------------------------------------ #
#  Training data assessment — risk-based status derivation             #
# ------------------------------------------------------------------ #

class TestTrainingDataAssessmentWithRiskRegistry:
    def setup_method(self):
        self.assessor = EUAIActAssessor()

    def test_all_safe_datasets_gives_met(self):
        """wikipedia + c4 are both low-risk → status should be 'met'."""
        finding = _make_finding(
            name="safe-model",
            version="1.0",
            resolved_license="apache-2.0",
            metadata={"datasets": ["wikipedia", "c4"]},
        )
        assessment = self.assessor.assess_component(finding)
        training_ob = assessment.obligations[3]
        assert training_ob.article == "Art.53(1)(d)"
        assert training_ob.status == "met"

    def test_openai_api_dataset_gives_not_met(self):
        """A dataset derived from OpenAI API should trigger not_met."""
        finding = _make_finding(
            name="bad-model",
            version="1.0",
            resolved_license="apache-2.0",
            metadata={"datasets": ["openai_api_outputs"]},
        )
        assessment = self.assessor.assess_component(finding)
        training_ob = assessment.obligations[3]
        assert training_ob.status == "not_met"
        # At least one gap mentioning the dataset
        assert any("openai_api" in g.lower() or "critical" in g.lower() for g in training_ob.gaps)

    def test_unknown_dataset_gives_partial(self):
        """An unrecognised dataset name → partial (unknown risk)."""
        finding = _make_finding(
            name="unknown-data-model",
            version="1.0",
            resolved_license="apache-2.0",
            metadata={"datasets": ["my_secret_internal_corpus"]},
        )
        assessment = self.assessor.assess_component(finding)
        training_ob = assessment.obligations[3]
        assert training_ob.status == "partial"

    def test_mixed_safe_and_high_risk_gives_not_met(self):
        """Safe + high-risk mix → not_met (worst case wins)."""
        finding = _make_finding(
            name="mixed-model",
            version="1.0",
            resolved_license="apache-2.0",
            metadata={"datasets": ["wikipedia", "sharegpt"]},
        )
        assessment = self.assessor.assess_component(finding)
        training_ob = assessment.obligations[3]
        assert training_ob.status == "not_met"

    def test_no_training_data_gives_not_met(self):
        finding = _make_finding(
            name="empty-model",
            version="1.0",
            resolved_license="apache-2.0",
            metadata={},
        )
        assessment = self.assessor.assess_component(finding)
        training_ob = assessment.obligations[3]
        assert training_ob.status == "not_met"
        assert any("no training data" in g.lower() for g in training_ob.gaps)


# ------------------------------------------------------------------ #
#  Scope note                                                          #
# ------------------------------------------------------------------ #

class TestArticle53ScopeNote:
    def setup_method(self):
        self.assessor = EUAIActAssessor()

    def test_scope_note_on_assessment(self):
        finding = _make_finding(
            name="my-model",
            version="1.0",
            resolved_license="apache-2.0",
            metadata={"description": "A test model."},
        )
        assessment = self.assessor.assess_component(finding)
        assert assessment.scope_note == ARTICLE_53_SCOPE_NOTE
        assert "Article 53" in assessment.scope_note
        assert "PROVIDERS" in assessment.scope_note
        assert "Legal review" in assessment.scope_note

    def test_scope_note_in_to_dict(self):
        finding = _make_finding(
            name="my-model",
            version="1.0",
            resolved_license="apache-2.0",
        )
        d = self.assessor.assess_component(finding).to_dict()
        assert "scope_note" in d
        assert d["scope_note"] == ARTICLE_53_SCOPE_NOTE

    def test_scope_note_in_report_summary(self):
        findings = [
            _make_finding(
                name="test-model",
                comp_type=ComponentType.AI_MODEL,
                resolved_license="MIT",
            )
        ]
        report = self.assessor.assess_scan(findings)
        assert "scope_note" in report.summary
        assert report.summary["scope_note"] == ARTICLE_53_SCOPE_NOTE
