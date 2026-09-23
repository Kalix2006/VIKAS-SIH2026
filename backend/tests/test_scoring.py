"""Tests for scoring service: hand-computed formula validation and embedding similarity.

Every formula test validates exact manual mathematical derivations to guarantee
that scoring logic is non-black-box and auditable for a technical government jury.
"""

import pytest

from app.models.enums import GapType
from app.services.scoring import (
    HAS_NLP,
    calculate_gap_score,
    scoring_service,
)


def test_hand_computed_curriculum_drift() -> None:
    """Case 1: Curriculum Drift (High job volume, low syllabus similarity).

    Hand Derivation:
    ----------------
    Similarity S = 0.25 -> Dissimilarity = 1.0 - 0.25 = 0.75
    Volume V = 60
    Volume Factor F_V = ln(1 + 60) / ln(101) = ln(61) / ln(101) = 0.8907
    Avg Age T = 12.0 days
    Recency Decay R = exp(-0.02 * 12.0) = exp(-0.24) = 0.7866
    Market Demand Factor W = (0.60 * 0.8907) + (0.40 * 0.7866) = 0.8491
    Final Gap Score = 100 * 0.75 * 0.8491 = 63.68
    Expected Classification = CURRICULUM_DRIFT
    """
    score, gap_type, breakdown = calculate_gap_score(
        similarity=0.25,
        volume=60,
        avg_age_days=12.0,
        seats_available=40,
    )

    assert score == 63.68
    assert gap_type == GapType.CURRICULUM_DRIFT
    assert breakdown["volume_factor"] == 0.8907
    assert breakdown["recency_decay"] == 0.7866
    assert breakdown["market_demand_factor"] == 0.8491
    assert breakdown["final_gap_score"] == 63.68


def test_hand_computed_undersupply() -> None:
    """Case 2: Undersupply (High similarity, employer vacancies exceed seats).

    Hand Derivation:
    ----------------
    Similarity S = 0.85 -> Dissimilarity = 1.0 - 0.85 = 0.15
    Volume V = 75
    Volume Factor F_V = ln(76) / ln(101) = 4.33073 / 4.61512 = 0.9384
    Avg Age T = 5.0 days
    Recency Decay R = exp(-0.02 * 5.0) = exp(-0.10) = 0.9048
    Market Demand Factor W = (0.60 * 0.9384) + (0.40 * 0.9048) = 0.9250
    Final Gap Score = 100 * 0.15 * 0.9250 = 13.88
    Expected Classification = UNDERSUPPLY
    """
    score, gap_type, breakdown = calculate_gap_score(
        similarity=0.85,
        volume=75,
        avg_age_days=5.0,
        seats_available=30,
    )

    assert score == 13.88
    assert gap_type == GapType.UNDERSUPPLY
    assert breakdown["volume_factor"] == 0.9384
    assert breakdown["recency_decay"] == 0.9048
    assert breakdown["market_demand_factor"] == 0.9250
    assert breakdown["final_gap_score"] == 13.88


def test_hand_computed_oversupply_zero_volume() -> None:
    """Case 3: Oversupply with zero vacancies (No local employer demand).

    Hand Derivation:
    ----------------
    Volume V = 0 -> Volume Factor F_V = 0.0, Recency Decay R = 0.0
    Market Demand Factor W = 0.0
    Final Gap Score = 0.0
    Expected Classification = OVERSUPPLY
    """
    score, gap_type, breakdown = calculate_gap_score(
        similarity=0.50,
        volume=0,
        avg_age_days=0.0,
        seats_available=40,
    )

    assert score == 0.0
    assert gap_type == GapType.OVERSUPPLY
    assert breakdown["volume_factor"] == 0.0
    assert breakdown["market_demand_factor"] == 0.0


