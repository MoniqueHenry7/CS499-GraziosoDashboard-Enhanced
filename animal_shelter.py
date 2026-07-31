"""
animal_shelter.py
-----------------
MongoDB data-access service for the enhanced Grazioso Salvare dashboard.

This module began as the CRUD class created for CS 340 Client/Server
Development. It was refactored during the CS 499 Software Design and
Engineering enhancement and expanded during the Databases enhancement.

Enhancement Three adds:
- Controlled MongoDB query construction.
- Database-side filtering.
- Field projections.
- Sorting and pagination.
- Distinct-value queries.
- Aggregation pipelines.
- Secure record-specific CRUD operations.
- Automatic success and failure audit logging.
- Compatibility with the normalized animals_enhanced collection.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Databases
"""

from collections.abc import Mapping
from datetime import datetime, timezone
from math import isfinite
from typing import Any
from uuid import uuid4

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError


DASHBOARD_PROJECTION: dict[str, int] = {
    "_id": 0,
    "record_uid": 1,
    "animal_id": 1,
    "name": 1,
    "animal_type": 1,
    "breed": 1,
    "sex_upon_outcome": 1,
    "age_in_weeks": 1,
    "outcome_type": 1,
    "location_lat": 1,
    "location_long": 1,
}

ALLOWED_SORT_FIELDS = frozenset({
    "animal_id",
    "name",
    "breed",
    "age_in_weeks",
    "outcome_type",
    "outcome_date",
})

ALLOWED_DISTINCT_FIELDS = frozenset({
    "animal_type",
    "breed",
    "sex_upon_outcome",
    "outcome_type",
})


ENHANCED_COLLECTION_NAME = "animals_enhanced"
AUDIT_COLLECTION_NAME = "audit_logs"

ALLOWED_MUTATION_FIELDS = frozenset({
    "animal_id",
    "name",
    "animal_type",
    "breed",
    "color",
    "sex_upon_outcome",
    "age_in_weeks",
    "outcome_type",
    "outcome_subtype",
    "outcome_date",
    "date_of_birth",
    "location_lat",
    "location_long",
})

REQUIRED_ANIMAL_FIELDS = frozenset({
    "animal_id",
    "animal_type",
    "breed",
})

TEXT_MUTATION_FIELDS = frozenset({
    "animal_id",
    "name",
    "animal_type",
    "breed",
    "color",
    "sex_upon_outcome",
    "outcome_type",
    "outcome_subtype",
})

NUMERIC_MUTATION_FIELDS = frozenset({
    "age_in_weeks",
    "location_lat",
    "location_long",
})

DATE_MUTATION_FIELDS = frozenset({
    "outcome_date",
    "date_of_birth",
})


