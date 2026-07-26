"""
animal_shelter.py
-----------------
MongoDB CRUD service for the CS 499 enhanced Grazioso Salvare dashboard.

This module is based on the original AnimalShelter CRUD class created for
CS 340 Client/Server Development. It has been refactored for the CS 499
Software Design and Engineering enhancement.

Enhancements include:
- Removal of hardcoded database credentials.
- Support for authenticated and unauthenticated MongoDB connections.
- Consistent use of the configured MongoDB collection.
- Improved input validation.
- Safer update and delete operations.
- More focused exception handling.
- Clearer method names, documentation, and return values.
- Separation of database responsibilities from dashboard and
  recommendation logic.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError


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