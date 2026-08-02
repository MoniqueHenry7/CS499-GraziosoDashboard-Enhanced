"""Tests for the Enhancement Two rescue recommendation engine.

The suite verifies profile compatibility, index construction, binary-search
age lookups, set-based candidate selection, weighted scoring, bounded
min-heap ranking, validation, caching, and protection of source records.
"""

from dataclasses import dataclass
from typing import Any

import pytest

from recommendation import RescueRecommendationEngine
from rescue_rules import RESCUE_PROFILES


TEST_PROFILES: dict[str, dict[str, Any]] = {
    "Water Rescue": {
        "breeds": (
            "Labrador Retriever",
            "Chesapeake Bay Retriever",
            "Newfoundland",
        ),
        "minimum_age_weeks": 26,
        "maximum_age_weeks": 156,
        "preferred_sex": "Intact Female",
        "preferred_outcome": "Transfer",
    },
    "Tracking": {
        "breeds": (
            "German Shepherd",
            "Bloodhound",
        ),
        "minimum_age_weeks": 20,
        "maximum_age_weeks": 300,
        "preferred_sex": "Intact Male",
        "preferred_outcome": "Transfer",
    },
}


@pytest.fixture
def animal_records() -> list[dict[str, Any]]:
    """Provide varied animal records for indexing and ranking tests."""

    return [
        {
            "animal_id": "A1",
            "name": "Aqua",
            "breed": "Labrador Retriever Mix",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 52,
            "outcome_type": "Transfer",
        },
        {
            "animal_id": "A2",
            "name": "Bay",
            "breed": "Chesapeake Bay Retriever",
            "sex_upon_outcome": "Intact Male",
            "age_upon_outcome_in_weeks": 60,
            "outcome_type": "Transfer",
        },
        {
            "animal_id": "A3",
            "name": "Cedar",
            "breed": "Poodle Mix",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 70,
            "outcome_type": "Transfer",
        },
        {
            "animal_id": "A4",
            "name": "Delta",
            "breed": "Poodle",
            "sex_upon_outcome": "Neutered Male",
            "age_upon_outcome_in_weeks": 500,
            "outcome_type": "Adoption",
        },
        {
            "animal_id": "A5",
            "name": "Echo",
            "breed": "Newfoundland",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 80,
            "outcome_type": "Adoption",
        },
        {
            "animal_id": "A6",
            "name": "Finder",
            "breed": "German Shepherd Mix",
            "sex_upon_outcome": "Intact Male",
            "age_upon_outcome_in_weeks": "100",
            "outcome_type": "Transfer",
        },
        {
            "animal_id": "A7",
            "name": "Unknown Age",
            "breed": "Bloodhound",
            "sex_upon_outcome": "Intact Male",
            "age_upon_outcome_in_weeks": "not available",
            "outcome_type": "Transfer",
        },
    ]


@pytest.fixture
def engine(
    animal_records: list[dict[str, Any]],
) -> RescueRecommendationEngine:
    """Create an engine using dictionary-based profiles."""

    return RescueRecommendationEngine(
        records=animal_records,
        rescue_profiles=TEST_PROFILES,
    )


def test_normalize_trims_case_and_repeated_spaces() -> None:
    assert (
        RescueRecommendationEngine._normalize(
            "  Labrador   Retriever MIX  "
        )
        == "labrador retriever mix"
    )


def test_normalize_none_returns_empty_string() -> None:
    assert RescueRecommendationEngine._normalize(None) == ""


def test_safe_number_converts_numeric_string() -> None:
    assert RescueRecommendationEngine._safe_number("52.5") == 52.5


def test_safe_number_returns_none_for_invalid_value() -> None:
    assert RescueRecommendationEngine._safe_number("unknown") is None


def test_normalize_profile_accepts_standard_dictionary() -> None:
    profile = RescueRecommendationEngine._normalize_profile(
        TEST_PROFILES["Water Rescue"]
    )

    assert profile["breeds"][0] == "Labrador Retriever"
    assert profile["minimum_age_weeks"] == 26.0
    assert profile["maximum_age_weeks"] == 156.0