def test_hand_computed_oversupply_low_volume() -> None:
    """Case 4: Oversupply with low volume and excess training seats.

    Hand Derivation:
    ----------------
    Similarity S = 0.50 -> Dissimilarity = 0.50
    Volume V = 4
    Volume Factor F_V = ln(5) / ln(101) = 1.60944 / 4.61512 = 0.3487
    Avg Age T = 25.0 days
    Recency Decay R = exp(-0.02 * 25.0) = exp(-0.50) = 0.6065
    Market Demand Factor W = (0.60 * 0.3487) + (0.40 * 0.6065) = 0.4518
    Final Gap Score = 100 * 0.50 * 0.4518 = 22.59
    Expected Classification = OVERSUPPLY
    """
    score, gap_type, breakdown = calculate_gap_score(
        similarity=0.50,
        volume=4,
        avg_age_days=25.0,
        seats_available=50,
    )

    assert score == 22.59
    assert gap_type == GapType.OVERSUPPLY
    assert breakdown["volume_factor"] == 0.3487
    assert breakdown["recency_decay"] == 0.6065
    assert breakdown["market_demand_factor"] == 0.4518


def test_hand_computed_emerging_skill() -> None:
    """Case 5: Emerging Skill (Recent postings requesting modern skills).

    Hand Derivation:
    ----------------
    Similarity S = 0.40 -> Dissimilarity = 0.60
    Volume V = 15
    Volume Factor F_V = ln(16) / ln(101) = 2.77259 / 4.61512 = 0.6008
    Avg Age T = 10.0 days (<= 30 days)
    Recency Decay R = exp(-0.02 * 10.0) = exp(-0.20) = 0.8187
    Market Demand Factor W = (0.60 * 0.6008) + (0.40 * 0.8187) = 0.6880
    Final Gap Score = 100 * 0.60 * 0.6880 = 41.28
    Expected Classification = EMERGING_SKILL
    """
    score, gap_type, breakdown = calculate_gap_score(
        similarity=0.40,
        volume=15,
        avg_age_days=10.0,
        seats_available=40,
    )

    assert score == 41.28
    assert gap_type == GapType.EMERGING_SKILL
    assert breakdown["volume_factor"] == 0.6008
    assert breakdown["recency_decay"] == 0.8187
    assert breakdown["market_demand_factor"] == 0.6880


@pytest.mark.skipif(not HAS_NLP, reason="NLP dependencies not installed")
def test_semantic_similarity_computation() -> None:
    """Validate SentenceTransformer cosine similarity."""
    curriculum = ["conduit wiring", "earthing", "mcb circuit breaker"]
    market_close = ["industrial conduit wiring", "earthing systems", "mcb installation"]
    market_distant = ["python programming", "django web development"]

    sim_close = scoring_service.compute_similarity(curriculum, market_close)
    sim_distant = scoring_service.compute_similarity(curriculum, market_distant)

    assert sim_close > 0.70
    assert sim_distant < 0.30
    assert sim_close > sim_distant


def test_compute_similarity_empty_inputs() -> None:
    """Verify compute_similarity returns 0.0 when either input list is empty."""
    assert scoring_service.compute_similarity([], ["conduit wiring"]) == 0.0
    assert scoring_service.compute_similarity(["conduit wiring"], []) == 0.0


def test_scoring_edge_case_fallback_branches() -> None:
    """Exercise remaining classification branches: low-similarity drift and default undersupply."""
    # Branch: sim_clamped < 0.50, low volume, low seats -> CURRICULUM_DRIFT
    _, gap_type_drift, _ = calculate_gap_score(
        similarity=0.35,
        volume=3,
        avg_age_days=45.0,
        seats_available=10,
    )
    assert gap_type_drift == GapType.CURRICULUM_DRIFT

    # Branch: else fallback -> UNDERSUPPLY
    _, gap_type_under, _ = calculate_gap_score(
        similarity=0.55,
        volume=8,
        avg_age_days=45.0,
        seats_available=15,
    )
    assert gap_type_under == GapType.UNDERSUPPLY
