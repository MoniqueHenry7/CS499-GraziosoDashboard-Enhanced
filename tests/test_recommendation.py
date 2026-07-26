"""Unit tests for the rescue recommendation engine.

These tests use controlled sample records and do not require MongoDB,
Dash, or the full animal shelter dataset.
"""

import pytest

from recommendation import RescueRecommendationEngine


# ---------------------------------------------------------------------------
# Controlled rescue profiles used only for unit testing
# ---------------------------------------------------------------------------

SAMPLE_PROFILES = {
    "Water Rescue": {
        "breeds": (
            "Labrador Retriever",
            "Chesapeake Bay Retriever",
            "Newfoundland",
        ),
        "preferred_sex": "Intact Female",
        "minimum_age_weeks": 26,
        "maximum_age_weeks": 156,
        "preferred_outcome": "Transfer",
    },

    "Mountain or Wilderness Rescue": {
        "breeds": (
            "German Shepherd",
            "Alaskan Malamute",
            "Old English Sheepdog",
            "Siberian Husky",
            "Rottweiler",
        ),
        "preferred_sex": "Intact Male",
        "minimum_age_weeks": 26,
        "maximum_age_weeks": 156,
        "preferred_outcome": "Transfer",
    },

    "Disaster or Individual Tracking": {
        "breeds": (
            "Doberman Pinscher",
            "German Shepherd",
            "Golden Retriever",
            "Bloodhound",
            "Rottweiler",
        ),
        "preferred_sex": "Intact Male",
        "minimum_age_weeks": 20,
        "maximum_age_weeks": 300,
        "preferred_outcome": "Transfer",
    },
}


# ---------------------------------------------------------------------------
# Controlled animal records used for testing
# ---------------------------------------------------------------------------

SAMPLE_RECORDS = [
    {
        "animal_id": "A1",
        "name": "Max",
        "breed": "Labrador Retriever Mix",
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": 52,
        "outcome_type": "Transfer",
    },
    {
        "animal_id": "A2",
        "name": "Luna",
        "breed": "Newfoundland Mix",
        "sex_upon_outcome": "Spayed Female",
        "age_upon_outcome_in_weeks": 60,
        "outcome_type": "Transfer",
    },
    {
        "animal_id": "A3",
        "name": "Rocky",
        "breed": "Chihuahua Shorthair Mix",
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": 400,
        "outcome_type": "Adoption",
    },
    {
        "animal_id": "A4",
        "name": "Scout",
        "breed": "German Shepherd Mix",
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": 75,
        "outcome_type": "Transfer",
    },
    {
        "animal_id": "A5",
        "name": "Unknown",
        "breed": "Labrador Retriever Mix",
        "sex_upon_outcome": None,
        "age_upon_outcome_in_weeks": None,
        "outcome_type": "Transfer",
    },
]


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_records():
    """Return fresh copies of the sample animal records."""

    return [
        dict(record)
        for record in SAMPLE_RECORDS
    ]


@pytest.fixture
def sample_profiles():
    """Return the controlled rescue profiles."""

    return SAMPLE_PROFILES


@pytest.fixture
def engine(sample_records, sample_profiles):
    """Create a recommendation engine for each test."""

    return RescueRecommendationEngine(
        records=sample_records,
        rescue_profiles=sample_profiles,
    )


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------

def animal_ids_from_keys(engine, record_keys):
    """Convert internal record keys into animal IDs."""

    return {
        engine.records[record_key]["animal_id"]
        for record_key in record_keys
    }


# ---------------------------------------------------------------------------
# Dictionary and index construction tests
# ---------------------------------------------------------------------------

def test_engine_builds_complete_record_index(engine):
    """Every input record should be stored in the main dictionary."""

    assert len(engine.records) == len(SAMPLE_RECORDS)


def test_record_keys_are_unique(engine):
    """Each record should receive a unique internal key."""

    record_keys = list(engine.records.keys())

    assert len(record_keys) == len(set(record_keys))


