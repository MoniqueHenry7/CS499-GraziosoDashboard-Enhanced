from datetime import datetime, timezone

import pytest

from animal_shelter import AnimalShelter


def test_normalize_valid_create_fields():
    result = (
        AnimalShelter
        ._normalize_mutation_fields(
            {
                "animal_id": "A100",
                "animal_type": "Dog",
                "breed": "Labrador Mix",
                "age_in_weeks": 52,
            },
            require_required_fields=True,
        )
    )

    assert result["animal_id"] == "A100"
    assert result["age_in_weeks"] == 52.0


def test_create_requires_breed():
    with pytest.raises(
        ValueError,
        match="Missing required",
    ):
        AnimalShelter._normalize_mutation_fields(
            {
                "animal_id": "A100",
                "animal_type": "Dog",
            },
            require_required_fields=True,
        )


def test_unsupported_field_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        AnimalShelter._normalize_mutation_fields(
            {
                "animal_id": "A100",
                "animal_type": "Dog",
                "breed": "Test Breed",
                "$where": "unsafe",
            },
            require_required_fields=True,
        )


def test_negative_age_is_rejected():
    with pytest.raises(
        ValueError,
        match="negative",
    ):
        AnimalShelter._normalize_mutation_fields(
            {
                "age_in_weeks": -1,
            },
            require_required_fields=False,
        )


def test_invalid_latitude_is_rejected():
    with pytest.raises(
        ValueError,
        match="location_lat",
    ):
        AnimalShelter._normalize_mutation_fields(
            {
                "location_lat": 100,
            },
            require_required_fields=False,
        )


def test_datetime_field_is_accepted():
    test_date = datetime.now(
        timezone.utc
    )

    result = (
        AnimalShelter
        ._normalize_mutation_fields(
            {
                "outcome_date": test_date,
            },
            require_required_fields=False,
        )
    )

    assert result["outcome_date"] == test_date