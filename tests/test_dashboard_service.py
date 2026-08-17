"""
test_dashboard_service.py
-------------------------
Unit tests for the DashboardService used by the enhanced Grazioso
Salvare Rescue Match Recommendation Dashboard.

Enhancement Three updates the FakeAnimalShelter test double to support:

- Database-side filtering
- Field compatibility for normalized age data
- Sorting and pagination
- Distinct-value queries
- Age-bound aggregation

The tests continue verifying the behavior completed during the Software
Engineering and Algorithms and Data Structures enhancements.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Databases
"""

from typing import Any

import pytest

from dashboard_service import DashboardService
from rescue_rules import RESET_RESCUE_TYPE


# ----------------------------------------------------------------------
# FAKE DATABASE SERVICE
# ----------------------------------------------------------------------


class FakeAnimalShelter:
    """
    In-memory test double for the Enhancement Three database interface.

    This class simulates the AnimalShelter methods used by
    DashboardService without connecting to a live MongoDB server.
    """

    def __init__(
        self,
        records: list[dict[str, Any]],
    ) -> None:
        """
        Store independent copies of the supplied test records.

        Copying the records prevents the recommendation engine or service
        from modifying the original fixture data.
        """

        self.records = [
            record.copy()
            for record in records
        ]

    @staticmethod
    def _age_value(
        record: dict[str, Any],
    ) -> Any:
        """
        Return the normalized or legacy age value.

        Enhancement Three stores age as age_in_weeks. The dashboard
        continues using age_upon_outcome_in_weeks for compatibility.
        """

        return record.get(
            "age_in_weeks",
            record.get(
                "age_upon_outcome_in_weeks"
            ),
        )

    def read(
        self,
        query: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Preserve the original fake CRUD read interface.

        This compatibility method remains available for older tests even
        though DashboardService now uses find_animals_page().
        """

        query = query or {}

        return [
            record.copy()
            for record in self.records
            if all(
                record.get(field) == value
                for field, value in query.items()
            )
        ]

    def find_animals_page(
        self,
        *,
        animal_type: str | None = "Dog",
        breed: str | None = None,
        outcome_type: str | None = None,
        sex_upon_outcome: str | None = None,
        age_range: (
            list[float]
            | tuple[float, float]
            | None
        ) = None,
        page: int = 1,
        page_size: int = 25,
        sort_field: str = "animal_id",
        sort_direction: int = 1,
    ) -> dict[str, Any]:
        """
        Filter, sort, and paginate records like AnimalShelter.

        The fake performs the operations in memory while returning the
        same response structure as the production database method.
        """

        filtered_records: list[
            dict[str, Any]
        ] = []

        for source_record in self.records:
            record = source_record.copy()

            if (
                animal_type is not None
                and record.get(
                    "animal_type"
                )
                != animal_type
            ):
                continue

            if (
                breed is not None
                and record.get(
                    "breed"
                )
                != breed
            ):
                continue

            if (
                outcome_type is not None
                and record.get(
                    "outcome_type"
                )
                != outcome_type
            ):
                continue

            if (
                sex_upon_outcome is not None
                and record.get(
                    "sex_upon_outcome"
                )
                != sex_upon_outcome
            ):
                continue

            age_value = self._age_value(
                record
            )

            if age_range is not None:
                minimum_age = float(
                    age_range[0]
                )

                maximum_age = float(
                    age_range[1]
                )

                if age_value is None:
                    continue

                numeric_age = float(
                    age_value
                )

                if not (
                    minimum_age
                    <= numeric_age
                    <= maximum_age
                ):
                    continue

            # Return both age-field names to simulate the production
            # projection and its dashboard compatibility field.
            record[
                "age_in_weeks"
            ] = age_value

            record[
                "age_upon_outcome_in_weeks"
            ] = age_value

            filtered_records.append(
                record
            )

        filtered_records.sort(
            key=lambda record: str(
                record.get(
                    sort_field,
                    "",
                )
                or ""
            ).casefold(),
            reverse=(
                sort_direction == -1
            ),
        )

        total_records = len(
            filtered_records
        )

        total_pages = (
            (
                total_records
                + page_size
                - 1
            )
            // page_size
            if total_records
            else 0
        )

        start_index = (
            page - 1
        ) * page_size

        end_index = (
            start_index
            + page_size
        )

        return {
            "records": filtered_records[
                start_index:end_index
            ],
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
        }

    def distinct_values(
        self,
        field: str,
        *,
        animal_type: str | None = "Dog",
    ) -> list[str]:
        """
        Return sorted distinct values for an approved field.
        """

        values = {
            str(
                record.get(field)
            ).strip()
            for record in self.records
            if (
                animal_type is None
                or record.get(
                    "animal_type"
                )
                == animal_type
            )
            and record.get(field)
            not in {
                None,
                "",
            }
        }

        return sorted(
            values,
            key=str.casefold,
        )

    def age_bounds(
        self,
        *,
        animal_type: str | None = "Dog",
    ) -> tuple[float, float] | None:
        """
        Return minimum and maximum ages for matching records.
        """

        ages = [
            float(
                self._age_value(
                    record
                )
            )
            for record in self.records
            if (
                animal_type is None
                or record.get(
                    "animal_type"
                )
                == animal_type
            )
            and self._age_value(
                record
            )
            is not None
        ]

        if not ages:
            return None

        return (
            min(ages),
            max(ages),
        )


# ----------------------------------------------------------------------
# TEST DATA
# ----------------------------------------------------------------------


@pytest.fixture
def animal_records() -> list[dict[str, Any]]:
    """
    Return dog and cat records covering ranking and filtering scenarios.
    """

    return [
        {
            "record_uid": "animals:test-a001",
            "animal_id": "A001",
            "animal_type": "Dog",
            "name": "Daisy",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_in_weeks": 100.0,
            "age_upon_outcome_in_weeks": 100.0,
            "outcome_type": "Transfer",
            "location_lat": 30.2672,
            "location_long": -97.7431,
        },
        {
            "record_uid": "animals:test-a002",
            "animal_id": "A002",
            "animal_type": "Dog",
            "name": "Bella",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Spayed Female",
            "age_in_weeks": 300.0,
            "age_upon_outcome_in_weeks": 300.0,
            "outcome_type": "Adoption",
            "location_lat": 30.3000,
            "location_long": -97.7000,
        },
        {
            "record_uid": "animals:test-a003",
            "animal_id": "A003",
            "animal_type": "Dog",
            "name": "Scout",
            "breed": "German Shepherd",
            "sex_upon_outcome": "Intact Male",
            "age_in_weeks": 130.0,
            "age_upon_outcome_in_weeks": 130.0,
            "outcome_type": "Transfer",
            "location_lat": 30.3500,
            "location_long": -97.7500,
        },
        {
            "record_uid": "animals:test-c001",
            "animal_id": "C001",
            "animal_type": "Cat",
            "name": "Whiskers",
            "breed": "Domestic Shorthair",
            "sex_upon_outcome": "Neutered Male",
            "age_in_weeks": 52.0,
            "age_upon_outcome_in_weeks": 52.0,
            "outcome_type": "Adoption",
            "location_lat": 30.2500,
            "location_long": -97.7200,
        },
    ]


@pytest.fixture
def service(
    animal_records: list[dict[str, Any]],
) -> DashboardService:
    """
    Return a DashboardService configured with the in-memory fake database.
    """

    shelter = FakeAnimalShelter(
        animal_records
    )

    return DashboardService(
        shelter
    )


# ----------------------------------------------------------------------
# DASHBOARD SERVICE TESTS
# ----------------------------------------------------------------------


def test_load_animals_returns_dogs_only(
    service: DashboardService,
) -> None:
    """
    The default service load should exclude non-dog records.
    """

    frame = service.load_animals(
        dogs_only=True
    )

    assert len(frame) == 3

    assert set(
        frame["animal_type"]
    ) == {
        "Dog",
    }

    assert list(
        frame["animal_id"]
    ) == [
        "A001",
        "A002",
        "A003",
    ]


def test_water_rescue_ranks_best_candidate_first(
    service: DashboardService,
) -> None:
    """
    Daisy matches every Water Rescue preference and should rank first.
    """

    frame = service.filter_and_rank(
        rescue_type="Water Rescue"
    )

    assert not frame.empty

    assert (
        frame.iloc[0][
            "animal_id"
        ]
        == "A001"
    )

    assert (
        frame.iloc[0][
            "name"
        ]
        == "Daisy"
    )

    assert (
        int(
            frame.iloc[0][
                "recommendation_rank"
            ]
        )
        == 1
    )

    assert (
        float(
            frame.iloc[0][
                "match_score"
            ]
        )
        == 100.0
    )


def test_breed_filter_narrows_results(
    service: DashboardService,
) -> None:
    """
    The breed filter should be applied before ranking or reset display.
    """

    frame = service.filter_and_rank(
        rescue_type=RESET_RESCUE_TYPE,
        breed="Labrador Retriever",
    )

    assert set(
        frame["animal_id"]
    ) == {
        "A001",
        "A002",
    }

    assert (
        frame["breed"]
        == "Labrador Retriever"
    ).all()


def test_breed_and_outcome_filters_work_together(
    service: DashboardService,
) -> None:
    """
    Multiple database filters should operate as combined constraints.
    """

    frame = service.filter_and_rank(
        rescue_type=RESET_RESCUE_TYPE,
        breed="Labrador Retriever",
        outcome_type="Transfer",
    )

    assert len(frame) == 1

    assert (
        frame.iloc[0][
            "animal_id"
        ]
        == "A001"
    )

    assert (
        frame.iloc[0][
            "outcome_type"
        ]
        == "Transfer"
    )


def test_age_filter_narrows_results(
    service: DashboardService,
) -> None:
    """
    The age-range filter should include both boundaries.
    """

    frame = service.filter_and_rank(
        rescue_type=RESET_RESCUE_TYPE,
        age_range=[
            90,
            110,
        ],
    )

    assert len(frame) == 1

    assert (
        frame.iloc[0][
            "animal_id"
        ]
        == "A001"
    )

    assert (
        float(
            frame.iloc[0][
                "age_upon_outcome_in_weeks"
            ]
        )
        == 100.0
    )


def test_reset_mode_does_not_rank_animals(
    service: DashboardService,
) -> None:
    """
    Reset mode should preserve browsing without rescue recommendation ranks.
    """

    frame = service.filter_and_rank(
        rescue_type=RESET_RESCUE_TYPE
    )

    assert len(frame) == 3

    assert (
        frame["match_score"]
        == 0
    ).all()

    assert set(
        frame["match_level"]
    ) == {
        "Not Ranked",
    }

    assert (
        frame[
            "recommendation_rank"
        ]
        .isna()
        .all()
    )


def test_top_candidate_returns_best_match(
    service: DashboardService,
) -> None:
    """
    top_candidate should return the first ranked Water Rescue result.
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
        candidate["name"]
        == "Daisy"
    )

    assert (
        candidate[
            "recommendation_rank"
        ]
        == 1
    )

    assert (
        candidate[
            "match_score"
        ]
        == 100
    )

    assert (
        candidate[
            "match_level"
        ]
        == "Strong Match"
    )