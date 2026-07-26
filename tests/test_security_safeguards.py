"""
test_security_safeguards.py
---------------------------
Unit tests for selected defensive-programming and security safeguards
implemented in the enhanced Grazioso Salvare application.

These tests verify:
- Safe local configuration defaults.
- Incomplete MongoDB credentials are rejected.
- Invalid MongoDB ports are rejected.
- Empty update queries are blocked.
- Empty delete queries are blocked.
- Direct MongoDB update operators are rejected from ordinary update data.

These safeguards reduce the risk of insecure configuration,
unintentional collection-wide modifications, and uncontrolled update
operations.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

import pytest

from animal_shelter import AnimalShelter
from config import AppConfig


def test_config_uses_safe_local_defaults(
    monkeypatch,
):
    """
    When no environment variables are supplied, the application should
    use the expected local-development defaults without storing database
    credentials directly in the configuration.
    """

    environment_variables = [
        "MONGO_HOST",
        "MONGO_PORT",
        "MONGO_DB",
        "MONGO_COLLECTION",
        "MONGO_USERNAME",
        "MONGO_PASSWORD",
        "DASH_DEBUG",
    ]

    # Remove any existing values only for the duration of this test.
    for variable in environment_variables:

        monkeypatch.delenv(
            variable,
            raising=False,
        )

    config = AppConfig.from_env()

    assert config.mongo_host == "127.0.0.1"

    assert config.mongo_port == 27017

    assert config.mongo_db == "aac"

    assert config.mongo_collection == "animals"

    assert config.mongo_username is None

    assert config.mongo_password is None

    assert config.debug is False


def test_username_without_password_is_rejected(
    monkeypatch,
):
    """
    A MongoDB username without a matching password should fail
    validation.
    """

    monkeypatch.setenv(
        "MONGO_USERNAME",
        "test_user",
    )

    monkeypatch.delenv(
        "MONGO_PASSWORD",
        raising=False,
    )

    with pytest.raises(
        ValueError,
        match="username and password",
    ):

        AppConfig.from_env()


def test_password_without_username_is_rejected(
    monkeypatch,
):
    """
    A MongoDB password without a matching username should also fail
    validation.
    """

    monkeypatch.delenv(
        "MONGO_USERNAME",
        raising=False,
    )

    monkeypatch.setenv(
        "MONGO_PASSWORD",
        "test_password",
    )

    with pytest.raises(
        ValueError,
        match="username and password",
    ):

        AppConfig.from_env()


def test_non_numeric_database_port_is_rejected(
    monkeypatch,
):
    """
    MongoDB port configuration must contain a valid integer.
    """

    monkeypatch.setenv(
        "MONGO_PORT",
        "not-a-port",
    )

    with pytest.raises(
        ValueError,
        match="valid integer",
    ):

        AppConfig.from_env()


def test_out_of_range_database_port_is_rejected(
    monkeypatch,
):
    """
    MongoDB ports must remain within the valid TCP/UDP port range.
    """

    monkeypatch.setenv(
        "MONGO_PORT",
        "70000",
    )

    with pytest.raises(
        ValueError,
        match="between 1 and 65535",
    ):

        AppConfig.from_env()


def test_empty_update_query_is_blocked():
    """
    An empty MongoDB update query could unintentionally modify every
    document in the collection.

    The enhanced CRUD class should reject the request before contacting
    MongoDB.
    """

    # __new__ creates the object without running __init__.
    #
    # This lets us test validation logic without requiring a live
    # MongoDB connection.
    shelter = AnimalShelter.__new__(
        AnimalShelter
    )

    with pytest.raises(
        ValueError,
        match="non-empty query",
    ):

        shelter.update(
            {},
            {
                "name": "Changed Name",
            },
        )


def test_empty_delete_query_is_blocked():
    """
    An empty delete query could unintentionally remove every document
    from the collection.

    The enhanced CRUD class should reject this operation before MongoDB
    is contacted.
    """

    shelter = AnimalShelter.__new__(
        AnimalShelter
    )

    with pytest.raises(
        ValueError,
        match="non-empty query",
    ):

        shelter.delete(
            {}
        )


def test_empty_update_data_is_rejected():
    """
    An update request must contain actual data to modify.
    """

    shelter = AnimalShelter.__new__(
        AnimalShelter
    )

    with pytest.raises(
        ValueError,
        match="non-empty update data",
    ):

        shelter.update(
            {
                "animal_id": "A001",
            },
            {},
        )


def test_direct_mongodb_update_operator_is_blocked():
    """
    Ordinary application update data should not accept direct MongoDB
    update operators.

    AnimalShelter controls the use of $set internally.
    """

    shelter = AnimalShelter.__new__(
        AnimalShelter
    )

    with pytest.raises(
        ValueError,
        match="may not begin with",
    ):

        shelter.update(
            {
                "animal_id": "A001",
            },
            {
                "$unset": {
                    "name": "",
                }
            },
        )
