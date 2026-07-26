"""
test_dashboard_service.py
-------------------------
Unit tests for the DashboardService business-logic layer used by the
Grazioso Salvare Rescue Match Recommendation Dashboard.

A lightweight fake shelter object is used so these tests do not require
a live MongoDB server.

These tests verify:
- Dog-only data retrieval.
- Rescue recommendation scoring and ranking.
- Breed and outcome filtering.
- Age-range filtering and validation.
- Rescue-type validation.
- Reset behavior.
- Safe coordinate validation.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

import pytest

from dashboard_service import DashboardService


class FakeAnimalShelter:
    """
    Simple test double that provides the read() method expected by
    DashboardService.

    This allows the service layer to be tested independently from MongoDB.
    """

    def __init__(self, records):
        self.records = records

    def read(self, query=None):
        """
        Return predictable test records.

        The fake implementation supports the dog-only query used by
        DashboardService.load_animals().
        """

        query = query or {}

        if query.get("animal_type") == "Dog":

            return [
                record.copy()
                for record in self.records
                if record.get("animal_type") == "Dog"
            ]

        return [
            record.copy()
            for record in self.records
        ]


@pytest.fixture
def sample_records():
    """
    Create a small predictable dataset for service tests.
    """

    return [
        # Perfect Water Rescue candidate.
        {
            "animal_id": "A001",
            "animal_type": "Dog",
            "name": "Daisy",
            "breed": "Labrador Retriever Mix",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 100,
            "outcome_type": "Transfer",
            "location_lat": 30.30,
            "location_long": -97.70,
        },

        # Matches age, sex, and outcome, but not preferred Water breed.
        {
            "animal_id": "A002",
            "animal_type": "Dog",
            "name": "Bella",
            "breed": "Chihuahua Shorthair Mix",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 100,
            "outcome_type": "Transfer",
            "location_lat": 30.31,
            "location_long": -97.71,
        },

        # Matches Water Rescue breed only.
        {
            "animal_id": "A003",
            "animal_type": "Dog",
            "name": "Scout",
            "breed": "Labrador Retriever Mix",
            "sex_upon_outcome": "Neutered Male",
            "age_upon_outcome_in_weeks": 400,
            "outcome_type": "Adoption",
            "location_lat": 30.32,
            "location_long": -97.72,
        },

        # Cat record should not appear in the default dog dashboard.
        {
            "animal_id": "C001",
            "animal_type": "Cat",
            "name": "Whiskers",
            "breed": "Domestic Shorthair Mix",
            "sex_upon_outcome": "Neutered Male",
            "age_upon_outcome_in_weeks": 50,
            "outcome_type": "Adoption",
            "location_lat": 30.33,
            "location_long": -97.73,
        },
    ]


@pytest.fixture
def service(sample_records):
    """
    Create a DashboardService using the fake shelter.
    """

    shelter = FakeAnimalShelter(
        sample_records
    )

    return DashboardService(
        shelter
    )


def test_load_animals_returns_dogs_only(
    service,
):
    """
    DashboardService should retrieve dog records only by default.
    """

    frame = service.load_animals()

    assert len(frame) == 3

    assert set(
        frame["animal_type"]
    ) == {
        "Dog"
    }


def test_water_rescue_ranks_best_candidate_first(
    service,
):
    """
    Daisy matches all Water Rescue criteria and should receive 100 points
    and appear first in the ranked results.
    """

    frame = service.filter_and_rank(
        rescue_type="Water Rescue"
    )

    assert not frame.empty

    assert (
        frame.iloc[0]["animal_id"]
        == "A001"
    )

    assert (
        frame.iloc[0]["match_score"]
        == 100
    )

    assert (
        frame.iloc[0]["match_level"]
        == "Strong Match"
    )


def test_breed_filter_narrows_results(
    service,
):
    """
    Selecting an exact breed description should narrow the displayed
    candidate set.
    """

    frame = service.filter_and_rank(
        rescue_type="Water Rescue",
        breed="Labrador Retriever Mix",
    )

    assert len(frame) == 2

    assert set(
        frame["animal_id"]
    ) == {
        "A001",
        "A003",
    }


def test_breed_and_outcome_filters_work_together(
    service,
):
    """
    Breed and outcome filters should work together.
    """

    frame = service.filter_and_rank(
        rescue_type="Water Rescue",
        breed="Labrador Retriever Mix",
        outcome_type="Transfer",
    )

    assert len(frame) == 1

    assert (
        frame.iloc[0]["animal_id"]
        == "A001"
    )


def test_age_filter_narrows_results(
    service,
):
    """
    Age filtering should retain only animals inside the selected range.
    """

    frame = service.filter_and_rank(
        rescue_type="Water Rescue",
        age_range=[
            26,
            156,
        ],
    )

    assert len(frame) == 2

    assert set(
        frame["animal_id"]
    ) == {
        "A001",
        "A002",
    }


def test_invalid_age_range_is_rejected(
    service,
):
    """
    A minimum age greater than the maximum age should raise ValueError.
    """

    with pytest.raises(
        ValueError,
        match="Minimum age",
    ):

        service.filter_and_rank(
            rescue_type="Water Rescue",
            age_range=[
                500,
                100,
            ],
        )


def test_negative_age_range_is_rejected(
    service,
):
    """
    Negative age values should not be accepted.
    """

    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):

        service.filter_and_rank(
            rescue_type="Water Rescue",
            age_range=[
                -10,
                100,
            ],
        )


def test_invalid_rescue_type_is_rejected(
    service,
):
    """
    An unsupported rescue category should be rejected.
    """

    with pytest.raises(
        ValueError,
        match="Unsupported rescue type",
    ):

        service.filter_and_rank(
            rescue_type=(
                "Unknown Rescue Profile"
            )
        )


def test_reset_mode_does_not_rank_animals(
    service,
):
    """
    Reset mode should preserve general browsing without recommendation
    scoring.
    """

    frame = service.filter_and_rank(
        rescue_type="Reset"
    )

    assert not frame.empty

    assert set(
        frame["match_level"]
    ) == {
        "Not Ranked"
    }

    assert set(
        frame["match_score"]
    ) == {
        0
    }


def test_top_candidate_returns_best_match(
    service,
):
    """
    top_candidate() should return the first/highest-ranked rescue match.
    """

    frame = service.filter_and_rank(
        rescue_type="Water Rescue"
    )

    candidate = service.top_candidate(
        frame
    )

    assert candidate is not None

    assert (
        candidate["animal_id"]
        == "A001"
    )

    assert (
        candidate["match_score"]
        == 100
    )


def test_valid_coordinates_are_accepted(
    service,
):
    """
    Valid latitude and longitude should be returned as a tuple.
    """

    animal = {
        "location_lat": 30.30,
        "location_long": -97.70,
    }

    coordinates = (
        service.valid_coordinates(
            animal
        )
    )

    assert coordinates == (
        30.30,
        -97.70,
    )


def test_invalid_coordinates_are_rejected(
    service,
):
    """
    Coordinates outside valid geographic ranges should be rejected.
    """

    animal = {
        "location_lat": 120,
        "location_long": -250,
    }

    coordinates = (
        service.valid_coordinates(
            animal
        )
    )

    assert coordinates is None


def test_table_columns_define_numeric_fields():
    """
    Numeric DataTable fields should be explicitly identified so native
    Dash filtering performs numeric rather than text comparisons.
    """

    columns = DashboardService.table_columns(
        include_recommendation_fields=True
    )

    column_types = {
        column["id"]: column["type"]
        for column in columns
    }

    assert (
        column_types[
            "age_upon_outcome_in_weeks"
        ]
        == "numeric"
    )

    assert (
        column_types[
            "match_score"
        ]
        == "numeric"
    )