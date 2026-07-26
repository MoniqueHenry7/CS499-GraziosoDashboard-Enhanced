"""
test_csv_smoke.py
-----------------
Real-data smoke tests for the CS 499 enhanced Grazioso Salvare
Rescue Match Recommendation Dashboard.

These tests use the actual Austin Animal Center CSV from the original
CS 340 artifact.

The smoke tests verify:
- The real artifact dataset can be loaded.
- Dog records exist in the dataset.
- All three rescue profiles can process real animal records.
- Recommendation scores remain within the valid 0-100 range.
- Each rescue profile produces meaningful candidate matches.
- A highest-scoring candidate can be identified for each profile.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

from pathlib import Path

import pandas as pd
import pytest

from rescue_rules import (
    RESCUE_PROFILES,
    score_animal,
)


def find_dataset() -> Path | None:
    """
    Search expected project locations for the Austin Animal Center CSV.

    Returns:
        Path to the dataset when found.
        None when the CSV cannot be located.
    """

    # tests/test_csv_smoke.py
    #        ↓
    # Enhanced/
    enhanced_dir = (
        Path(__file__)
        .resolve()
        .parents[1]
    )

    # Main working project directory,
    # which is one level above Enhanced.
    project_dir = enhanced_dir.parent

    possible_paths = [
        # Dataset inside Enhanced.
        enhanced_dir
        / "aac_shelter_outcomes.csv",

        enhanced_dir
        / "aac_shelter_outcomes(1).csv",

        # Dataset one directory above Enhanced.
        project_dir
        / "aac_shelter_outcomes.csv",

        project_dir
        / "aac_shelter_outcomes(1).csv",

        # Optional supporting_files locations.
        enhanced_dir
        / "supporting_files"
        / "aac_shelter_outcomes.csv",

        project_dir
        / "supporting_files"
        / "aac_shelter_outcomes.csv",
    ]

    for path in possible_paths:

        if (
            path.exists()
            and path.is_file()
        ):
            return path

    return None


@pytest.fixture(scope="module")
def real_dog_records():
    """
    Load real dog records from the Austin Animal Center dataset.

    The test is skipped rather than failed if the CSV cannot be found.
    """

    dataset_path = find_dataset()

    if dataset_path is None:

        pytest.skip(
            "Austin Animal Center CSV was not found "
            "in the expected project locations."
        )

    frame = pd.read_csv(
        dataset_path
    )

    assert not frame.empty, (
        "The Austin Animal Center CSV is empty."
    )

    assert "animal_type" in frame.columns, (
        "The dataset is missing the animal_type column."
    )

    dogs = frame[
        frame["animal_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
        == "dog"
    ].copy()

    assert not dogs.empty, (
        "The dataset does not contain any dog records."
    )

    return dogs.to_dict(
        orient="records"
    )


def test_real_dataset_contains_dog_records(
    real_dog_records,
):
    """
    Confirm that the real artifact dataset contains usable dog records.
    """

    assert len(
        real_dog_records
    ) > 0


@pytest.mark.parametrize(
    "rescue_type",
    list(
        RESCUE_PROFILES.keys()
    ),
)
def test_real_dataset_produces_valid_scores(
    real_dog_records,
    rescue_type,
):
    """
    Score real dog records for every configured rescue profile.

    Every recommendation score must remain between zero and 100.
    """

    scores = [
        score_animal(
            animal,
            rescue_type,
        ).score
        for animal in real_dog_records
    ]

    assert scores

    assert min(scores) >= 0

    assert max(scores) <= 100


@pytest.mark.parametrize(
    "rescue_type",
    list(
        RESCUE_PROFILES.keys()
    ),
)
def test_each_rescue_profile_finds_meaningful_candidates(
    real_dog_records,
    rescue_type,
):
    """
    Confirm that the real dataset contains at least one meaningful
    candidate for every rescue profile.

    A score of 40 or greater means at least one significant rescue
    criterion was matched.
    """

    scores = [
        score_animal(
            animal,
            rescue_type,
        ).score
        for animal in real_dog_records
    ]

    assert max(scores) >= 40, (
        f"No meaningful candidates were found for "
        f"{rescue_type}."
    )


@pytest.mark.parametrize(
    "rescue_type",
    list(
        RESCUE_PROFILES.keys()
    ),
)
def test_each_rescue_profile_can_identify_top_candidate(
    real_dog_records,
    rescue_type,
):
    """
    Confirm that a highest-scoring real candidate can be identified for
    every rescue profile.
    """

    scored_candidates = [
        (
            score_animal(
                animal,
                rescue_type,
            ).score,
            animal,
        )
        for animal in real_dog_records
    ]

    best_score, best_animal = max(
        scored_candidates,
        key=lambda item: item[0],
    )

    assert best_animal is not None

    assert 0 <= best_score <= 100

    assert best_score >= 40
