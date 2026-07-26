"""
test_rescue_rules.py
--------------------
Unit tests for the rescue recommendation logic used by the
Grazioso Salvare Rescue Match Recommendation Dashboard.

These tests verify:
- A perfect rescue candidate receives the expected 100-point score.
- Mixed-breed descriptions are recognized correctly.
- Partial matches receive appropriate scores.
- Reset mode does not rank candidates.
- Match classifications follow the defined thresholds.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

import pytest

from rescue_rules import (
    breed_matches,
    classify_match,
    score_animal,
)


def test_perfect_water_rescue_candidate_scores_100():
    """
    A candidate matching every Water Rescue criterion should receive
    the maximum recommendation score of 100.
    """

    animal = {
        "animal_id": "TEST001",
        "name": "Daisy",
        "breed": "Labrador Retriever Mix",
        "age_upon_outcome_in_weeks": 100,
        "sex_upon_outcome": "Intact Female",
        "outcome_type": "Transfer",
    }

    result = score_animal(
        animal,
        "Water Rescue",
    )

    assert result.score == 100
    assert result.level == "Strong Match"

    assert (
        "Labrador Retriever"
        in result.explanation
    )


def test_mixed_breed_description_is_recognized():
    """
    A mixed-breed description should still match a preferred breed.

    This tests the improved logic that uses normalized breed matching
    rather than requiring exact string equality.
    """

    actual_breed = (
        "German Shepherd/Labrador Retriever"
    )

    preferred_breeds = (
        "Labrador Retriever",
        "Chesapeake Bay Retriever",
        "Newfoundland",
    )

    result = breed_matches(
        actual_breed,
        preferred_breeds,
    )

    assert result is True


def test_nonpreferred_breed_does_not_match():
    """
    A breed that is not included in the preferred rescue breeds should
    not receive a breed match.
    """

    result = breed_matches(
        "Chihuahua Shorthair Mix",
        (
            "Labrador Retriever",
            "Chesapeake Bay Retriever",
            "Newfoundland",
        ),
    )

    assert result is False


def test_partial_candidate_receives_partial_match():
    """
    A candidate matching only the preferred breed should receive
    40 points and be classified as a Partial Match.
    """

    animal = {
        "animal_id": "TEST002",
        "name": "Scout",
        "breed": "Labrador Retriever Mix",
        "age_upon_outcome_in_weeks": 400,
        "sex_upon_outcome": "Neutered Male",
        "outcome_type": "Adoption",
    }

    result = score_animal(
        animal,
        "Water Rescue",
    )

    assert result.score == 40
    assert result.level == "Partial Match"


def test_reset_mode_does_not_rank_animal():
    """
    Reset mode should preserve general browsing behavior rather than
    assigning a rescue recommendation score.
    """

    animal = {
        "animal_id": "TEST003",
        "name": "Daisy",
        "breed": "Labrador Retriever",
        "age_upon_outcome_in_weeks": 100,
        "sex_upon_outcome": "Intact Female",
        "outcome_type": "Transfer",
    }

    result = score_animal(
        animal,
        "Reset",
    )

    assert result.score == 0
    assert result.level == "Not Ranked"


def test_invalid_rescue_type_is_rejected():
    """
    Unsupported rescue categories should be rejected.
    """

    animal = {
        "animal_id": "TEST004",
        "breed": "Labrador Retriever",
        "age_upon_outcome_in_weeks": 100,
        "sex_upon_outcome": "Intact Female",
        "outcome_type": "Transfer",
    }

    with pytest.raises(
        ValueError,
        match="Unsupported rescue type",
    ):

        score_animal(
            animal,
            "Invalid Rescue Type",
        )


@pytest.mark.parametrize(
    "score, expected_level",
    [
        (100, "Strong Match"),
        (80, "Strong Match"),
        (79, "Good Match"),
        (55, "Good Match"),
        (54, "Partial Match"),
        (40, "Partial Match"),
        (39, "Low Match"),
        (0, "Low Match"),
    ],
)
def test_match_classification_thresholds(
    score,
    expected_level,
):
    """
    Verify the boundaries between recommendation classifications.
    """

    assert (
        classify_match(score)
        == expected_level
    )