def test_normalize_profile_accepts_alternate_dictionary_keys() -> None:
    profile = RescueRecommendationEngine._normalize_profile(
        {
            "preferred_breeds": ("Bloodhound",),
            "min_age_weeks": 20,
            "max_age_weeks": 300,
            "preferred_sex": "Intact Male",
            "preferred_outcome": "Transfer",
        }
    )

    assert profile["breeds"] == ("Bloodhound",)
    assert profile["minimum_age_weeks"] == 20.0
    assert profile["maximum_age_weeks"] == 300.0


def test_normalize_profile_accepts_dataclass_object() -> None:
    @dataclass(frozen=True)
    class Profile:
        preferred_breeds: tuple[str, ...]
        min_age_weeks: float
        max_age_weeks: float
        preferred_sex: str
        preferred_outcome: str

    profile = RescueRecommendationEngine._normalize_profile(
        Profile(
            preferred_breeds=("Newfoundland",),
            min_age_weeks=26,
            max_age_weeks=156,
            preferred_sex="Intact Female",
            preferred_outcome="Transfer",
        )
    )

    assert profile["breeds"] == ("Newfoundland",)
    assert profile["preferred_sex"] == "Intact Female"


def test_normalize_profile_rejects_missing_age_bounds() -> None:
    with pytest.raises(
        ValueError,
        match="minimum and maximum ages",
    ):
        RescueRecommendationEngine._normalize_profile(
            {
                "breeds": ("Labrador Retriever",),
                "preferred_sex": "Intact Female",
                "preferred_outcome": "Transfer",
            }
        )


def test_index_building_does_not_modify_source_records(
    animal_records: list[dict[str, Any]],
) -> None:
    RescueRecommendationEngine(
        records=animal_records,
        rescue_profiles=TEST_PROFILES,
    )

    assert all(
        "record_key" not in record
        for record in animal_records
    )


def test_index_uses_mongodb_id_as_record_key() -> None:
    engine = RescueRecommendationEngine(
        records=[
            {
                "_id": "mongo-123",
                "animal_id": "A1",
                "breed": "Labrador Retriever",
                "sex_upon_outcome": "Intact Female",
                "age_upon_outcome_in_weeks": 50,
                "outcome_type": "Transfer",
            }
        ],
        rescue_profiles=TEST_PROFILES,
    )

    assert "mongo-123" in engine.records


def test_index_creates_unique_fallback_record_keys() -> None:
    duplicate_records = [
        {"animal_id": "A1"},
        {"animal_id": "A1"},
    ]

    engine = RescueRecommendationEngine(
        records=duplicate_records,
        rescue_profiles=TEST_PROFILES,
    )

    assert set(engine.records) == {"A1:0", "A1:1"}


def test_breed_index_matches_mixed_breed_description(
    engine: RescueRecommendationEngine,
) -> None:
    assert "A1:0" in engine.breed_index["labrador retriever"]
    assert "A6:5" in engine.breed_index["german shepherd"]


def test_text_indexes_are_normalized(
    engine: RescueRecommendationEngine,
) -> None:
    assert "A1:0" in engine.sex_index["intact female"]
    assert "A1:0" in engine.outcome_index["transfer"]


def test_age_index_is_sorted_and_skips_invalid_ages(
    engine: RescueRecommendationEngine,
) -> None:
    assert engine.sorted_age_values == sorted(
        engine.sorted_age_values
    )

    assert len(engine.sorted_age_values) == 6

    assert "A7:6" not in {
        record_key
        for _, record_key in engine.sorted_age_records
    }


def test_cache_is_empty_after_initial_index_build(
    engine: RescueRecommendationEngine,
) -> None:
    assert engine.cache == {}


def test_find_age_ids_uses_inclusive_boundaries(
    engine: RescueRecommendationEngine,
) -> None:
    matching_ids = engine._find_age_ids(52, 70)

    assert matching_ids == {
        "A1:0",
        "A2:1",
        "A3:2",
    }


def test_find_age_ids_returns_empty_for_reversed_range(
    engine: RescueRecommendationEngine,
) -> None:
    assert engine._find_age_ids(100, 20) == set()


