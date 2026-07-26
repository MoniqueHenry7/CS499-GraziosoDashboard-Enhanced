"""
rescue_rules.py
---------------
Rescue recommendation rules and scoring logic for the CS 499 enhanced
Grazioso Salvare dashboard.

This module separates rescue-selection business logic from the dashboard
user interface and MongoDB database code.

The original CS 340 dashboard used fixed MongoDB queries to determine
whether an animal met a rescue profile. The enhanced version uses a
weighted recommendation system that evaluates multiple characteristics
and produces:

- A match score from 0 to 100.
- A match classification.
- A plain-language explanation of why an animal received the score.

This design makes the recommendation process more transparent to users
while improving code modularity, readability, maintainability, and
testability.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

from dataclasses import dataclass
from typing import Any


# ----------------------------------------------------------------------
# RESCUE PROFILE MODEL
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class RescueProfile:
    """
    Defines the preferred characteristics for a rescue-training category.

    Attributes:
        label:
            User-friendly name of the rescue category.

        preferred_breeds:
            Breeds considered especially suitable for the rescue type.

        min_age_weeks:
            Minimum preferred animal age in weeks.

        max_age_weeks:
            Maximum preferred animal age in weeks.

        preferred_sex:
            Preferred sex-upon-outcome value.

        preferred_outcome:
            Preferred shelter outcome.

        description:
            Plain-language explanation of the rescue profile.
    """

    label: str
    preferred_breeds: tuple[str, ...]
    min_age_weeks: float
    max_age_weeks: float
    preferred_sex: str
    preferred_outcome: str
    description: str


# ----------------------------------------------------------------------
# SCORING WEIGHTS
# ----------------------------------------------------------------------

# The total possible recommendation score is 100 points.
#
# Breed receives the greatest weight because breed characteristics are
# strongly connected to the type of rescue work identified in the
# original Grazioso Salvare requirements.
#
# Age, sex, and shelter outcome contribute additional suitability points.
#
# These weights are intentionally simple and explainable for Enhancement
# One. More advanced algorithmic optimization will be reserved for the
# Algorithms and Data Structures enhancement.

SCORE_WEIGHTS: dict[str, int] = {
    "breed": 40,
    "age": 25,
    "sex": 20,
    "outcome": 15,
}

MAX_MATCH_SCORE = sum(SCORE_WEIGHTS.values())


# ----------------------------------------------------------------------
# RESCUE PROFILES
# ----------------------------------------------------------------------

RESCUE_PROFILES: dict[str, RescueProfile] = {

    "Water Rescue": RescueProfile(
        label="Water Rescue",

        preferred_breeds=(
            "Labrador Retriever",
            "Chesapeake Bay Retriever",
            "Newfoundland",
        ),

        min_age_weeks=26,
        max_age_weeks=156,

        preferred_sex="Intact Female",

        preferred_outcome="Transfer",

        description=(
            "Water Rescue candidates are evaluated for breeds commonly "
            "associated with strong swimming ability, a preferred working "
            "age range, the preferred sex category, and a Transfer outcome."
        ),
    ),

    "Mountain or Wilderness Rescue": RescueProfile(
        label="Mountain or Wilderness Rescue",

        preferred_breeds=(
            "German Shepherd",
            "Alaskan Malamute",
            "Old English Sheepdog",
            "Siberian Husky",
            "Rottweiler",
        ),

        min_age_weeks=26,
        max_age_weeks=156,

        preferred_sex="Intact Male",

        preferred_outcome="Transfer",

        description=(
            "Mountain or Wilderness Rescue candidates are evaluated for "
            "breeds associated with strength, endurance, working ability, "
            "a preferred working age range, the preferred sex category, "
            "and a Transfer outcome."
        ),
    ),

    "Disaster Rescue or Individual Tracking": RescueProfile(
        label="Disaster Rescue or Individual Tracking",

        preferred_breeds=(
            "Doberman Pinscher",
            "German Shepherd",
            "Golden Retriever",
            "Bloodhound",
            "Rottweiler",
        ),

        min_age_weeks=20,
        max_age_weeks=300,

        preferred_sex="Intact Male",

        preferred_outcome="Transfer",

        description=(
            "Disaster Rescue or Individual Tracking candidates are "
            "evaluated for breeds associated with tracking, search, "
            "working ability, an appropriate age range, the preferred "
            "sex category, and a Transfer outcome."
        ),
    ),
}


# ----------------------------------------------------------------------
# SUPPORTED RESCUE TYPES
# ----------------------------------------------------------------------

RESET_RESCUE_TYPE = "Reset"

SUPPORTED_RESCUE_TYPES: tuple[str, ...] = (
    RESET_RESCUE_TYPE,
    *RESCUE_PROFILES.keys(),
)


# ----------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------


def normalize_text(value: Any) -> str:
    """
    Normalize a value for case-insensitive text comparison.

    Args:
        value:
            Any input value that may contain text.

    Returns:
        A stripped, case-folded string.

        None becomes an empty string.
    """

    if value is None:
        return ""

    return str(value).strip().casefold()


def safe_float(
    value: Any,
) -> float | None:
    """
    Safely convert a value to a floating-point number.

    Args:
        value:
            Value that may represent a number.

    Returns:
        Converted float when valid.
        None when the value is missing or cannot be converted.
    """

    if value is None:
        return None

    try:
        numeric_value = float(value)

    except (TypeError, ValueError):
        return None

    return numeric_value


def validate_rescue_type(
    rescue_type: str | None,
) -> None:
    """
    Validate a rescue category received from the user interface.

    Controlled validation prevents arbitrary strings from being treated
    as application rescue profiles.

    Args:
        rescue_type:
            Selected rescue category.

    Raises:
        ValueError:
            If the rescue type is unsupported.
    """

    allowed_values = {
        None,
        "",
        RESET_RESCUE_TYPE,
        *RESCUE_PROFILES.keys(),
    }

    if rescue_type not in allowed_values:
        raise ValueError(
            f"Unsupported rescue type: {rescue_type!r}"
        )


def get_rescue_profile(
    rescue_type: str | None,
) -> RescueProfile | None:
    """
    Return the rescue profile associated with a rescue category.

    Args:
        rescue_type:
            Selected rescue category.

    Returns:
        RescueProfile when a recommendation category is selected.
        None for Reset, blank, or no selection.

    Raises:
        ValueError:
            If the rescue type is unsupported.
    """

    validate_rescue_type(rescue_type)

    if rescue_type in {
        None,
        "",
        RESET_RESCUE_TYPE,
    }:
        return None

    return RESCUE_PROFILES[rescue_type]


# ----------------------------------------------------------------------
# BREED MATCHING
# ----------------------------------------------------------------------


def breed_matches(
    actual_breed: Any,
    preferred_breeds: tuple[str, ...],
) -> bool:
    """
    Determine whether an animal breed matches a preferred breed.

    The Austin Animal Center data may contain values such as:

        Labrador Retriever Mix
        German Shepherd Mix
        German Shepherd/Labrador Retriever

    Exact equality would incorrectly reject these animals.

    This function performs normalized substring matching so that a breed
    such as "Labrador Retriever Mix" can correctly satisfy a preference
    for "Labrador Retriever."

    Args:
        actual_breed:
            Breed value from the animal record.

        preferred_breeds:
            Preferred breeds for the rescue profile.

    Returns:
        True when at least one preferred breed appears in the animal's
        breed description.

        False otherwise.
    """

    normalized_actual = normalize_text(actual_breed)

    if not normalized_actual:
        return False

    for preferred_breed in preferred_breeds:

        normalized_preferred = normalize_text(
            preferred_breed
        )

        if (
            normalized_preferred
            and normalized_preferred
            in normalized_actual
        ):
            return True

    return False


def matched_preferred_breeds(
    actual_breed: Any,
    preferred_breeds: tuple[str, ...],
) -> list[str]:
    """
    Return the preferred breeds found in an animal's breed description.

    This function is useful for producing transparent recommendation
    explanations.

    Args:
        actual_breed:
            Animal breed description.

        preferred_breeds:
            Preferred breeds associated with a rescue profile.

    Returns:
        List of preferred breed names found in the animal record.
    """

    normalized_actual = normalize_text(actual_breed)

    if not normalized_actual:
        return []

    matches: list[str] = []

    for preferred_breed in preferred_breeds:

        if (
            normalize_text(preferred_breed)
            in normalized_actual
        ):
            matches.append(preferred_breed)

    return matches


# ----------------------------------------------------------------------
# INDIVIDUAL CRITERION CHECKS
# ----------------------------------------------------------------------


def age_matches(
    actual_age_weeks: Any,
    minimum_age_weeks: float,
    maximum_age_weeks: float,
) -> bool:
    """
    Determine whether an animal's age falls within the preferred range.

    Args:
        actual_age_weeks:
            Animal age in weeks.

        minimum_age_weeks:
            Minimum preferred age.

        maximum_age_weeks:
            Maximum preferred age.

    Returns:
        True if the age is valid and within the inclusive range.
        False otherwise.
    """

    age = safe_float(actual_age_weeks)

    if age is None:
        return False

    return (
        minimum_age_weeks
        <= age
        <= maximum_age_weeks
    )


def sex_matches(
    actual_sex: Any,
    preferred_sex: str,
) -> bool:
    """
    Determine whether an animal's sex category matches the profile.

    Args:
        actual_sex:
            sex_upon_outcome value from the animal record.

        preferred_sex:
            Preferred sex value from the rescue profile.

    Returns:
        True when the normalized values match.
        False otherwise.
    """

    return (
        normalize_text(actual_sex)
        == normalize_text(preferred_sex)
    )


def outcome_matches(
    actual_outcome: Any,
    preferred_outcome: str,
) -> bool:
    """
    Determine whether the animal's shelter outcome matches the profile.

    Args:
        actual_outcome:
            outcome_type from the animal record.

        preferred_outcome:
            Preferred outcome from the rescue profile.

    Returns:
        True when the values match.
        False otherwise.
    """

    return (
        normalize_text(actual_outcome)
        == normalize_text(preferred_outcome)
    )


# ----------------------------------------------------------------------
# MATCH CLASSIFICATION
# ----------------------------------------------------------------------


def classify_match(
    score: int,
) -> str:
    """
    Convert a numeric recommendation score into a readable match level.

    Classification:
        80-100: Strong Match
        55-79:  Good Match
        40-54:  Partial Match
        0-39:   Low Match

    Args:
        score:
            Recommendation score from 0 to 100.

    Returns:
        Human-readable match classification.

    Raises:
        ValueError:
            If the score is outside the valid range.
    """

    if not 0 <= score <= MAX_MATCH_SCORE:
        raise ValueError(
            f"Match score must be between 0 and "
            f"{MAX_MATCH_SCORE}."
        )

    if score >= 80:
        return "Strong Match"

    if score >= 55:
        return "Good Match"

    if score >= 40:
        return "Partial Match"

    return "Low Match"


# ----------------------------------------------------------------------
# SCORE RESULT
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class MatchResult:
    """
    Stores the result of evaluating one animal for a rescue profile.

    Attributes:
        score:
            Numeric score from 0 to 100.

        level:
            Human-readable match classification.

        reasons:
            Individual positive criteria contributing to the score.

        explanation:
            Combined plain-language explanation for display in the UI.
    """

    score: int
    level: str
    reasons: tuple[str, ...]
    explanation: str


# ----------------------------------------------------------------------
# ANIMAL SCORING
# ----------------------------------------------------------------------


def score_animal(
    animal: dict[str, Any],
    rescue_type: str | None,
) -> MatchResult:
    """
    Evaluate one animal against a selected rescue profile.

    Scoring model:

        Preferred breed       40 points
        Preferred age range   25 points
        Preferred sex         20 points
        Preferred outcome     15 points
                            ------------
        Maximum              100 points

    Args:
        animal:
            Dictionary containing an animal record.

            Expected fields include:
                breed
                age_upon_outcome_in_weeks
                sex_upon_outcome
                outcome_type

        rescue_type:
            Selected rescue category.

    Returns:
        MatchResult containing:
            score
            match level
            reasons
            explanation

        Reset or no rescue selection returns a score of zero and a
        "Not Ranked" classification.

    Raises:
        ValueError:
            If animal is not a dictionary or the rescue type is invalid.
    """

    if not isinstance(animal, dict):
        raise ValueError(
            "Animal record must be a dictionary."
        )

    profile = get_rescue_profile(rescue_type)

    # Reset/Show All mode does not rank animals.
    if profile is None:

        return MatchResult(
            score=0,
            level="Not Ranked",
            reasons=(),
            explanation=(
                "Select a rescue type to calculate "
                "a recommendation score."
            ),
        )

    score = 0

    reasons: list[str] = []

    # --------------------------------------------------------------
    # BREED
    # --------------------------------------------------------------

    breed = animal.get("breed")

    matching_breeds = matched_preferred_breeds(
        breed,
        profile.preferred_breeds,
    )

    if matching_breeds:

        score += SCORE_WEIGHTS["breed"]

        breed_text = ", ".join(
            matching_breeds
        )

        reasons.append(
            f"Preferred breed match ({breed_text})"
        )

    # --------------------------------------------------------------
    # AGE
    # --------------------------------------------------------------

    age_weeks = animal.get(
        "age_upon_outcome_in_weeks"
    )

    if age_matches(
        age_weeks,
        profile.min_age_weeks,
        profile.max_age_weeks,
    ):

        score += SCORE_WEIGHTS["age"]

        reasons.append(
            "Age is within the preferred "
            f"{profile.min_age_weeks:g}-"
            f"{profile.max_age_weeks:g} week range"
        )

    # --------------------------------------------------------------
    # SEX
    # --------------------------------------------------------------

    actual_sex = animal.get(
        "sex_upon_outcome"
    )

    if sex_matches(
        actual_sex,
        profile.preferred_sex,
    ):

        score += SCORE_WEIGHTS["sex"]

        reasons.append(
            f"Preferred sex category "
            f"({profile.preferred_sex})"
        )

    # --------------------------------------------------------------
    # OUTCOME
    # --------------------------------------------------------------

    actual_outcome = animal.get(
        "outcome_type"
    )

    if outcome_matches(
        actual_outcome,
        profile.preferred_outcome,
    ):

        score += SCORE_WEIGHTS["outcome"]

        reasons.append(
            f"Preferred shelter outcome "
            f"({profile.preferred_outcome})"
        )

    # --------------------------------------------------------------
    # CLASSIFY RESULT
    # --------------------------------------------------------------

    match_level = classify_match(score)

    # --------------------------------------------------------------
    # CREATE USER-FRIENDLY EXPLANATION
    # --------------------------------------------------------------

    if reasons:

        explanation = "; ".join(reasons)

    else:

        explanation = (
            "This animal does not currently match the "
            "preferred characteristics for the selected "
            "rescue profile."
        )

    return MatchResult(
        score=score,
        level=match_level,
        reasons=tuple(reasons),
        explanation=explanation,
    )


# ----------------------------------------------------------------------
# CONVENIENCE FUNCTION FOR DATAFRAME / SERVICE USE
# ----------------------------------------------------------------------


def score_animal_record(
    animal: dict[str, Any],
    rescue_type: str | None,
) -> dict[str, Any]:
    """
    Score an animal and return display-ready recommendation fields.

    This helper makes it easy for dashboard_service.py to add
    recommendation information to a Pandas DataFrame.

    Args:
        animal:
            Animal record dictionary.

        rescue_type:
            Selected rescue category.

    Returns:
        Dictionary containing:

            match_score
            match_level
            match_reasons
    """

    result = score_animal(
        animal,
        rescue_type,
    )

    return {
        "match_score": result.score,
        "match_level": result.level,
        "match_reasons": result.explanation,
    }


# ----------------------------------------------------------------------
# RESCUE PROFILE DISPLAY INFORMATION
# ----------------------------------------------------------------------


def get_profile_summary(
    rescue_type: str | None,
) -> dict[str, Any]:
    """
    Return display-ready information about a rescue profile.

    The dashboard can use this information to explain recommendation
    criteria to technical and nontechnical users.

    Args:
        rescue_type:
            Selected rescue category.

    Returns:
        Dictionary describing the profile.

        Reset mode returns an informational message rather than scoring
        criteria.
    """

    profile = get_rescue_profile(
        rescue_type
    )

    if profile is None:

        return {
            "label": "All Animals",
            "description": (
                "All available animal records are shown. "
                "Select a rescue type to rank animals by suitability."
            ),
            "preferred_breeds": [],
            "age_range": None,
            "preferred_sex": None,
            "preferred_outcome": None,
            "weights": SCORE_WEIGHTS.copy(),
        }

    return {
        "label": profile.label,

        "description": profile.description,

        "preferred_breeds": list(
            profile.preferred_breeds
        ),

        "age_range": (
            profile.min_age_weeks,
            profile.max_age_weeks,
        ),

        "preferred_sex":
            profile.preferred_sex,

        "preferred_outcome":
            profile.preferred_outcome,

        "weights":
            SCORE_WEIGHTS.copy(),
    }