"""
test_security_safeguards.py
---------------------------
Security and defensive-programming tests for the enhanced Grazioso
Salvare dashboard.

These tests verify that:

- Local MongoDB defaults are safe and predictable.
- The validated animals_enhanced collection is used by default.
- MongoDB credentials must be supplied together.
- Invalid MongoDB ports are rejected.
- Empty update and delete queries are rejected.
- Empty update data is rejected.
- Callers cannot submit MongoDB update operators directly.

The database validation tests use AnimalShelter.__new__() so they do not
create a live MongoDB connection.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Databases
"""

import pytest

from animal_shelter import AnimalShelter
from config import AppConfig


# ----------------------------------------------------------------------
# TEST HELPERS
# ----------------------------------------------------------------------


def clear_mongodb_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Remove MongoDB environment variables before configuration tests.

    Clearing the variables ensures that each test evaluates only the
    settings explicitly supplied by that test.
    """

    environment_variables = (
        "MONGO_HOST",
        "MONGO_PORT",
        "MONGO_DB",
        "MONGO_DATABASE",
        "MONGO_COLLECTION",
        "MONGO_USERNAME",
        "MONGO_PASSWORD",
    )

    for variable_name in environment_variables:
        monkeypatch.delenv(
            variable_name,
            raising=False,
        )


@pytest.fixture
def uninitialized_shelter() -> AnimalShelter:
    """
    Return an AnimalShelter instance without opening MongoDB.

    The tested safeguards execute before a database collection is used,
    so calling __init__() is unnecessary.
    """

    return AnimalShelter.__new__(
        AnimalShelter
    )


# ----------------------------------------------------------------------
# CONFIGURATION SAFEGUARDS
# ----------------------------------------------------------------------


def test_config_uses_safe_local_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Local development should use predictable, non-secret defaults.

    Enhancement Three uses the validated and indexed collection rather
    than the original source collection.
    """

    clear_mongodb_environment(
        monkeypatch
    )

    config = AppConfig.from_env()

    assert config.mongo_host == "127.0.0.1"
    assert config.mongo_port == 27017
    assert config.mongo_db == "aac"

    assert (
        config.mongo_collection
        == "animals_enhanced"
    )

    assert config.mongo_username is None
    assert config.mongo_password is None


@pytest.mark.parametrize(
    (
        "username",
        "password",
    ),
    [
        (
            "test-user",
            None,
        ),
        (
            None,
            "test-password",
        ),
    ],
)
def test_config_requires_complete_credentials(
    monkeypatch: pytest.MonkeyPatch,
    username: str | None,
    password: str | None,
) -> None:
    """
    A username and password must be supplied together.

    Supplying only one authentication value could create an incomplete
    or misleading MongoDB connection configuration.
    """

    clear_mongodb_environment(
        monkeypatch
    )

    if username is not None:
        monkeypatch.setenv(
            "MONGO_USERNAME",
            username,
        )

    if password is not None:
        monkeypatch.setenv(
            "MONGO_PASSWORD",
            password,
        )

    with pytest.raises(
        ValueError,
        match="both",
    ):
        AppConfig.from_env()


def test_config_rejects_nonnumeric_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A MongoDB port must be convertible to an integer.
    """

    clear_mongodb_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "MONGO_PORT",
        "not-a-number",
    )

    with pytest.raises(
        ValueError,
        match="integer",
    ):
        AppConfig.from_env()


@pytest.mark.parametrize(
    "invalid_port",
    [
        "0",
        "-1",
        "65536",
    ],
)
def test_config_rejects_out_of_range_port(
    monkeypatch: pytest.MonkeyPatch,
    invalid_port: str,
) -> None:
    """
    A MongoDB port must fall within the valid network-port range.
    """

    clear_mongodb_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "MONGO_PORT",
        invalid_port,
    )

    with pytest.raises(
        ValueError,
        match="between",
    ):
        AppConfig.from_env()


# ----------------------------------------------------------------------
# DESTRUCTIVE-OPERATION SAFEGUARDS
# ----------------------------------------------------------------------


def test_update_rejects_empty_query(
    uninitialized_shelter: AnimalShelter,
) -> None:
    """
    An empty update query could modify every document in a collection.
    """

    with pytest.raises(
        ValueError,
        match="non-empty query",
    ):
        uninitialized_shelter.update(
            {},
            {
                "name": "Updated Name",
            },
        )


def test_delete_rejects_empty_query(
    uninitialized_shelter: AnimalShelter,
) -> None:
    """
    An empty delete query could remove every document in a collection.
    """

    with pytest.raises(
        ValueError,
        match="non-empty query",
    ):
        uninitialized_shelter.delete(
            {}
        )


def test_update_rejects_empty_update_data(
    uninitialized_shelter: AnimalShelter,
) -> None:
    """
    An update operation must contain at least one field to change.
    """

    with pytest.raises(
        ValueError,
        match="non-empty update data",
    ):
        uninitialized_shelter.update(
            {
                "animal_id": "A001",
            },
            {},
        )


def test_update_rejects_direct_mongodb_operator(
    uninitialized_shelter: AnimalShelter,
) -> None:
    """
    Callers cannot submit MongoDB update operators directly.

    AnimalShelter controls the use of $set so that updates follow one
    predictable structure.
    """

    with pytest.raises(
        ValueError,
        match="may not begin",
    ):
        uninitialized_shelter.update(
            {
                "animal_id": "A001",
            },
            {
                "$set": {
                    "name": "Unsafe Update",
                }
            },
        )