def test_find_age_ids_returns_empty_when_no_age_matches(
    engine: RescueRecommendationEngine,
) -> None:
    assert engine._find_age_ids(1000, 2000) == set()


def test_find_breed_ids_combines_multiple_breed_sets(
    engine: RescueRecommendationEngine,
) -> None:
    matching_ids = engine._find_breed_ids(
        (
            "Labrador Retriever",
            "Newfoundland",
        )
    )

    assert matching_ids == {
        "A1:0",
        "A5:4",
    }


def test_find_breed_ids_returns_empty_for_unknown_breed(
    engine: RescueRecommendationEngine,
) -> None:
    assert engine._find_breed_ids(
        ("Unknown Breed",)
    ) == set()


def test_find_candidates_returns_strict_intersection_when_sufficient(
    engine: RescueRecommendationEngine,
) -> None:
    profile = engine.rescue_profiles["Water Rescue"]

    assert engine._find_candidates(
        profile,
        requested_count=1,
    ) == {"A1:0"}


def test_find_candidates_uses_broader_set_and_preserves_outcome(
    engine: RescueRecommendationEngine,
) -> None:
    profile = engine.rescue_profiles["Water Rescue"]

    candidates = engine._find_candidates(
        profile,
        requested_count=5,
    )

    assert "A1:0" in candidates
    assert "A2:1" in candidates
    assert "A3:2" in candidates
    assert "A5:4" not in candidates


def test_find_candidates_falls_back_to_all_records() -> None:
    profile = {
        "No Match": {
            "breeds": ("Nonexistent Breed",),
            "minimum_age_weeks": 2000,
            "maximum_age_weeks": 3000,
            "preferred_sex": "Unknown Sex",
            "preferred_outcome": "Unknown Outcome",
        }
    }

    records = [
        {
            "animal_id": "A1",
            "breed": "Poodle",
            "sex_upon_outcome": "Neutered Male",
            "age_upon_outcome_in_weeks": 50,
            "outcome_type": "Adoption",
        }
    ]

    engine = RescueRecommendationEngine(
        records,
        profile,
    )

    candidates = engine._find_candidates(
        engine.rescue_profiles["No Match"],
        requested_count=3,
    )

    assert candidates == {"A1:0"}


def test_calculate_score_returns_100_for_exact_match(
    engine: RescueRecommendationEngine,
) -> None:
    score, reasons = engine._calculate_score(
        engine.records["A1:0"],
        engine.rescue_profiles["Water Rescue"],
    )

    assert score == 100.0
    assert len(reasons) == 4


def test_calculate_score_awards_partial_age_credit(
    engine: RescueRecommendationEngine,
) -> None:
    record = {
        "breed": "Poodle",
        "sex_upon_outcome": "Neutered Male",
        "age_upon_outcome_in_weeks": 166,
        "outcome_type": "Adoption",
    }

    score, reasons = engine._calculate_score(
        record,
        engine.rescue_profiles["Water Rescue"],
    )

    assert score == 22.5
    assert reasons == ["Age near preferred range"]


def test_calculate_score_handles_missing_age(
    engine: RescueRecommendationEngine,
) -> None:
    score, reasons = engine._calculate_score(
        engine.records["A7:6"],
        engine.rescue_profiles["Tracking"],
    )

    assert score == 75.0
    assert "Age within preferred range" not in reasons
    assert "Age near preferred range" not in reasons


def test_calculate_score_returns_zero_when_nothing_matches(
    engine: RescueRecommendationEngine,
) -> None:
    record = {
        "breed": "Poodle",
        "sex_upon_outcome": "Neutered Male",
        "age_upon_outcome_in_weeks": 1000,
        "outcome_type": "Adoption",
    }

    score, reasons = engine._calculate_score(
        record,
        engine.rescue_profiles["Water Rescue"],
    )

    assert score == 0.0
    assert reasons == []