def test_engine_builds_labrador_breed_index(engine):
    """The breed dictionary should contain both Labrador records."""

    labrador_keys = engine.breed_index[
        "labrador retriever"
    ]

    animal_ids = animal_ids_from_keys(
        engine,
        labrador_keys,
    )

    assert animal_ids == {"A1", "A5"}


def test_engine_builds_newfoundland_breed_index(engine):
    """The breed index should contain the Newfoundland record."""

    newfoundland_keys = engine.breed_index[
        "newfoundland"
    ]

    animal_ids = animal_ids_from_keys(
        engine,
        newfoundland_keys,
    )

    assert animal_ids == {"A2"}


def test_engine_builds_sex_index(engine):
    """The sex dictionary should index matching animal records."""

    male_keys = engine.sex_index["intact male"]

    animal_ids = animal_ids_from_keys(
        engine,
        male_keys,
    )

    assert animal_ids == {"A3", "A4"}


def test_engine_builds_outcome_index(engine):
    """The outcome dictionary should index transfer records."""

    transfer_keys = engine.outcome_index["transfer"]

    animal_ids = animal_ids_from_keys(
        engine,
        transfer_keys,
    )

    assert animal_ids == {"A1", "A2", "A4", "A5"}


def test_engine_sorts_age_values(engine):
    """Valid age values should be stored in ascending order."""

    assert engine.sorted_age_values == [
        52.0,
        60.0,
        75.0,
        400.0,
    ]


def test_missing_age_is_not_added_to_sorted_age_index(engine):
    """Records with missing ages should not break age indexing."""

    indexed_animal_ids = {
        engine.records[record_key]["animal_id"]
        for _, record_key in engine.sorted_age_records
    }

    assert "A5" not in indexed_animal_ids


# ---------------------------------------------------------------------------
# Normalization and safe-conversion tests
# ---------------------------------------------------------------------------

def test_normalize_removes_extra_spaces_and_case_differences():
    """Text normalization should produce consistent lookup values."""

    normalized = RescueRecommendationEngine._normalize(
        "  INTACT    Female  "
    )

    assert normalized == "intact female"


def test_safe_number_converts_valid_number():
    """Numeric strings should be converted to floating-point values."""

    result = RescueRecommendationEngine._safe_number("52")

    assert result == 52.0


def test_safe_number_returns_none_for_invalid_value():
    """Invalid age values should return None instead of crashing."""

    result = RescueRecommendationEngine._safe_number(
        "unknown"
    )

    assert result is None


# ---------------------------------------------------------------------------
# Binary-search tests
# ---------------------------------------------------------------------------

def test_binary_age_search_returns_matching_records(engine):
    """Binary search should return animals within the age range."""

    matching_keys = engine._find_age_ids(
        minimum_age=26,
        maximum_age=156,
    )

    animal_ids = animal_ids_from_keys(
        engine,
        matching_keys,
    )

    assert animal_ids == {"A1", "A2", "A4"}


def test_binary_age_search_uses_inclusive_boundaries():
    """Animals exactly on minimum and maximum ages should match."""

    boundary_records = [
        {
            "animal_id": "LOW",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 26,
            "outcome_type": "Transfer",
        },
        {
            "animal_id": "HIGH",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 156,
            "outcome_type": "Transfer",
        },
        {
            "animal_id": "BELOW",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 25,
            "outcome_type": "Transfer",
        },
        {
            "animal_id": "ABOVE",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 157,
            "outcome_type": "Transfer",
        },
    ]

    boundary_engine = RescueRecommendationEngine(
        records=boundary_records,
        rescue_profiles=SAMPLE_PROFILES,
    )

    matching_keys = boundary_engine._find_age_ids(
        minimum_age=26,
        maximum_age=156,
    )

    animal_ids = animal_ids_from_keys(
        boundary_engine,
        matching_keys,
    )

    assert animal_ids == {"LOW", "HIGH"}


def test_binary_age_search_returns_empty_set_when_no_match(engine):
    """An unmatched age range should return an empty set."""

    matching_keys = engine._find_age_ids(
        minimum_age=500,
        maximum_age=600,
    )

    assert matching_keys == set()


# ---------------------------------------------------------------------------
# Set-operation and candidate-selection tests
# ---------------------------------------------------------------------------

