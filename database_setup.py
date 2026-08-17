"""
database_setup.py
-----------------
Database collection and validation setup for CS 499 Enhancement Three.

This module creates and configures the validated MongoDB collections used
by the enhanced Grazioso Salvare dashboard.

The original aac.animals collection is never modified by this module.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Databases
"""

from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database


ENHANCED_COLLECTION = "animals_enhanced"
AUDIT_COLLECTION = "audit_logs"


ANIMAL_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Enhanced Animal Record",
        "required": [
            "record_uid",
            "animal_id",
            "animal_type",
            "breed",
            "source_collection",
            "source_record_id",
            "migrated_at",
        ],
        "additionalProperties": False,
        "properties": {
            "_id": {
                "bsonType": "objectId",
            },
            "record_uid": {
                "bsonType": "string",
                "minLength": 1,
                "description": (
                    "Unique identifier for this database record."
                ),
            },
            "animal_id": {
                "bsonType": "string",
                "minLength": 1,
            },
            "name": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "animal_type": {
                "bsonType": "string",
                "minLength": 1,
            },
            "breed": {
                "bsonType": "string",
                "minLength": 1,
            },
            "color": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "sex_upon_outcome": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "age_in_weeks": {
                "bsonType": [
                    "double",
                    "int",
                    "long",
                    "decimal",
                    "null",
                ],
                "minimum": 0,
            },
            "outcome_type": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "outcome_subtype": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "outcome_date": {
                "bsonType": [
                    "date",
                    "null",
                ],
            },
            "date_of_birth": {
                "bsonType": [
                    "date",
                    "null",
                ],
            },
            "location_lat": {
                "bsonType": [
                    "double",
                    "int",
                    "long",
                    "decimal",
                    "null",
                ],
                "minimum": -90,
                "maximum": 90,
            },
            "location_long": {
                "bsonType": [
                    "double",
                    "int",
                    "long",
                    "decimal",
                    "null",
                ],
                "minimum": -180,
                "maximum": 180,
            },
            "source_collection": {
                "bsonType": "string",
                "minLength": 1,
            },
            "source_record_id": {
                "bsonType": "string",
                "minLength": 1,
            },
            "migrated_at": {
                "bsonType": "date",
            },
        },
    }
}


AUDIT_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Database Audit Record",
        "required": [
            "action",
            "timestamp",
            "performed_by",
            "success",
        ],
        "additionalProperties": False,
        "properties": {
            "_id": {
                "bsonType": "objectId",
            },
            "record_uid": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "source_record_id": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "action": {
                "bsonType": "string",
                "enum": [
                    "create",
                    "update",
                    "delete",
                    "migration",
                    "schema_test",
                ],
            },
            "timestamp": {
                "bsonType": "date",
            },
            "changed_fields": {
                "bsonType": "array",
                "items": {
                    "bsonType": "string",
                },
            },
            "performed_by": {
                "bsonType": "string",
                "minLength": 1,
            },
            "success": {
                "bsonType": "bool",
            },
            "error_message": {
                "bsonType": [
                    "string",
                    "null",
                ],
            },
            "details": {
                "bsonType": [
                    "object",
                    "null",
                ],
            },
        },
    }
}


def _collection_exists(
    database: Database,
    collection_name: str,
) -> bool:
    """Return True when the requested collection already exists."""

    return collection_name in database.list_collection_names()


def _ensure_validated_collection(
    database: Database,
    collection_name: str,
    validator: dict[str, Any],
) -> str:
    """
    Create a validated collection or update its existing validator.

    This function is safe to run more than once. It never drops a
    collection or deletes existing data.
    """

    if not _collection_exists(
        database,
        collection_name,
    ):
        database.create_collection(
            collection_name,
            validator=validator,
            validationLevel="strict",
            validationAction="error",
        )

        return "created"

    database.command(
        {
            "collMod": collection_name,
            "validator": validator,
            "validationLevel": "strict",
            "validationAction": "error",
        }
    )

    return "updated"


def setup_database(
    database: Database,
) -> dict[str, Any]:
    """
    Create or update Enhancement Three database collections.

    Args:
        database:
            Connected PyMongo database object.

    Returns:
        Dictionary containing collection and index setup results.
    """

    animal_status = _ensure_validated_collection(
        database,
        ENHANCED_COLLECTION,
        ANIMAL_VALIDATOR,
    )

    audit_status = _ensure_validated_collection(
        database,
        AUDIT_COLLECTION,
        AUDIT_VALIDATOR,
    )

    animal_collection = database[
        ENHANCED_COLLECTION
    ]

    audit_collection = database[
        AUDIT_COLLECTION
    ]

    # This unique index protects the generated record identifier.
    #
    # animal_id is intentionally not unique because the source dataset
    # contains animals with more than one shelter outcome record.
    animal_uid_index = animal_collection.create_index(
        [
            (
                "record_uid",
                ASCENDING,
            )
        ],
        unique=True,
        name="uidx_record_uid",
    )

    audit_timestamp_index = audit_collection.create_index(
        [
            (
                "timestamp",
                DESCENDING,
            )
        ],
        name="idx_audit_timestamp",
    )

    return {
        "animal_collection": ENHANCED_COLLECTION,
        "animal_collection_status": animal_status,
        "animal_uid_index": animal_uid_index,
        "audit_collection": AUDIT_COLLECTION,
        "audit_collection_status": audit_status,
        "audit_timestamp_index": audit_timestamp_index,
    }