def test_select_top_candidates_respects_limit(
    engine: RescueRecommendationEngine,
) -> None:
    results = engine._select_top_candidates(
        candidate_ids=set(engine.records),
        profile=engine.rescue_profiles["Water Rescue"],
        limit=2,
    )

    assert len(results) == 2


def test_select_top_candidates_returns_descending_scores_and_ranks(
    engine: RescueRecommendationEngine,
) -> None:
    results = engine._select_top_candidates(
        candidate_ids=set(engine.records),
        profile=engine.rescue_profiles["Water Rescue"],
        limit=4,
    )

    scores = [
        record["match_score"]
        for record in results
    ]

    ranks = [
        record["recommendation_rank"]
        for record in results
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )

    assert ranks == [
        1,
        2,
        3,
        4,
    ]


def test_select_top_candidates_uses_deterministic_tie_breaker() -> None:
    records = [
        {
            "animal_id": "A",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 52,
            "outcome_type": "Transfer",
        },
        {
            "animal_id": "B",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 52,
            "outcome_type": "Transfer",
        },
    ]

    engine = RescueRecommendationEngine(
        records,
        TEST_PROFILES,
    )

    results = engine._select_top_candidates(
        candidate_ids=set(engine.records),
        profile=engine.rescue_profiles["Water Rescue"],
        limit=2,
    )

    assert [
        record["record_key"]
        for record in results
    ] == [
        "A:0",
        "B:1",
    ]


def test_recommend_rejects_unknown_profile(
    engine: RescueRecommendationEngine,
) -> None:
    with pytest.raises(
        ValueError,
        match="Unknown rescue profile",
    ):
        engine.recommend("Unknown Rescue")


def test_recommend_rejects_zero_limit(
    engine: RescueRecommendationEngine,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be positive",
    ):
        engine.recommend(
            "Water Rescue",
            limit=0,
        )


def test_recommend_rejects_negative_limit(
    engine: RescueRecommendationEngine,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be positive",
    ):
        engine.recommend(
            "Water Rescue",
            limit=-1,
        )


def test_recommend_rejects_noninteger_limit(
    engine: RescueRecommendationEngine,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be positive",
    ):
        engine.recommend(
            "Water Rescue",
            limit=2.5,  # type: ignore[arg-type]
        )


def test_recommend_returns_ranked_fields_and_protected_cache(
    engine: RescueRecommendationEngine,
    animal_records: list[dict[str, Any]],
) -> None:
    first_results = engine.recommend(
        "Water Rescue",
        limit=3,
    )

    assert 1 <= len(first_results) <= 3

    assert [
        record["match_score"]
        for record in first_results
    ] == sorted(
        (
            record["match_score"]
            for record in first_results
        ),
        reverse=True,
    )

    assert all(
        {
            "recommendation_rank",
            "match_score",
            "match_reasons",
        }.issubset(record)
        for record in first_results
    )

    assert (
        "Water Rescue",
        3,
    ) in engine.cache

    original_name = first_results[0]["name"]

    first_results[0]["name"] = (
        "Changed Outside Cache"
    )

    second_results = engine.recommend(
        "Water Rescue",
        limit=3,
    )

    assert (
        second_results[0]["name"]
        == original_name
    )

    assert all(
        "record_key" not in source_record
        for source_record in animal_records
    )


def test_engine_accepts_dashboard_rescue_profiles() -> None:
    """The engine should accept RescueProfile dataclass objects."""

    engine = RescueRecommendationEngine(
        records=[],
        rescue_profiles=RESCUE_PROFILES,
    )

    assert set(engine.rescue_profiles) == set(
        RESCUE_PROFILES
    )

    water_profile = engine.rescue_profiles[
        "Water Rescue"
    ]

    assert water_profile["breeds"] == (
        "Labrador Retriever",
        "Chesapeake Bay Retriever",
        "Newfoundland",
    )

    assert (
        water_profile["minimum_age_weeks"]
        == 26.0
    )

    assert (
        water_profile["maximum_age_weeks"]
        == 156.0
    )

    assert (
        water_profile["preferred_sex"]
        == "Intact Female"
    )

    assert (
        water_profile["preferred_outcome"]
        == "Transfer"
    )