class AnimalShelter:
    """
    Provides CRUD operations for the MongoDB animal shelter collection.

    The class is responsible only for database connectivity and basic
    database operations. Dashboard presentation, rescue recommendation
    logic, and user-interface behavior are handled by separate modules.

    This separation of responsibilities improves maintainability,
    readability, testing, and future extensibility.
    """

    def __init__(
        self,
        username: str | None,
        password: str | None,
        host: str,
        port: int,
        db: str,
        col: str,
    ) -> None:
        """
        Connect to the requested MongoDB database and collection.

        Args:
            username:
                MongoDB username. May be None when authentication is
                disabled in the local development environment.

            password:
                MongoDB password. May be None when authentication is
                disabled.

            host:
                MongoDB server hostname or IP address.

            port:
                MongoDB server port.

            db:
                Name of the MongoDB database.

            col:
                Name of the MongoDB collection.

        Raises:
            ValueError:
                If required connection configuration is missing or if
                username/password values are supplied inconsistently.

            ConnectionError:
                If MongoDB cannot be reached.
        """

        self._validate_connection_settings(
            username=username,
            password=password,
            host=host,
            port=port,
            db=db,
            col=col,
        )

        # Store database and collection names for reference.
        self.database_name = db
        self.collection_name = col

        # Build MongoDB connection options.
        #
        # The current local CS 499 development environment can connect
        # without authentication. Authentication can still be enabled by
        # supplying a username and password through configuration.
        connection_options: dict[str, Any] = {
            "host": host,
            "port": int(port),
            "serverSelectionTimeoutMS": 5000,
        }

        if username and password:
            connection_options.update(
                {
                    "username": username,
                    "password": password,
                    "authSource": db,
                }
            )

        try:
            # Establish the MongoDB client connection.
            self.client = MongoClient(**connection_options)

            # Force an immediate connection check instead of waiting until
            # the first database operation.
            self.client.admin.command("ping")

            # Store reusable database and collection references.
            self.database = self.client[db]
            self.collection = self.database[col]

            print(
                f"Connected to MongoDB successfully: "
                f"{self.database_name}.{self.collection_name}"
            )

        except PyMongoError as error:
            # Do not expose usernames, passwords, or full connection strings.
            raise ConnectionError(
                "Unable to connect to the MongoDB database. "
                "Verify that MongoDB is running and that the "
                "connection configuration is correct."
            ) from error

    @staticmethod
    def _validate_connection_settings(
        username: str | None,
        password: str | None,
        host: str,
        port: int,
        db: str,
        col: str,
    ) -> None:
        """
        Validate MongoDB connection configuration before connecting.

        Args:
            username:
                Optional MongoDB username.

            password:
                Optional MongoDB password.

            host:
                MongoDB host.

            port:
                MongoDB port.

            db:
                Database name.

            col:
                Collection name.

        Raises:
            ValueError:
                If required values are invalid.
        """

        if not isinstance(host, str) or not host.strip():
            raise ValueError(
                "MongoDB host must be a non-empty string."
            )

        try:
            numeric_port = int(port)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "MongoDB port must be a valid integer."
            ) from error

        if not 1 <= numeric_port <= 65535:
            raise ValueError(
                "MongoDB port must be between 1 and 65535."
            )

        if not isinstance(db, str) or not db.strip():
            raise ValueError(
                "MongoDB database name must be a non-empty string."
            )

        if not isinstance(col, str) or not col.strip():
            raise ValueError(
                "MongoDB collection name must be a non-empty string."
            )

        # Authentication values must be supplied together.
        if bool(username) != bool(password):
            raise ValueError(
                "MongoDB username and password must both be supplied "
                "or both be omitted."
            )


    # ------------------------------------------------------------------
    # ENHANCEMENT THREE QUERY VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_optional_text(
        value: str | None,
        label: str,
    ) -> str | None:
        """Return cleaned optional text after basic validation."""

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{label} must be a string or None."
            )

        cleaned = value.strip()

        if not cleaned:
            return None

        if len(cleaned) > 200:
            raise ValueError(
                f"{label} exceeds the permitted length."
            )

        return cleaned

    @classmethod
    def build_animal_query(
        cls,
        *,
        animal_type: str | None = "Dog",
        breed: str | None = None,
        outcome_type: str | None = None,
        sex_upon_outcome: str | None = None,
        age_range: tuple[float, float] | list[float] | None = None,
    ) -> dict[str, Any]:
        """Build a MongoDB query from approved application filters."""

        query: dict[str, Any] = {}

        text_filters = {
            "animal_type": (animal_type, "Animal type"),
            "breed": (breed, "Breed"),
            "outcome_type": (outcome_type, "Outcome type"),
            "sex_upon_outcome": (
                sex_upon_outcome,
                "Sex upon outcome",
            ),
        }

        for field, (value, label) in text_filters.items():
            cleaned = cls._clean_optional_text(value, label)

            if cleaned is not None:
                query[field] = cleaned

        if age_range is not None:
            if (
                not isinstance(age_range, (tuple, list))
                or len(age_range) != 2
            ):
                raise ValueError(
                    "Age range must contain exactly two values."
                )

            try:
                minimum_age = float(age_range[0])
                maximum_age = float(age_range[1])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "Age values must be numeric."
                ) from error

            if not (
                isfinite(minimum_age)
                and isfinite(maximum_age)
            ):
                raise ValueError(
                    "Age values must be finite numbers."
                )

            if minimum_age < 0 or maximum_age < 0:
                raise ValueError(
                    "Age values cannot be negative."
                )

            if minimum_age > maximum_age:
                raise ValueError(
                    "Minimum age cannot exceed maximum age."
                )

            query["age_in_weeks"] = {
                "$gte": minimum_age,
                "$lte": maximum_age,
            }

        return query

    @staticmethod
    def _validate_page_parameters(
        page: int,
        page_size: int,
    ) -> tuple[int, int]:
        """Validate pagination boundaries."""

        if not isinstance(page, int) or page < 1:
            raise ValueError(
                "Page must be an integer greater than or equal to 1."
            )

        if (
            not isinstance(page_size, int)
            or not 1 <= page_size <= 100
        ):
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        return page, page_size

    # ------------------------------------------------------------------
    # ENHANCEMENT THREE SECURE MUTATION VALIDATION
    # ------------------------------------------------------------------

    def _require_enhanced_collection(self) -> None:
        """Restrict secure mutation methods to animals_enhanced."""

        if self.collection.name != ENHANCED_COLLECTION_NAME:
            raise RuntimeError(
                "Secure mutation operations are permitted only "
                "on the animals_enhanced collection."
            )

    @classmethod
    def _clean_record_uid(cls, record_uid: str) -> str:
        """Validate an exact enhanced-record identifier."""

        cleaned_uid = cls._clean_optional_text(
            record_uid,
            "Record UID",
        )

        if cleaned_uid is None:
            raise ValueError("Record UID is required.")

        return cleaned_uid

    @staticmethod
    def _attempted_field_names(data: Any) -> list[str]:
        """Return field names safely for audit reporting."""

        if not isinstance(data, Mapping):
            return []

        return sorted(str(field) for field in data.keys())

    @classmethod
    def _normalize_mutation_fields(
        cls,
        data: Mapping[str, Any],
        *,
        require_required_fields: bool,
    ) -> dict[str, Any]:
        """Validate and normalize fields used for creates and updates."""

        if not isinstance(data, Mapping):
            raise ValueError(
                "Animal data must be a mapping of fields and values."
            )

        if not data:
            raise ValueError(
                "At least one animal field is required."
            )

        submitted_fields = set(data.keys())
        unsupported_fields = submitted_fields - ALLOWED_MUTATION_FIELDS

        if unsupported_fields:
            unsupported_text = ", ".join(
                sorted(str(field) for field in unsupported_fields)
            )
            raise ValueError(
                f"Unsupported animal fields: {unsupported_text}"
            )

        normalized: dict[str, Any] = {}

        for field, value in data.items():
            if field in TEXT_MUTATION_FIELDS:
                cleaned_value = cls._clean_optional_text(
                    value,
                    field.replace("_", " ").title(),
                )

                if (
                    field in REQUIRED_ANIMAL_FIELDS
                    and cleaned_value is None
                ):
                    raise ValueError(
                        f"{field} cannot be empty."
                    )

                normalized[field] = cleaned_value
                continue

            if field in NUMERIC_MUTATION_FIELDS:
                if value is None:
                    normalized[field] = None
                    continue

                if isinstance(value, bool):
                    raise ValueError(
                        f"{field} must be numeric."
                    )

                try:
                    numeric_value = float(value)
                except (TypeError, ValueError) as error:
                    raise ValueError(
                        f"{field} must be numeric."
                    ) from error

                if not isfinite(numeric_value):
                    raise ValueError(
                        f"{field} must be a finite number."
                    )

                if field == "age_in_weeks" and numeric_value < 0:
                    raise ValueError(
                        "age_in_weeks cannot be negative."
                    )

                if (
                    field == "location_lat"
                    and not -90 <= numeric_value <= 90
                ):
                    raise ValueError(
                        "location_lat must be between -90 and 90."
                    )

                if (
                    field == "location_long"
                    and not -180 <= numeric_value <= 180
                ):
                    raise ValueError(
                        "location_long must be between -180 and 180."
                    )

                normalized[field] = numeric_value
                continue

            if field in DATE_MUTATION_FIELDS:
                if value is not None and not isinstance(value, datetime):
                    raise ValueError(
                        f"{field} must be a datetime or None."
                    )

                normalized[field] = value

        if require_required_fields:
            missing_fields = REQUIRED_ANIMAL_FIELDS - set(normalized.keys())

            if missing_fields:
                missing_text = ", ".join(sorted(missing_fields))
                raise ValueError(
                    f"Missing required animal fields: {missing_text}"
                )

        if not normalized:
            raise ValueError(
                "No approved animal fields were supplied."
            )

        return normalized

    def _write_audit_entry(
        self,
        *,
        action: str,
        performed_by: str,
        success: bool,
        record_uid: str | None = None,
        source_record_id: str | None = None,
        changed_fields: list[str] | None = None,
        error_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Write one validated database audit event."""

        try:
            cleaned_performer = (
                self._clean_optional_text(
                    performed_by,
                    "Performed by",
                )
                or "unknown"
            )
        except ValueError:
            cleaned_performer = "unknown"

        audit_document = {
            "record_uid": record_uid,
            "source_record_id": source_record_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc),
            "changed_fields": sorted(changed_fields or []),
            "performed_by": cleaned_performer,
            "success": success,
            "error_message": error_message,
            "details": details,
        }

        try:
            result = self.database[AUDIT_COLLECTION_NAME].insert_one(
                audit_document
            )
            return bool(result.acknowledged)
        except PyMongoError as error:
            print(
                "[AUDIT ERROR] Unable to save audit entry: "
                f"{type(error).__name__}"
            )
            return False

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(
        self,
        data: dict[str, Any],
    ) -> bool:
        """
        Insert one animal document into the configured collection.

        Args:
            data:
                Dictionary containing the document to insert.

        Returns:
            True if MongoDB acknowledged the insert.
            False if the database operation failed.

        Raises:
            ValueError:
                If data is not a non-empty dictionary.
        """

        if not isinstance(data, dict) or not data:
            raise ValueError(
                "Create requires a non-empty dictionary."
            )

        try:
            result = self.collection.insert_one(data)

            return bool(result.acknowledged)

        except PyMongoError as error:
            print(
                f"[DATABASE ERROR] Create operation failed: "
                f"{type(error).__name__}"
            )

            return False

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def read(
        self,
        query: dict[str, Any] | None = None,
        projection: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve animal documents that match a MongoDB query.

        Args:
            query:
                MongoDB query dictionary.

                An empty dictionary or None retrieves all documents.

            projection:
                Optional MongoDB field projection dictionary.

                Example:
                    {
                        "animal_id": 1,
                        "name": 1,
                        "breed": 1
                    }

        Returns:
            A list containing matching MongoDB documents.

            Returns an empty list if no records match or if the database
            operation fails.

        Raises:
            ValueError:
                If query or projection is not a dictionary.
        """

        # None means "retrieve all records."
        if query is None:
            query = {}

        if not isinstance(query, dict):
            raise ValueError(
                "Read query must be a dictionary."
            )

        if projection is not None and not isinstance(
            projection,
            dict,
        ):
            raise ValueError(
                "Projection must be a dictionary or None."
            )

        try:
            cursor = self.collection.find(
                query,
                projection,
            )

            return list(cursor)

        except PyMongoError as error:
            print(
                f"[DATABASE ERROR] Read operation failed: "
                f"{type(error).__name__}"
            )

            return []


    # ------------------------------------------------------------------
    # ENHANCEMENT THREE DATABASE-SIDE READ OPERATIONS
    # ------------------------------------------------------------------

    def find_animals_page(
        self,
        *,
        animal_type: str | None = "Dog",
        breed: str | None = None,
        outcome_type: str | None = None,
        sex_upon_outcome: str | None = None,
        age_range: tuple[float, float] | list[float] | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_field: str = "animal_id",
        sort_direction: int = ASCENDING,
    ) -> dict[str, Any]:
        """Return a projected, sorted, and paginated animal result set."""

        page, page_size = self._validate_page_parameters(
            page,
            page_size,
        )

        if sort_field not in ALLOWED_SORT_FIELDS:
            raise ValueError(
                f"Unsupported sort field: {sort_field}"
            )

        if sort_direction not in {ASCENDING, DESCENDING}:
            raise ValueError(
                "Sort direction must be ASCENDING or DESCENDING."
            )

        query = self.build_animal_query(
            animal_type=animal_type,
            breed=breed,
            outcome_type=outcome_type,
            sex_upon_outcome=sex_upon_outcome,
            age_range=age_range,
        )

        skip_count = (page - 1) * page_size

        try:
            total_records = self.collection.count_documents(query)

            cursor = (
                self.collection.find(
                    query,
                    DASHBOARD_PROJECTION,
                )
                .sort(sort_field, sort_direction)
                .skip(skip_count)
                .limit(page_size)
            )

            records = list(cursor)

            # Keep the field name used by the existing dashboard while
            # retaining the normalized database field.
            for record in records:
                record[
                    "age_upon_outcome_in_weeks"
                ] = record.get("age_in_weeks")

            total_pages = (
                (total_records + page_size - 1) // page_size
                if total_records
                else 0
            )

            return {
                "records": records,
                "page": page,
                "page_size": page_size,
                "total_records": total_records,
                "total_pages": total_pages,
            }

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Paginated read failed: "
                f"{type(error).__name__}"
            )

            return {
                "records": [],
                "page": page,
                "page_size": page_size,
                "total_records": 0,
                "total_pages": 0,
            }

    def distinct_values(
        self,
        field: str,
        *,
        animal_type: str | None = "Dog",
    ) -> list[str]:
        """Return approved distinct values directly from MongoDB."""

        if field not in ALLOWED_DISTINCT_FIELDS:
            raise ValueError(
                f"Unsupported distinct field: {field}"
            )

        query = self.build_animal_query(
            animal_type=animal_type
        )

        try:
            values = self.collection.distinct(field, query)

            return sorted(
                {
                    str(value).strip()
                    for value in values
                    if value is not None
                    and str(value).strip()
                },
                key=str.casefold,
            )

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Distinct query failed: "
                f"{type(error).__name__}"
            )

            return []

    def age_bounds(
        self,
        *,
        animal_type: str | None = "Dog",
    ) -> tuple[float, float] | None:
        """Return minimum and maximum age values using aggregation."""

        query = self.build_animal_query(
            animal_type=animal_type
        )

        pipeline = [
            {
                "$match": {
                    **query,
                    "age_in_weeks": {"$ne": None},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "minimum_age": {"$min": "$age_in_weeks"},
                    "maximum_age": {"$max": "$age_in_weeks"},
                }
            },
        ]

        try:
            results = list(
                self.collection.aggregate(pipeline)
            )

            if not results:
                return None

            return (
                float(results[0]["minimum_age"]),
                float(results[0]["maximum_age"]),
            )

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Age aggregation failed: "
                f"{type(error).__name__}"
            )

            return None

    def outcome_summary(
        self,
        *,
        animal_type: str | None = "Dog",
    ) -> list[dict[str, Any]]:
        """Summarize totals and average ages by outcome type."""

        query = self.build_animal_query(
            animal_type=animal_type
        )

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": "$outcome_type",
                    "total": {"$sum": 1},
                    "average_age": {"$avg": "$age_in_weeks"},
                }
            },
            {"$sort": {"total": -1, "_id": 1}},
            {
                "$project": {
                    "_id": 0,
                    "outcome_type": {
                        "$ifNull": ["$_id", "Unknown"]
                    },
                    "total": 1,
                    "average_age": {
                        "$round": ["$average_age", 2]
                    },
                }
            },
        ]

        try:
            return list(
                self.collection.aggregate(pipeline)
            )

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Outcome aggregation failed: "
                f"{type(error).__name__}"
            )

            return []

    # ------------------------------------------------------------------
    # ENHANCEMENT THREE SECURE CRUD
    # ------------------------------------------------------------------

    def create_animal_record(
        self,
        data: Mapping[str, Any],
        *,
        performed_by: str = "dashboard",
    ) -> dict[str, Any]:
        """Create one validated record in animals_enhanced."""

        self._require_enhanced_collection()
        attempted_fields = self._attempted_field_names(data)

        try:
            normalized_fields = self._normalize_mutation_fields(
                data,
                require_required_fields=True,
            )
        except ValueError as error:
            self._write_audit_entry(
                action="create",
                performed_by=performed_by,
                success=False,
                changed_fields=attempted_fields,
                error_message=str(error),
                details={"reason": "input_validation"},
            )
            raise

        generated_identifier = uuid4().hex
        record_uid = f"application:{generated_identifier}"
        created_at = datetime.now(timezone.utc)

        document = {
            **normalized_fields,
            "record_uid": record_uid,
            "source_collection": "application",
            "source_record_id": generated_identifier,
            "migrated_at": created_at,
        }

        try:
            result = self.collection.insert_one(document)

            self._write_audit_entry(
                action="create",
                performed_by=performed_by,
                success=bool(result.acknowledged),
                record_uid=record_uid,
                source_record_id=generated_identifier,
                changed_fields=list(normalized_fields.keys()),
                details={"collection": self.collection.name},
            )

            returned_document = dict(document)
            returned_document["inserted_id"] = str(result.inserted_id)
            return returned_document

        except (DuplicateKeyError, PyMongoError) as error:
            self._write_audit_entry(
                action="create",
                performed_by=performed_by,
                success=False,
                record_uid=record_uid,
                source_record_id=generated_identifier,
                changed_fields=list(normalized_fields.keys()),
                error_message=type(error).__name__,
                details={"collection": self.collection.name},
            )
            raise RuntimeError(
                "The animal record could not be created."
            ) from error

    def get_animal_by_uid(
        self,
        record_uid: str,
    ) -> dict[str, Any] | None:
        """Return one enhanced record by exact record_uid."""

        cleaned_uid = self._clean_record_uid(record_uid)

        try:
            record = self.collection.find_one(
                {"record_uid": cleaned_uid},
                DASHBOARD_PROJECTION,
            )
        except PyMongoError as error:
            raise RuntimeError(
                "The animal record could not be read."
            ) from error

        if record is None:
            return None

        record["age_upon_outcome_in_weeks"] = record.get(
            "age_in_weeks"
        )
        return record

    def update_animal_record(
        self,
        record_uid: str,
        updates: Mapping[str, Any],
        *,
        performed_by: str = "dashboard",
    ) -> dict[str, int]:
        """Update approved fields on one exact enhanced record."""

        self._require_enhanced_collection()
        cleaned_uid = self._clean_record_uid(record_uid)
        attempted_fields = self._attempted_field_names(updates)

        try:
            normalized_updates = self._normalize_mutation_fields(
                updates,
                require_required_fields=False,
            )
        except ValueError as error:
            self._write_audit_entry(
                action="update",
                performed_by=performed_by,
                success=False,
                record_uid=cleaned_uid,
                changed_fields=attempted_fields,
                error_message=str(error),
                details={"reason": "input_validation"},
            )
            raise

        try:
            existing_record = self.collection.find_one(
                {"record_uid": cleaned_uid},
                {"_id": 0, "source_record_id": 1},
            )
        except PyMongoError as error:
            self._write_audit_entry(
                action="update",
                performed_by=performed_by,
                success=False,
                record_uid=cleaned_uid,
                changed_fields=list(normalized_updates.keys()),
                error_message=type(error).__name__,
                details={"reason": "lookup_failed"},
            )
            raise RuntimeError(
                "The animal record could not be read before updating."
            ) from error

        if existing_record is None:
            self._write_audit_entry(
                action="update",
                performed_by=performed_by,
                success=False,
                record_uid=cleaned_uid,
                changed_fields=list(normalized_updates.keys()),
                error_message="Record not found.",
                details={"reason": "not_found"},
            )
            return {"matched": 0, "modified": 0}

        source_record_id = existing_record.get("source_record_id")

        try:
            result = self.collection.update_one(
                {"record_uid": cleaned_uid},
                {"$set": normalized_updates},
            )

            self._write_audit_entry(
                action="update",
                performed_by=performed_by,
                success=result.matched_count == 1,
                record_uid=cleaned_uid,
                source_record_id=source_record_id,
                changed_fields=list(normalized_updates.keys()),
                details={
                    "matched_count": result.matched_count,
                    "modified_count": result.modified_count,
                },
            )

            return {
                "matched": int(result.matched_count),
                "modified": int(result.modified_count),
            }

        except PyMongoError as error:
            self._write_audit_entry(
                action="update",
                performed_by=performed_by,
                success=False,
                record_uid=cleaned_uid,
                source_record_id=source_record_id,
                changed_fields=list(normalized_updates.keys()),
                error_message=type(error).__name__,
            )
            raise RuntimeError(
                "The animal record could not be updated."
            ) from error

    def delete_animal_record(
        self,
        record_uid: str,
        *,
        confirm: bool = False,
        performed_by: str = "dashboard",
    ) -> bool:
        """Delete one exact enhanced record after confirmation."""

        self._require_enhanced_collection()
        cleaned_uid = self._clean_record_uid(record_uid)

        if confirm is not True:
            self._write_audit_entry(
                action="delete",
                performed_by=performed_by,
                success=False,
                record_uid=cleaned_uid,
                changed_fields=[],
                error_message=(
                    "Deletion confirmation was not supplied."
                ),
                details={"reason": "confirmation_required"},
            )
            raise ValueError(
                "Deletion requires confirm=True."
            )

        try:
            existing_record = self.collection.find_one(
                {"record_uid": cleaned_uid},
                {"_id": 0, "source_record_id": 1},
            )
        except PyMongoError as error:
            self._write_audit_entry(
                action="delete",
                performed_by=performed_by,
                success=False,
                record_uid=cleaned_uid,
                changed_fields=[],
                error_message=type(error).__name__,
                details={"reason": "lookup_failed"},
            )
            raise RuntimeError(
                "The animal record could not be read before deletion."
            ) from error

        if existing_record is None:
            self._write_audit_entry(
                action="delete",
                performed_by=performed_by,
                success=False,
                record_uid=cleaned_uid,
                changed_fields=[],
                error_message="Record not found.",
                details={"reason": "not_found"},
            )
            return False

        source_record_id = existing_record.get("source_record_id")

        try:
            result = self.collection.delete_one(
                {"record_uid": cleaned_uid}
            )
            deleted = result.deleted_count == 1

            self._write_audit_entry(
                action="delete",
                performed_by=performed_by,
                success=deleted,
                record_uid=cleaned_uid,
                source_record_id=source_record_id,
                changed_fields=[],
                error_message=(
                    None if deleted else "Record was not deleted."
                ),
                details={"deleted_count": result.deleted_count},
            )

            return deleted

        except PyMongoError as error:
            self._write_audit_entry(
                action="delete",
                performed_by=performed_by,
                success=False,
                record_uid=cleaned_uid,
                source_record_id=source_record_id,
                changed_fields=[],
                error_message=type(error).__name__,
            )
            raise RuntimeError(
                "The animal record could not be deleted."
            ) from error

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(
        self,
        query: dict[str, Any],
        update_data: dict[str, Any],
    ) -> int:
        """
        Update documents that match a MongoDB query.

        The method intentionally rejects an empty query. Allowing an empty
        update query could unintentionally modify every document in the
        collection.

        Args:
            query:
                Non-empty MongoDB query identifying documents to update.

            update_data:
                Non-empty dictionary containing fields and values to change.

        Returns:
            Number of documents modified.

            Returns 0 when no documents were modified or when the database
            operation fails.

        Raises:
            ValueError:
                If query or update_data is empty or not a dictionary.
        """

        if not isinstance(query, dict) or not query:
            raise ValueError(
                "Update requires a non-empty query. "
                "Empty update queries are not permitted."
            )

        if (
            not isinstance(update_data, dict)
            or not update_data
        ):
            raise ValueError(
                "Update requires non-empty update data."
            )

        # Prevent callers from supplying MongoDB update operators directly
        # through update_data during this milestone.
        #
        # The service controls the use of "$set" so that ordinary field
        # updates follow one predictable structure.
        if any(
            str(field).startswith("$")
            for field in update_data
        ):
            raise ValueError(
                "Update field names may not begin with '$'."
            )

        try:
            result = self.collection.update_many(
                query,
                {
                    "$set": update_data
                },
            )

            return int(result.modified_count)

        except PyMongoError as error:
            print(
                f"[DATABASE ERROR] Update operation failed: "
                f"{type(error).__name__}"
            )

            return 0

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(
        self,
        query: dict[str, Any],
    ) -> int:
        """
        Delete documents that match a MongoDB query.

        The method intentionally rejects an empty query to reduce the risk
        of accidentally deleting every record in the collection.

        Args:
            query:
                Non-empty MongoDB query identifying documents to delete.

        Returns:
            Number of documents deleted.

            Returns 0 when no documents were deleted or when the database
            operation fails.

        Raises:
            ValueError:
                If query is empty or is not a dictionary.
        """

        if not isinstance(query, dict) or not query:
            raise ValueError(
                "Delete requires a non-empty query. "
                "Empty delete queries are not permitted."
            )

        try:
            result = self.collection.delete_many(query)

            return int(result.deleted_count)

        except PyMongoError as error:
            print(
                f"[DATABASE ERROR] Delete operation failed: "
                f"{type(error).__name__}"
            )

            return 0

    # ------------------------------------------------------------------
    # CONNECTION MANAGEMENT
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """
        Check whether the MongoDB server is reachable.

        Returns:
            True when the MongoDB server responds successfully.
            False when the connection check fails.
        """

        try:
            self.client.admin.command("ping")

            return True

        except PyMongoError:
            return False

    def close(self) -> None:
        """
        Close the MongoDB client connection.

        Calling close() when the application shuts down helps release
        database connection resources cleanly.
        """

        if hasattr(self, "client"):
            self.client.close()

    def __enter__(self) -> "AnimalShelter":
        """
        Allow AnimalShelter to optionally be used as a context manager.

        Example:
            with AnimalShelter(...) as shelter:
                records = shelter.read({})
        """

        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        """
        Close the MongoDB connection when leaving a context manager.
        """

        self.close()