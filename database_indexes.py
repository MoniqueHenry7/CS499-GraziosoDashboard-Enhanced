"""
database_indexes.py
-------------------
MongoDB index configuration for CS 499 Enhancement Three.

Indexes are selected from the filter and lookup patterns used by
the Grazioso Salvare Rescue Match Recommendation Dashboard.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Databases
"""

from __future__ import annotations

from typing import Any

from pymongo import (
    ASCENDING,
    DESCENDING,
    IndexModel,
)
from pymongo.collection import Collection
from pymongo.errors import PyMongoError


QUERY_INDEXES: tuple[IndexModel, ...] = (
    IndexModel(
        [
            (
                "animal_type",
                ASCENDING,
            ),
            (
                "breed",
                ASCENDING,
            ),
            (
                "age_in_weeks",
                ASCENDING,
            ),
        ],
        name="idx_type_breed_age",
    ),
    IndexModel(
        [
            (
                "animal_type",
                ASCENDING,
            ),
            (
                "outcome_type",
                ASCENDING,
            ),
            (
                "age_in_weeks",
                ASCENDING,
            ),
        ],
        name="idx_type_outcome_age",
    ),
    IndexModel(
        [
            (
                "animal_id",
                ASCENDING,
            ),
        ],
        name="idx_animal_id",
    ),
    IndexModel(
        [
            (
                "outcome_date",
                DESCENDING,
            ),
        ],
        name="idx_outcome_date",
    ),
)


def ensure_query_indexes(
    collection: Collection,
) -> dict[str, Any]:
    """
    Create or confirm indexes supporting dashboard query patterns.

    animal_id is intentionally not unique because the source data
    contains multiple shelter records for some animals.
    """

    try:
        created_index_names = (
            collection.create_indexes(
                list(QUERY_INDEXES)
            )
        )

        current_indexes = list(
            collection.list_indexes()
        )

        return {
            "created_or_confirmed": (
                created_index_names
            ),
            "all_index_names": [
                index["name"]
                for index in current_indexes
            ],
        }

    except PyMongoError as error:
        raise RuntimeError(
            "Unable to create the Enhancement Three "
            "MongoDB query indexes."
        ) from error