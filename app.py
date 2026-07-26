"""
app.py
------
Application entry point for the CS 499 enhanced Grazioso Salvare
Rescue Match Recommendation Dashboard.

This module is responsible for assembling the application's separate
software components.

Responsibilities include:
- Loading application configuration.
- Creating the MongoDB AnimalShelter data-access object.
- Creating the DashboardService business-logic layer.
- Retrieving dynamic filter options from the database.
- Building the Dash user interface.
- Registering dashboard callbacks.
- Starting the Dash application.

The enhanced architecture separates database access, rescue scoring,
business logic, presentation, and callbacks into individual modules.

Application structure:

    config.py
        ↓
    animal_shelter.py
        ↓
    dashboard_service.py ← rescue_rules.py
        ↓
    app.py
       ↙   ↘
    ui.py  callbacks.py

This modular design improves maintainability, readability, testing,
security, and future extensibility compared with the original
single-notebook implementation.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

from __future__ import annotations

from pathlib import Path

from dash import Dash

from animal_shelter import AnimalShelter
from callbacks import register_callbacks
from config import AppConfig
from dashboard_service import DashboardService
from ui import build_layout


# ----------------------------------------------------------------------
# APPLICATION PATHS
# ----------------------------------------------------------------------

# Directory containing this app.py file.
BASE_DIR = Path(__file__).resolve().parent


# ----------------------------------------------------------------------
# LOGO HELPER
# ----------------------------------------------------------------------


def find_logo_path() -> Path | None:
    """
    Locate the Grazioso Salvare logo used by the dashboard.

    The helper checks several possible filenames so that the application
    can still start if the supplied artifact retained its original file
    name.

    Returns:
        Path to the first matching logo file.

        None if no supported logo file is found.

    Notes:
        The user interface is designed to continue loading even when the
        logo file is unavailable.
    """

    possible_logos = (
        "Grazioso Salvare Logo.png",
        "Grazioso Salvare Logo(1).png",
        "Grazioso_Salvare_Logo.png",
    )

    for filename in possible_logos:

        candidate = (
            BASE_DIR
            / filename
        )

        if (
            candidate.exists()
            and candidate.is_file()
        ):
            return candidate

    return None


# ----------------------------------------------------------------------
# DATABASE CREATION
# ----------------------------------------------------------------------


def create_shelter(
    config: AppConfig,
) -> AnimalShelter:
    """
    Create the application's MongoDB data-access object.

    Args:
        config:
            Validated AppConfig containing MongoDB settings.

    Returns:
        Connected AnimalShelter instance.

    Raises:
        ConnectionError:
            If MongoDB cannot be reached.

        ValueError:
            If database configuration is invalid.
    """

    return AnimalShelter(
        username=(
            config.mongo_username
        ),

        password=(
            config.mongo_password
        ),

        host=(
            config.mongo_host
        ),

        port=(
            config.mongo_port
        ),

        db=(
            config.mongo_db
        ),

        col=(
            config.mongo_collection
        ),
    )


# ----------------------------------------------------------------------
# APPLICATION FACTORY
# ----------------------------------------------------------------------


def create_app(
    config: AppConfig | None = None,
) -> Dash:
    """
    Create and configure the Grazioso Salvare Dash application.

    Using an application-factory function keeps application construction
    separate from application startup. This design makes the software
    easier to test, reuse, and launch from either:

        python app.py

    or:

        Jupyter Notebook

    Args:
        config:
            Optional AppConfig instance.

            When omitted, configuration is loaded from environment
            variables using AppConfig.from_env().

    Returns:
        Fully configured Dash application.

    Raises:
        ValueError:
            If application or database configuration is invalid.

        ConnectionError:
            If MongoDB cannot be reached.
    """

    # ------------------------------------------------------------------
    # LOAD CONFIGURATION
    # ------------------------------------------------------------------

    if config is None:

        config = (
            AppConfig.from_env()
        )

    # ------------------------------------------------------------------
    # CREATE DATABASE LAYER
    # ------------------------------------------------------------------

    shelter = create_shelter(
        config
    )

    # ------------------------------------------------------------------
    # CREATE SERVICE LAYER
    # ------------------------------------------------------------------

    service = DashboardService(
        shelter
    )

    # ------------------------------------------------------------------
    # RETRIEVE FILTER OPTIONS
    # ------------------------------------------------------------------

    # These values come from the actual database rather than being
    # manually duplicated inside the user-interface module.

    available_breeds = (
        service.available_breeds()
    )

    available_outcomes = (
        service.available_outcomes()
    )

    age_bounds = (
        service.age_bounds()
    )

    # ------------------------------------------------------------------
    # LOCATE BRANDING ASSET
    # ------------------------------------------------------------------

    logo_path = find_logo_path()

    # ------------------------------------------------------------------
    # CREATE DASH APPLICATION
    # ------------------------------------------------------------------

    app = Dash(
        __name__,

        title=(
            "Grazioso Salvare "
            "Rescue Match Dashboard"
        ),

        update_title=(
            "Updating rescue candidates..."
        ),
    )

    # ------------------------------------------------------------------
    # BUILD USER INTERFACE
    # ------------------------------------------------------------------

    app.layout = build_layout(
        available_breeds=(
            available_breeds
        ),

        available_outcomes=(
            available_outcomes
        ),

        age_bounds=(
            age_bounds
        ),

        logo_path=(
            logo_path
        ),
    )

    # ------------------------------------------------------------------
    # REGISTER CALLBACKS
    # ------------------------------------------------------------------

    register_callbacks(
        app=app,
        service=service,
    )

    # ------------------------------------------------------------------
    # STORE SERVICE REFERENCES
    # ------------------------------------------------------------------

    # These references are attached to the Dash application's server
    # configuration so they remain available for application shutdown,
    # debugging, or future testing without relying on global variables.

    app.server.config[
        "ANIMAL_SHELTER_SERVICE"
    ] = shelter

    app.server.config[
        "DASHBOARD_SERVICE"
    ] = service

    return app


# ----------------------------------------------------------------------
# APPLICATION STARTUP
# ----------------------------------------------------------------------


def main() -> None:
    """
    Start the enhanced Grazioso Salvare dashboard.

    Configuration is loaded from environment variables when available.

    The current local development defaults are:

        MongoDB Host:       127.0.0.1
        MongoDB Port:       27017
        Database:           aac
        Collection:         animals
        Authentication:     None
        Dash Debug:         False
    """

    try:

        # Load and validate configuration.
        config = (
            AppConfig.from_env()
        )

        # Build the complete application.
        app = create_app(
            config
        )

        print(
            "\n"
            "Grazioso Salvare Rescue Match "
            "Recommendation Dashboard"
        )

        print(
            "---------------------------------------------"
        )

        print(
            f"MongoDB database: "
            f"{config.mongo_db}"
        )

        print(
            f"MongoDB collection: "
            f"{config.mongo_collection}"
        )

        print(
            "Dashboard address: "
            "http://127.0.0.1:8050/"
        )

        print(
            "Press Control+C in the terminal "
            "to stop the application."
        )

        print()

        # Start the Dash development server.
        #
        # Debug mode defaults to False and can be controlled through the
        # DASH_DEBUG environment variable.
        app.run(
            host="127.0.0.1",
            port=8050,
            debug=config.debug,
        )

    except ValueError as error:

        # Configuration errors are safe to print because the messages
        # intentionally avoid exposing database credentials.

        print(
            "\n[CONFIGURATION ERROR]"
        )

        print(
            str(error)
        )

        print(
            "\nThe application could not start. "
            "Review the configuration settings "
            "and try again."
        )

    except ConnectionError:

        # Do not print the underlying MongoDB exception because it may
        # reveal unnecessary internal connection information.

        print(
            "\n[DATABASE CONNECTION ERROR]"
        )

        print(
            "The Grazioso Salvare dashboard could not "
            "connect to MongoDB."
        )

        print(
            "\nVerify that:"
        )

        print(
            "1. MongoDB is running."
        )

        print(
            "2. The 'aac' database exists."
        )

        print(
            "3. The 'animals' collection exists."
        )

        print(
            "4. The connection settings are correct."
        )

    except KeyboardInterrupt:

        print(
            "\nDashboard stopped by user."
        )


# ----------------------------------------------------------------------
# COMMAND-LINE ENTRY POINT
# ----------------------------------------------------------------------


if __name__ == "__main__":

    main()        