def test_breed_lookup_combines_multiple_breed_sets(engine):
    """Breed lookup should use a set union for acceptable breeds."""

    matching_keys = engine._find_breed_ids(
        (
            "Labrador Retriever",
            "Newfoundland",
        )
    )

    animal_ids = animal_ids_from_keys(
        engine,
        matching_keys,
    )

    assert animal_ids == {"A1", "A2", "A5"}


def test_strict_candidate_intersection_finds_perfect_match(engine):
    """Set intersection should identify the perfect Water Rescue match."""

    water_profile = SAMPLE_PROFILES["Water Rescue"]

    matching_keys = engine._find_candidates(
        profile=water_profile,
        requested_count=1,
    )

    animal_ids = animal_ids_from_keys(
        engine,
        matching_keys,
    )

    assert animal_ids == {"A1"}


def test_broader_candidate_pool_is_used_when_needed(engine):
    """The engine should broaden the search when strict matches are limited."""

    water_profile = SAMPLE_PROFILES["Water Rescue"]

    matching_keys = engine._find_candidates(
        profile=water_profile,
        requested_count=10,
    )

    animal_ids = animal_ids_from_keys(
        engine,
        matching_keys,
    )

    assert "A1" in animal_ids
    assert "A2" in animal_ids
    assert "A4" in animal_ids
    assert "A5" in animal_ids

    # A3 is excluded because its outcome is Adoption.
    assert "A3" not in animal_ids


# ---------------------------------------------------------------------------
# Weighted-scoring tests
# ---------------------------------------------------------------------------

def test_perfect_water_rescue_match_receives_100_points(engine):
    """A record matching every requirement should receive 100 points."""

    water_profile = SAMPLE_PROFILES["Water Rescue"]
    perfect_record = SAMPLE_RECORDS[0]

    score, reasons = engine._calculate_score(
        record=perfect_record,
        profile=water_profile,
    )

    assert score == 100
    assert "Preferred rescue breed" in reasons
    assert "Preferred sex" in reasons
    assert "Age within preferred range" in reasons
    assert "Preferred outcome type" in reasons


def test_partial_water_rescue_match_receives_expected_score(engine):
    """Luna should receive breed, age, and outcome points."""

    water_profile = SAMPLE_PROFILES["Water Rescue"]
    partial_record = SAMPLE_RECORDS[1]

    score, reasons = engine._calculate_score(
        record=partial_record,
        profile=water_profile,
    )

    # Breed 40 + age 25 + outcome 15 = 80.
    assert score == 80
    assert "Preferred rescue breed" in reasons
    assert "Age within preferred range" in reasons
    assert "Preferred outcome type" in reasons
    assert "Preferred sex" not in reasons


def test_missing_values_do_not_crash_scoring(engine):
    """Missing sex and age values should be handled safely."""

    water_profile = SAMPLE_PROFILES["Water Rescue"]
    incomplete_record = SAMPLE_RECORDS[4]

    score, reasons = engine._calculate_score(
        record=incomplete_record,
        profile=water_profile,
    )

    # Breed 40 + outcome 15 = 55.
    assert score == 55
    assert "Preferred rescue breed" in reasons
    assert "Preferred outcome type" in reasons


# ---------------------------------------------------------------------------
# Heap and ranking tests
# ---------------------------------------------------------------------------

