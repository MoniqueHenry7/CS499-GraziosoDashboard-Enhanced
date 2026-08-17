"""
database_migration.py
---------------------
Data migration utilities for CS 499 Enhancement Three.

This module copies and normalizes records from the original
aac.animals collection into the validated aac.animals_enhanced
collection.

The original collection is treated as read-only.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Databases
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ReplaceOne
from pymongo.database import Database
from pymongo.errors import BulkWriteError, PyMongoError

from database_setup import (
    AUDIT_COLLECTION,
    ENHANCED_COLLECTION,
)


SOURCE_COLLECTION = "animals"
DEFAULT_BATCH_SIZE = 500


def clean_text(
    value: Any,
) -> str | None:
    """Convert a value to cleaned text or return None."""

    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    return cleaned


def safe_float(
    value: Any,
) -> float | None:
    """Convert a value to float when possible."""

    if value is None:
        return None

    try:
        numeric_value = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None

    return numeric_value


def normalize_age(
    value: Any,
) -> float | None:
    """
    Convert the original age value to a nonnegative float.

    Invalid or negative values become None rather than being
    misrepresented as zero.
    """

    numeric_age = safe_float(value)

    if numeric_age is None:
        return None

    if numeric_age < 0:
        return None

    return numeric_age


def parse_datetime(
    value: Any,
) -> datetime | None:
    """Convert supported date values into Python datetime objects."""

    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value

    cleaned = clean_text(value)

    if cleaned is None:
        return None

    supported_formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y",
    )

    for date_format in supported_formats:
        try:
            return datetime.strptime(
                cleaned,
                date_format,
            )

        except ValueError:
            continue

    return None


def normalize_source_record(
    source_record: dict[str, Any],
    migrated_at: datetime | None = None,
) -> dict[str, Any]:
    """
    Convert one original shelter record into the enhanced schema.

    Raises:
        ValueError:
            When a field required by the enhanced schema is missing.
    """

    source_id = clean_text(
        source_record.get("_id")
    )

    animal_id = clean_text(
        source_record.get("animal_id")
    )

    animal_type = clean_text(
        source_record.get("animal_type")
    )

    breed = clean_text(
        source_record.get("breed")
    )

    missing_required_fields: list[str] = []

    if source_id is None:
        missing_required_fields.append(
            "_id"
        )

    if animal_id is None:
        missing_required_fields.append(
            "animal_id"
        )

    if animal_type is None:
        missing_required_fields.append(
            "animal_type"
        )

    if breed is None:
        missing_required_fields.append(
            "breed"
        )

    if missing_required_fields:
        missing_text = ", ".join(
            missing_required_fields
        )

        raise ValueError(
            "Missing required source fields: "
            f"{missing_text}"
        )

    migration_time = (
        migrated_at
        if migrated_at is not None
        else datetime.now(
            timezone.utc
        )
    )

    # The MongoDB source _id is unique for every shelter outcome
    # record. It is therefore safer than making animal_id unique,
    # because one animal can appear in multiple outcome records.
    record_uid = (
        f"{SOURCE_COLLECTION}:{source_id}"
    )

    outcome_date = parse_datetime(
        source_record.get(
            "outcome_date"
        )
        or source_record.get(
            "datetime"
        )
    )

    return {
        "record_uid": record_uid,
        "animal_id": animal_id,
        "name": clean_text(
            source_record.get("name")
        ),
        "animal_type": animal_type,
        "breed": breed,
        "color": clean_text(
            source_record.get("color")
        ),
        "sex_upon_outcome": clean_text(
            source_record.get(
                "sex_upon_outcome"
            )
        ),
        "age_in_weeks": normalize_age(
            source_record.get(
                "age_upon_outcome_in_weeks"
            )
        ),
        "outcome_type": clean_text(
            source_record.get(
                "outcome_type"
            )
        ),
        "outcome_subtype": clean_text(
            source_record.get(
                "outcome_subtype"
            )
        ),
        "outcome_date": outcome_date,
        "date_of_birth": parse_datetime(
            source_record.get(
                "date_of_birth"
            )
        ),
        "location_lat": safe_float(
            source_record.get(
                "location_lat"
            )
        ),
        "location_long": safe_float(
            source_record.get(
                "location_long"
            )
        ),
        "source_collection": SOURCE_COLLECTION,
        "source_record_id": source_id,
        "migrated_at": migration_time,
    }


def _execute_batch(
    target_collection: Any,
    operations: list[ReplaceOne],
) -> dict[str, int]:
    """Execute one migration batch."""

    if not operations:
        return {
            "matched": 0,
            "modified": 0,
            "upserted": 0,
        }

    result = target_collection.bulk_write(
        operations,
        ordered=False,
    )

    return {
        "matched": result.matched_count,
        "modified": result.modified_count,
        "upserted": result.upserted_count,
    }


def migrate_animals(
    database: Database,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Migrate and normalize all original shelter records.

    ReplaceOne with upsert makes the migration safe to rerun.
    Existing enhanced records are updated rather than duplicated.
    """

    if not isinstance(
        batch_size,
        int,
    ) or batch_size < 1:
        raise ValueError(
            "Batch size must be a positive integer."
        )

    source_collection = database[
        SOURCE_COLLECTION
    ]

    target_collection = database[
        ENHANCED_COLLECTION
    ]

    audit_collection = database[
        AUDIT_COLLECTION
    ]

    migration_time = datetime.now(
        timezone.utc
    )

    source_count_before = (
        source_collection.count_documents({})
    )

    statistics: dict[str, Any] = {
        "source_collection": SOURCE_COLLECTION,
        "target_collection": ENHANCED_COLLECTION,
        "source_count_before": source_count_before,
        "records_processed": 0,
        "valid_records": 0,
        "skipped_records": 0,
        "negative_or_invalid_ages_normalized": 0,
        "missing_names_preserved_as_null": 0,
        "missing_outcomes_preserved_as_null": 0,
        "matched_records": 0,
        "modified_records": 0,
        "upserted_records": 0,
        "migration_errors": [],
    }

    operations: list[ReplaceOne] = []

    try:
        source_cursor = source_collection.find(
            {}
        )

        for source_record in source_cursor:
            statistics[
                "records_processed"
            ] += 1

            original_age = source_record.get(
                "age_upon_outcome_in_weeks"
            )

            try:
                normalized_record = (
                    normalize_source_record(
                        source_record,
                        migrated_at=migration_time,
                    )
                )

            except ValueError as error:
                statistics[
                    "skipped_records"
                ] += 1

                if (
                    len(
                        statistics[
                            "migration_errors"
                        ]
                    )
                    < 25
                ):
                    statistics[
                        "migration_errors"
                    ].append(
                        {
                            "source_record_id": (
                                clean_text(
                                    source_record.get(
                                        "_id"
                                    )
                                )
                            ),
                            "error": str(error),
                        }
                    )

                continue

            if (
                original_age is not None
                and normalized_record[
                    "age_in_weeks"
                ]
                is None
            ):
                statistics[
                    "negative_or_invalid_ages_normalized"
                ] += 1

            if normalized_record["name"] is None:
                statistics[
                    "missing_names_preserved_as_null"
                ] += 1

            if (
                normalized_record[
                    "outcome_type"
                ]
                is None
            ):
                statistics[
                    "missing_outcomes_preserved_as_null"
                ] += 1

            operations.append(
                ReplaceOne(
                    {
                        "record_uid": (
                            normalized_record[
                                "record_uid"
                            ]
                        )
                    },
                    normalized_record,
                    upsert=True,
                )
            )

            statistics[
                "valid_records"
            ] += 1

            if len(operations) >= batch_size:
                batch_result = _execute_batch(
                    target_collection,
                    operations,
                )

                statistics[
                    "matched_records"
                ] += batch_result["matched"]

                statistics[
                    "modified_records"
                ] += batch_result["modified"]

                statistics[
                    "upserted_records"
                ] += batch_result["upserted"]

                operations.clear()

        if operations:
            batch_result = _execute_batch(
                target_collection,
                operations,
            )

            statistics[
                "matched_records"
            ] += batch_result["matched"]

            statistics[
                "modified_records"
            ] += batch_result["modified"]

            statistics[
                "upserted_records"
            ] += batch_result["upserted"]

            operations.clear()

        statistics["source_count_after"] = (
            source_collection.count_documents({})
        )

        statistics["target_count_after"] = (
            target_collection.count_documents({})
        )

        migration_successful = (
            statistics["skipped_records"] == 0
            and statistics[
                "source_count_before"
            ]
            == statistics[
                "source_count_after"
            ]
            and statistics[
                "target_count_after"
            ]
            == statistics[
                "valid_records"
            ]
        )

        statistics["success"] = (
            migration_successful
        )

        audit_collection.insert_one(
            {
                "record_uid": None,
                "source_record_id": None,
                "action": "migration",
                "timestamp": migration_time,
                "changed_fields": [
                    "record_uid",
                    "age_in_weeks",
                    "outcome_date",
                    "date_of_birth",
                    "location_lat",
                    "location_long",
                ],
                "performed_by": (
                    "database_migration.py"
                ),
                "success": migration_successful,
                "error_message": (
                    None
                    if migration_successful
                    else (
                        "Migration completed with "
                        "skipped or mismatched records."
                    )
                ),
                "details": {
                    "source_count": statistics[
                        "source_count_before"
                    ],
                    "target_count": statistics[
                        "target_count_after"
                    ],
                    "valid_records": statistics[
                        "valid_records"
                    ],
                    "skipped_records": statistics[
                        "skipped_records"
                    ],
                },
            }
        )

        return statistics

    except (
        BulkWriteError,
        PyMongoError,
    ) as error:
        try:
            audit_collection.insert_one(
                {
                    "record_uid": None,
                    "source_record_id": None,
                    "action": "migration",
                    "timestamp": migration_time,
                    "changed_fields": [],
                    "performed_by": (
                        "database_migration.py"
                    ),
                    "success": False,
                    "error_message": (
                        type(error).__name__
                    ),
                    "details": {
                        "records_processed": (
                            statistics[
                                "records_processed"
                            ]
                        )
                    },
                }
            )

        except PyMongoError:
            pass

        raise RuntimeError(
            "The animal migration failed."
        ) from error