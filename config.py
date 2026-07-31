"""
config.py
---------
Configuration settings for the CS 499 enhanced Grazioso Salvare dashboard.

This module keeps environment-specific settings separate from the main
application code. Database credentials and connection settings can be
supplied through environment variables instead of being hardcoded directly
into the application.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    """
    Stores application and MongoDB configuration values.

    The default values support a locally running MongoDB instance.
    Environment variables can override these defaults when the application
    is deployed or moved to a different development environment.
    """

    mongo_host: str = "127.0.0.1"
    mongo_port: int = 27017
    mongo_db: str = "aac"
    mongo_collection: str = "animals_enhanced"

    # Authentication is optional for the current local development
    # environment but can be supplied through environment variables.
    mongo_username: str | None = None
    mongo_password: str | None = None

    # Dash debug mode should normally remain disabled for the final artifact.
    debug: bool = False

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Create an AppConfig object using environment variables.

        Environment variables:
            MONGO_HOST
            MONGO_PORT
            MONGO_DB
            MONGO_COLLECTION
            MONGO_USERNAME
            MONGO_PASSWORD
            DASH_DEBUG

        Returns:
            AppConfig: Validated application configuration.

        Raises:
            ValueError:
                If only one MongoDB credential is provided or if the
                MongoDB port is invalid.
        """

        # Read optional MongoDB credentials.
        # Empty strings are converted to None.
        username = os.getenv("MONGO_USERNAME", "").strip() or None
        password = os.getenv("MONGO_PASSWORD", "").strip() or None

        # Username and password must either both be supplied or both omitted.
        if bool(username) != bool(password):
            raise ValueError(
                "MongoDB username and password must both be supplied "
                "or both be omitted."
            )

        # Validate the MongoDB port before creating the configuration.
        try:
            mongo_port = int(os.getenv("MONGO_PORT", "27017"))
        except ValueError as error:
            raise ValueError(
                "MONGO_PORT must contain a valid integer."
            ) from error

        if not 1 <= mongo_port <= 65535:
            raise ValueError(
                "MONGO_PORT must be between 1 and 65535."
            )

        # Interpret several common true values for Dash debug mode.
        debug_value = os.getenv("DASH_DEBUG", "false").strip().lower()

        debug = debug_value in {
            "true",
            "1",
            "yes",
            "on",
        }

        return cls(
            mongo_host=os.getenv(
                "MONGO_HOST",
                "127.0.0.1"
            ).strip(),

            mongo_port=mongo_port,

            mongo_db=os.getenv(
                "MONGO_DB",
                "aac"
            ).strip(),

            mongo_collection=os.getenv(
                "MONGO_COLLECTION",
                "animals_enhanced"
            ).strip(),

            mongo_username=username,

            mongo_password=password,

            debug=debug,
        )


# Create the default application configuration when this module is imported.
#
# Other modules can use:
#
#     from config import CONFIG
#
# instead of repeatedly calling AppConfig.from_env().
CONFIG = AppConfig.from_env()