def test_recommendations_are_ranked_highest_to_lowest(engine):
    """Recommendation scores should be returned in descending order."""

    results = engine.recommend(
        rescue_type="Water Rescue",
        limit=10,
    )

    scores = [
        result["match_score"]
        for result in results
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_perfect_water_rescue_match_ranks_first(engine):
    """The perfect Water Rescue candidate should rank first."""

    results = engine.recommend(
        rescue_type="Water Rescue",
        limit=10,
    )

    assert results[0]["animal_id"] == "A1"
    assert results[0]["recommendation_rank"] == 1
    assert results[0]["match_score"] == 100


def test_mountain_rescue_match_ranks_first(engine):
    """The German Shepherd should rank first for mountain rescue."""

    results = engine.recommend(
        rescue_type="Mountain or Wilderness Rescue",
        limit=10,
    )

    assert results[0]["animal_id"] == "A4"
    assert results[0]["match_score"] == 100


def test_disaster_tracking_match_ranks_first(engine):
    """The German Shepherd should rank first for tracking rescue."""

    results = engine.recommend(
        rescue_type="Disaster or Individual Tracking",
        limit=10,
    )

    assert results[0]["animal_id"] == "A4"
    assert results[0]["match_score"] == 100


def test_heap_respects_requested_limit(engine):
    """The bounded heap should not return more than the requested limit."""

    results = engine.recommend(
        rescue_type="Water Rescue",
        limit=2,
    )

    assert len(results) == 2


def test_top_two_water_rescue_candidates_are_correct(engine):
    """The heap should retain the two highest-scoring Water candidates."""

    results = engine.recommend(
        rescue_type="Water Rescue",
        limit=2,
    )

    returned_ids = [
        result["animal_id"]
        for result in results
    ]

    assert returned_ids == ["A1", "A2"]


def test_recommendation_ranks_are_sequential(engine):
    """Returned recommendation ranks should begin at one."""

    results = engine.recommend(
        rescue_type="Water Rescue",
        limit=4,
    )

    ranks = [
        result["recommendation_rank"]
        for result in results
    ]

    assert ranks == list(
        range(1, len(results) + 1)
    )


def test_recommendations_include_match_reasons(engine):
    """Every returned recommendation should explain its score."""

    results = engine.recommend(
        rescue_type="Water Rescue",
        limit=4,
    )

    for result in results:
        assert "match_reasons" in result
        assert isinstance(
            result["match_reasons"],
            str,
        )


# ---------------------------------------------------------------------------
# Validation and error-handling tests
# ---------------------------------------------------------------------------

def test_unknown_rescue_type_raises_value_error(engine):
    """An invalid rescue type should raise a clear error."""

    with pytest.raises(
        ValueError,
        match="Unknown rescue profile",
    ):
        engine.recommend(
            rescue_type="Unknown Rescue",
            limit=10,
        )


def test_zero_limit_raises_value_error(engine):
    """A zero recommendation limit should be rejected."""

    with pytest.raises(
        ValueError,
        match="positive",
    ):
        engine.recommend(
            rescue_type="Water Rescue",
            limit=0,
        )


def test_negative_limit_raises_value_error(engine):
    """A negative recommendation limit should be rejected."""

    with pytest.raises(
        ValueError,
        match="positive",
    ):
        engine.recommend(
            rescue_type="Water Rescue",
            limit=-5,
        )


# ---------------------------------------------------------------------------
# Cache and consistency tests
# ---------------------------------------------------------------------------

def test_repeated_request_returns_same_results(engine):
    """Cached and uncached requests should return equivalent results."""

    first_results = engine.recommend(
        rescue_type="Water Rescue",
        limit=3,
    )

    second_results = engine.recommend(
        rescue_type="Water Rescue",
        limit=3,
    )

    assert first_results == second_results


def test_recommendation_request_is_added_to_cache(engine):
    """Completed recommendations should be stored by rescue type and limit."""

    engine.recommend(
        rescue_type="Water Rescue",
        limit=3,
    )

    assert ("Water Rescue", 3) in engine.cache


def test_cached_results_are_returned_as_copies(engine):
    """Changing a returned result should not corrupt cached data."""

    first_results = engine.recommend(
        rescue_type="Water Rescue",
        limit=3,
    )

    first_results[0]["name"] = "Changed Name"

    second_results = engine.recommend(
        rescue_type="Water Rescue",
        limit=3,
    )

    assert second_results[0]["name"] == "Max"


def test_different_limits_create_different_cache_entries(engine):
    """Each top-k request should have its own cache entry."""

    engine.recommend(
        rescue_type="Water Rescue",
        limit=2,
    )

    engine.recommend(
        rescue_type="Water Rescue",
        limit=4,
    )

    assert ("Water Rescue", 2) in engine.cache
    assert ("Water Rescue", 4) in engine.cache