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
- Compatibility with the normalized animals_enhanced collection.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Databases
"""

from math import isfinite
from typing import Any

from pymongo import (
    ASCENDING,
    DESCENDING,
    MongoClient,
)
from pymongo.errors import PyMongoError


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


ALLOWED_SORT_FIELDS = frozenset(
    {
        "animal_id",
        "name",
        "breed",
        "age_in_weeks",
        "outcome_type",
        "outcome_date",
    }
)


ALLOWED_DISTINCT_FIELDS = frozenset(
    {
        "animal_type",
        "breed",
        "sex_upon_outcome",
        "outcome_type",
    }
)


class AnimalShelter:
    """
    Provide MongoDB access for the animal shelter collection.

    Database connectivity and data-access behavior remain in this class.
    Dashboard presentation, callbacks, and recommendation algorithms are
    handled by separate modules.
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
                Optional MongoDB username.

            password:
                Optional MongoDB password.

            host:
                MongoDB server hostname or IP address.

            port:
                MongoDB server port.

            db:
                MongoDB database name.

            col:
                MongoDB collection name.

        Raises:
            ValueError:
                If the connection configuration is invalid.

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

        self.database_name = db
        self.collection_name = col

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
            self.client = MongoClient(
                **connection_options
            )

            # Force an immediate connection check.
            self.client.admin.command(
                "ping"
            )

            self.database = self.client[db]
            self.collection = self.database[col]

            print(
                "Connected to MongoDB successfully: "
                f"{self.database_name}."
                f"{self.collection_name}"
            )

        except PyMongoError as error:
            # Avoid exposing credentials or a full connection string.
            raise ConnectionError(
                "Unable to connect to MongoDB. "
                "Verify that MongoDB is running and that "
                "the connection configuration is correct."
            ) from error

    # ------------------------------------------------------------------
    # CONNECTION VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_connection_settings(
        username: str | None,
        password: str | None,
        host: str,
        port: int,
        db: str,
        col: str,
    ) -> None:
        """Validate MongoDB connection values before connecting."""

        if (
            not isinstance(
                host,
                str,
            )
            or not host.strip()
        ):
            raise ValueError(
                "MongoDB host must be a non-empty string."
            )

        try:
            numeric_port = int(
                port
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                "MongoDB port must be a valid integer."
            ) from error

        if not 1 <= numeric_port <= 65535:
            raise ValueError(
                "MongoDB port must be between 1 and 65535."
            )

        if (
            not isinstance(
                db,
                str,
            )
            or not db.strip()
        ):
            raise ValueError(
                "MongoDB database name must be a "
                "non-empty string."
            )

        if (
            not isinstance(
                col,
                str,
            )
            or not col.strip()
        ):
            raise ValueError(
                "MongoDB collection name must be a "
                "non-empty string."
            )

        # Authentication values must be supplied together.
        if bool(username) != bool(password):
            raise ValueError(
                "MongoDB username and password must both "
                "be supplied or both be omitted."
            )

    # ------------------------------------------------------------------
    # ENHANCEMENT THREE QUERY VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_optional_text(
        value: str | None,
        label: str,
    ) -> str | None:
        """Return cleaned optional text after validation."""

        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):
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
        age_range: (
            tuple[float, float]
            | list[float]
            | None
        ) = None,
    ) -> dict[str, Any]:
        """
        Build a MongoDB query using approved application filters.

        Callers provide normal filter values rather than unrestricted
        MongoDB fields or operators.
        """

        query: dict[str, Any] = {}

        text_filters = {
            "animal_type": (
                animal_type,
                "Animal type",
            ),
            "breed": (
                breed,
                "Breed",
            ),
            "outcome_type": (
                outcome_type,
                "Outcome type",
            ),
            "sex_upon_outcome": (
                sex_upon_outcome,
                "Sex upon outcome",
            ),
        }

        for field, (
            value,
            label,
        ) in text_filters.items():

            cleaned = cls._clean_optional_text(
                value,
                label,
            )

            if cleaned is not None:
                query[field] = cleaned

        if age_range is not None:
            if (
                not isinstance(
                    age_range,
                    (
                        tuple,
                        list,
                    ),
                )
                or len(age_range) != 2
            ):
                raise ValueError(
                    "Age range must contain exactly two values."
                )

            try:
                minimum_age = float(
                    age_range[0]
                )

                maximum_age = float(
                    age_range[1]
                )

            except (
                TypeError,
                ValueError,
            ) as error:
                raise ValueError(
                    "Age values must be numeric."
                ) from error

            if not (
                isfinite(
                    minimum_age
                )
                and isfinite(
                    maximum_age
                )
            ):
                raise ValueError(
                    "Age values must be finite numbers."
                )

            if (
                minimum_age < 0
                or maximum_age < 0
            ):
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

        if (
            not isinstance(
                page,
                int,
            )
            or page < 1
        ):
            raise ValueError(
                "Page must be an integer greater than "
                "or equal to 1."
            )

        if (
            not isinstance(
                page_size,
                int,
            )
            or not 1 <= page_size <= 100
        ):
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        return page, page_size

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(
        self,
        data: dict[str, Any],
    ) -> bool:
        """
        Insert one document into the configured collection.

        Returns:
            True when MongoDB acknowledges the insert.
            False when the database operation fails.
        """

        if (
            not isinstance(
                data,
                dict,
            )
            or not data
        ):
            raise ValueError(
                "Create requires a non-empty dictionary."
            )

        try:
            result = self.collection.insert_one(
                data
            )

            return bool(
                result.acknowledged
            )

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Create operation failed: "
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
        Retrieve documents matching a MongoDB query.

        This method is retained for backward compatibility with the
        existing dashboard and Enhancement Two tests.
        """

        if query is None:
            query = {}

        if not isinstance(
            query,
            dict,
        ):
            raise ValueError(
                "Read query must be a dictionary."
            )

        if (
            projection is not None
            and not isinstance(
                projection,
                dict,
            )
        ):
            raise ValueError(
                "Projection must be a dictionary or None."
            )

        try:
            cursor = self.collection.find(
                query,
                projection,
            )

            return list(
                cursor
            )

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Read operation failed: "
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
        age_range: (
            tuple[float, float]
            | list[float]
            | None
        ) = None,
        page: int = 1,
        page_size: int = 25,
        sort_field: str = "animal_id",
        sort_direction: int = ASCENDING,
    ) -> dict[str, Any]:
        """
        Return projected, sorted, and paginated animal records.

        Filtering, sorting, skipping, and limiting occur inside MongoDB
        rather than after loading the entire collection into Pandas.
        """

        page, page_size = (
            self._validate_page_parameters(
                page,
                page_size,
            )
        )

        if sort_field not in ALLOWED_SORT_FIELDS:
            raise ValueError(
                f"Unsupported sort field: {sort_field}"
            )

        if sort_direction not in {
            ASCENDING,
            DESCENDING,
        }:
            raise ValueError(
                "Sort direction must be ASCENDING "
                "or DESCENDING."
            )

        query = self.build_animal_query(
            animal_type=animal_type,
            breed=breed,
            outcome_type=outcome_type,
            sex_upon_outcome=sex_upon_outcome,
            age_range=age_range,
        )

        skip_count = (
            page - 1
        ) * page_size

        try:
            total_records = (
                self.collection.count_documents(
                    query
                )
            )

            cursor = (
                self.collection.find(
                    query,
                    DASHBOARD_PROJECTION,
                )
                .sort(
                    sort_field,
                    sort_direction,
                )
                .skip(
                    skip_count
                )
                .limit(
                    page_size
                )
            )

            records = list(
                cursor
            )

            # The normalized database uses age_in_weeks.
            # Enhancement Two's dashboard and recommendation layer still
            # use age_upon_outcome_in_weeks. Supplying both maintains
            # compatibility during integration.
            for record in records:
                record[
                    "age_upon_outcome_in_weeks"
                ] = record.get(
                    "age_in_weeks"
                )

            if total_records:
                total_pages = (
                    total_records
                    + page_size
                    - 1
                ) // page_size

            else:
                total_pages = 0

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
            values = self.collection.distinct(
                field,
                query,
            )

            cleaned_values = {
                str(value).strip()
                for value in values
                if value is not None
                and str(value).strip()
            }

            return sorted(
                cleaned_values,
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
        """Calculate minimum and maximum ages with aggregation."""

        query = self.build_animal_query(
            animal_type=animal_type
        )

        pipeline = [
            {
                "$match": {
                    **query,
                    "age_in_weeks": {
                        "$ne": None,
                    },
                }
            },
            {
                "$group": {
                    "_id": None,
                    "minimum_age": {
                        "$min": "$age_in_weeks",
                    },
                    "maximum_age": {
                        "$max": "$age_in_weeks",
                    },
                }
            },
        ]

        try:
            results = list(
                self.collection.aggregate(
                    pipeline
                )
            )

            if not results:
                return None

            return (
                float(
                    results[0][
                        "minimum_age"
                    ]
                ),
                float(
                    results[0][
                        "maximum_age"
                    ]
                ),
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
        """Summarize record totals and average ages by outcome."""

        query = self.build_animal_query(
            animal_type=animal_type
        )

        pipeline = [
            {
                "$match": query,
            },
            {
                "$group": {
                    "_id": "$outcome_type",
                    "total": {
                        "$sum": 1,
                    },
                    "average_age": {
                        "$avg": "$age_in_weeks",
                    },
                }
            },
            {
                "$sort": {
                    "total": -1,
                    "_id": 1,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "outcome_type": {
                        "$ifNull": [
                            "$_id",
                            "Unknown",
                        ]
                    },
                    "total": 1,
                    "average_age": {
                        "$round": [
                            "$average_age",
                            2,
                        ]
                    },
                }
            },
        ]

        try:
            return list(
                self.collection.aggregate(
                    pipeline
                )
            )

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Outcome aggregation failed: "
                f"{type(error).__name__}"
            )

            return []

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(
        self,
        query: dict[str, Any],
        update_data: dict[str, Any],
    ) -> int:
        """
        Update documents matching a MongoDB query.

        An empty query is rejected to prevent unintentionally updating
        every document in the collection.
        """

        if (
            not isinstance(
                query,
                dict,
            )
            or not query
        ):
            raise ValueError(
                "Update requires a non-empty query. "
                "Empty update queries are not permitted."
            )

        if (
            not isinstance(
                update_data,
                dict,
            )
            or not update_data
        ):
            raise ValueError(
                "Update requires non-empty update data."
            )

        # The service controls use of $set. Callers cannot submit their
        # own MongoDB update operators through update_data.
        if any(
            str(field).startswith(
                "$"
            )
            for field in update_data
        ):
            raise ValueError(
                "Update field names may not begin with '$'."
            )

        try:
            result = self.collection.update_many(
                query,
                {
                    "$set": update_data,
                },
            )

            return int(
                result.modified_count
            )

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Update operation failed: "
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
        Delete documents matching a MongoDB query.

        An empty query is rejected to prevent accidentally deleting every
        record in the collection.
        """

        if (
            not isinstance(
                query,
                dict,
            )
            or not query
        ):
            raise ValueError(
                "Delete requires a non-empty query. "
                "Empty delete queries are not permitted."
            )

        try:
            result = self.collection.delete_many(
                query
            )

            return int(
                result.deleted_count
            )

        except PyMongoError as error:
            print(
                "[DATABASE ERROR] Delete operation failed: "
                f"{type(error).__name__}"
            )

            return 0

    # ------------------------------------------------------------------
    # CONNECTION MANAGEMENT
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True when MongoDB responds to a ping."""

        try:
            self.client.admin.command(
                "ping"
            )

            return True

        except PyMongoError:
            return False

    def close(self) -> None:
        """Close the MongoDB client connection."""

        if hasattr(
            self,
            "client",
        ):
            self.client.close()

    def __enter__(
        self,
    ) -> "AnimalShelter":
        """Allow AnimalShelter to be used as a context manager."""

        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        """Close the connection when leaving a context manager."""

        self.close()