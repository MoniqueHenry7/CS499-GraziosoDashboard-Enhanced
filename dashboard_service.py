"""
dashboard_service.py
--------------------
Application service layer for the CS 499 enhanced Grazioso Salvare
Rescue Match Recommendation Dashboard.

This module connects the MongoDB data-access layer to the rescue
recommendation logic.

Responsibilities include:
- Retrieving animal records through the AnimalShelter CRUD class.
- Cleaning database records before presentation.
- Safely removing MongoDB/internal fields from display data.
- Validating user-selected filters.
- Filtering records by breed, age, and outcome type.
- Applying rescue recommendation scoring.
- Ranking candidates from strongest to weakest match.
- Providing display-ready data for the dashboard.
- Providing helper methods for summaries and selected-animal details.

The service layer keeps business logic out of the Dash user-interface
and callback modules. This separation improves modularity,
maintainability, readability, testing, and future extensibility.

Important scope note:
This Software Design and Engineering enhancement uses normal Pandas
filtering and sorting. Advanced dictionary indexes, sets, binary search,
min-heaps, and caching are intentionally reserved for the later
Algorithms and Data Structures enhancement.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

from typing import Any

import pandas as pd

from animal_shelter import AnimalShelter
from rescue_rules import (
    RESET_RESCUE_TYPE,
    get_profile_summary,
    get_rescue_profile,
    score_animal_record,
    validate_rescue_type,
)


# ----------------------------------------------------------------------
# DISPLAY CONFIGURATION
# ----------------------------------------------------------------------

# These are the main fields displayed in the enhanced dashboard table.
#
# The service uses column names instead of fixed numeric DataFrame
# positions. This prevents map/table logic from breaking when columns
# are added, removed, or reordered.

DISPLAY_COLUMNS: tuple[str, ...] = (
    "animal_id",
    "name",
    "breed",
    "sex_upon_outcome",
    "age_upon_outcome_in_weeks",
    "outcome_type",
    "match_score",
    "match_level",
    "match_reasons",
)


# Location fields are retained internally because the map callback needs
# them, but they do not have to be displayed in the main table.

LOCATION_COLUMNS: tuple[str, ...] = (
    "location_lat",
    "location_long",
)


# Fields used by the original Austin Animal Center dataset and enhanced
# application.

EXPECTED_COLUMNS: tuple[str, ...] = (
    "animal_id",
    "animal_type",
    "name",
    "breed",
    "sex_upon_outcome",
    "age_upon_outcome_in_weeks",
    "outcome_type",
    "location_lat",
    "location_long",
)


# ----------------------------------------------------------------------
# DASHBOARD SERVICE
# ----------------------------------------------------------------------


class DashboardService:
    """
    Provides business and presentation-preparation logic for the
    Grazioso Salvare dashboard.

    The DashboardService sits between:

        AnimalShelter
            Database access

        Rescue Rules
            Recommendation/scoring logic

        Dash UI and callbacks
            Presentation and user interaction

    This prevents database, recommendation, and user-interface concerns
    from becoming tightly coupled inside one notebook or callback.
    """

    def __init__(
        self,
        shelter: AnimalShelter,
    ) -> None:
        """
        Initialize the dashboard service.

        Args:
            shelter:
                Configured AnimalShelter database-access object.

        Raises:
            ValueError:
                If shelter is not supplied.
        """

        if shelter is None:
            raise ValueError(
                "DashboardService requires an AnimalShelter instance."
            )

        self.shelter = shelter

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------

    def load_animals(
        self,
        dogs_only: bool = True,
    ) -> pd.DataFrame:
        """
        Retrieve animal records from MongoDB.

        Grazioso Salvare primarily evaluates dogs for rescue training.
        Therefore, dogs_only defaults to True.

        Args:
            dogs_only:
                When True, retrieve dog records only.

                When False, retrieve all animal records.

        Returns:
            Cleaned Pandas DataFrame.

            An empty DataFrame is returned if no records are found.
        """

        if dogs_only:
            query = {
                "animal_type": "Dog"
            }

        else:
            query = {}

        records = self.shelter.read(query)

        if not records:
            return self._empty_frame()

        frame = pd.DataFrame(records)

        return self._clean_frame(frame)

    # ------------------------------------------------------------------
    # DATA CLEANING
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_frame(
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Clean MongoDB records before dashboard processing.

        Improvements over the original artifact include:
        - Safely removing MongoDB _id.
        - Safely removing CSV-generated index columns.
        - Ensuring expected columns exist.
        - Converting age and coordinates to numeric values safely.
        - Filling missing display text where appropriate.

        Args:
            frame:
                Raw DataFrame created from MongoDB records.

        Returns:
            Cleaned copy of the DataFrame.
        """

        cleaned = frame.copy()

        # The original artifact dropped "_id" directly, which could fail
        # when the field was absent. errors="ignore" makes this operation
        # safe in either case.
        cleaned.drop(
            columns=[
                "_id",
                "Unnamed: 0",
            ],
            errors="ignore",
            inplace=True,
        )

        # Ensure expected fields exist so later code can reference columns
        # by name without relying on fixed numeric positions.
        for column in EXPECTED_COLUMNS:

            if column not in cleaned.columns:
                cleaned[column] = None

        # Normalize important text fields.
        text_columns = [
            "animal_id",
            "animal_type",
            "name",
            "breed",
            "sex_upon_outcome",
            "outcome_type",
        ]

        for column in text_columns:

            cleaned[column] = (
                cleaned[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        # Convert age into numeric form.
        #
        # Invalid or missing values become NaN instead of causing the
        # application to crash.
        cleaned[
            "age_upon_outcome_in_weeks"
        ] = pd.to_numeric(
            cleaned[
                "age_upon_outcome_in_weeks"
            ],
            errors="coerce",
        )

        # Convert geographic coordinates safely.
        cleaned["location_lat"] = pd.to_numeric(
            cleaned["location_lat"],
            errors="coerce",
        )

        cleaned["location_long"] = pd.to_numeric(
            cleaned["location_long"],
            errors="coerce",
        )

        return cleaned

    # ------------------------------------------------------------------
    # EMPTY DATAFRAME
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        """
        Create an empty DataFrame with the expected dashboard structure.

        Returns:
            Empty DataFrame containing expected and recommendation fields.
        """

        columns = list(EXPECTED_COLUMNS) + [
            "match_score",
            "match_level",
            "match_reasons",
        ]

        return pd.DataFrame(
            columns=columns
        )

    # ------------------------------------------------------------------
    # AVAILABLE FILTER OPTIONS
    # ------------------------------------------------------------------

    def available_breeds(
        self,
    ) -> list[str]:
        """
        Return alphabetically sorted dog-breed values for the UI dropdown.

        Returns:
            List of unique non-empty breed strings.
        """

        frame = self.load_animals(
            dogs_only=True
        )

        if frame.empty:
            return []

        breeds = {
            str(value).strip()
            for value in frame["breed"].dropna()
            if str(value).strip()
        }

        return sorted(
            breeds,
            key=str.casefold,
        )

    def available_outcomes(
        self,
    ) -> list[str]:
        """
        Return alphabetically sorted shelter outcomes for the UI dropdown.

        Returns:
            List of unique non-empty outcome values.
        """

        frame = self.load_animals(
            dogs_only=True
        )

        if frame.empty:
            return []

        outcomes = {
            str(value).strip()
            for value
            in frame["outcome_type"].dropna()
            if str(value).strip()
        }

        return sorted(
            outcomes,
            key=str.casefold,
        )

    def age_bounds(
        self,
    ) -> tuple[float, float]:
        """
        Determine the minimum and maximum valid dog ages in the dataset.

        Returns:
            Tuple containing:
                minimum age in weeks
                maximum age in weeks

            Returns (0.0, 1000.0) when no valid ages are available.
        """

        frame = self.load_animals(
            dogs_only=True
        )

        if (
            frame.empty
            or frame[
                "age_upon_outcome_in_weeks"
            ].dropna().empty
        ):
            return 0.0, 1000.0

        age_values = frame[
            "age_upon_outcome_in_weeks"
        ].dropna()

        minimum = max(
            0.0,
            float(age_values.min()),
        )

        maximum = max(
            minimum,
            float(age_values.max()),
        )

        return minimum, maximum

    # ------------------------------------------------------------------
    # FILTER VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_age_range(
        age_range: Any,
    ) -> tuple[float, float] | None:
        """
        Validate an optional age-range selection.

        Args:
            age_range:
                Expected to be a list or tuple containing exactly two
                numeric values:

                    [minimum_age, maximum_age]

        Returns:
            Validated numeric tuple.

            None if no age range was supplied.

        Raises:
            ValueError:
                If the value is malformed, negative, or reversed.
        """

        if age_range is None:
            return None

        if not isinstance(
            age_range,
            (list, tuple),
        ):
            raise ValueError(
                "Age range must contain a minimum and maximum value."
            )

        if len(age_range) != 2:
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

        except (TypeError, ValueError) as error:
            raise ValueError(
                "Age-range values must be numeric."
            ) from error

        if (
            minimum_age < 0
            or maximum_age < 0
        ):
            raise ValueError(
                "Age values cannot be negative."
            )

        if minimum_age > maximum_age:
            raise ValueError(
                "Minimum age cannot be greater than maximum age."
            )

        return (
            minimum_age,
            maximum_age,
        )

    @staticmethod
    def _validate_optional_text_filter(
        value: Any,
        field_name: str,
    ) -> str | None:
        """
        Validate a controlled text filter.

        Args:
            value:
                User-selected dropdown value.

            field_name:
                Human-readable filter name used in error messages.

        Returns:
            Stripped string or None.

        Raises:
            ValueError:
                If a non-string value is supplied.
        """

        if value in {
            None,
            "",
        }:
            return None

        if not isinstance(
            value,
            str,
        ):
            raise ValueError(
                f"{field_name} must be a text value."
            )

        cleaned = value.strip()

        if not cleaned:
            return None

        return cleaned

    # ------------------------------------------------------------------
    # FILTER AND RANK
    # ------------------------------------------------------------------

    def filter_and_rank(
        self,
        rescue_type: str | None = RESET_RESCUE_TYPE,
        breed: str | None = None,
        age_range: list[float] | tuple[float, float] | None = None,
        outcome_type: str | None = None,
    ) -> pd.DataFrame:
        """
        Retrieve, filter, score, and rank rescue candidates.

        Processing steps:

            1. Validate user selections.
            2. Retrieve dog records from MongoDB.
            3. Apply optional breed filter.
            4. Apply optional age-range filter.
            5. Apply optional outcome filter.
            6. Score animals when a rescue profile is selected.
            7. Rank strongest candidates first.
            8. Return display-ready results.

        The user-selected values are NOT inserted directly into MongoDB
        query expressions. Controlled selections are applied after the
        base dog dataset has been retrieved.

        This limits the amount of dynamic database-query construction
        performed during Enhancement One.

        Args:
            rescue_type:
                Selected rescue-training category.

            breed:
                Optional exact breed-description filter.

            age_range:
                Optional [minimum, maximum] age range in weeks.

            outcome_type:
                Optional exact shelter-outcome filter.

        Returns:
            Filtered and ranked DataFrame.

        Raises:
            ValueError:
                If any filter contains an invalid value.
        """

        # Validate the rescue profile using the controlled list in
        # rescue_rules.py.
        validate_rescue_type(
            rescue_type
        )

        selected_breed = (
            self._validate_optional_text_filter(
                breed,
                "Breed filter",
            )
        )

        selected_outcome = (
            self._validate_optional_text_filter(
                outcome_type,
                "Outcome filter",
            )
        )

        validated_age_range = (
            self._validate_age_range(
                age_range
            )
        )

        frame = self.load_animals(
            dogs_only=True
        )

        if frame.empty:
            return self._empty_frame()

        # --------------------------------------------------------------
        # BREED FILTER
        # --------------------------------------------------------------

        if selected_breed is not None:

            normalized_breed = (
                selected_breed.casefold()
            )

            frame = frame[
                frame["breed"]
                .astype(str)
                .str.casefold()
                == normalized_breed
            ].copy()

        # --------------------------------------------------------------
        # AGE FILTER
        # --------------------------------------------------------------

        if validated_age_range is not None:

            minimum_age, maximum_age = (
                validated_age_range
            )

            age_values = pd.to_numeric(
                frame[
                    "age_upon_outcome_in_weeks"
                ],
                errors="coerce",
            )

            frame = frame[
                age_values.between(
                    minimum_age,
                    maximum_age,
                    inclusive="both",
                )
            ].copy()

        # --------------------------------------------------------------
        # OUTCOME FILTER
        # --------------------------------------------------------------

        if selected_outcome is not None:

            normalized_outcome = (
                selected_outcome.casefold()
            )

            frame = frame[
                frame["outcome_type"]
                .astype(str)
                .str.casefold()
                == normalized_outcome
            ].copy()

        if frame.empty:
            return self._empty_frame()

        # --------------------------------------------------------------
        # RECOMMENDATION SCORING
        # --------------------------------------------------------------

        profile = get_rescue_profile(
            rescue_type
        )

        if profile is None:

            # Reset/Show All mode preserves the ability to browse records
            # without ranking them.
            frame["match_score"] = 0

            frame["match_level"] = (
                "Not Ranked"
            )

            frame["match_reasons"] = (
                "Select a rescue type to calculate "
                "a recommendation score."
            )

            # Use animal ID as a stable display order when available.
            sort_columns: list[str] = []

            if "animal_id" in frame.columns:
                sort_columns.append(
                    "animal_id"
                )

            if sort_columns:

                frame.sort_values(
                    by=sort_columns,
                    ascending=True,
                    inplace=True,
                    kind="stable",
                )

        else:

            recommendation_results = []

            # Normal iteration is intentionally used during the Software
            # Design and Engineering enhancement.
            #
            # Indexed data structures and optimized top-k selection are
            # reserved for the later Algorithms and Data Structures
            # enhancement.
            for record in frame.to_dict(
                orient="records"
            ):

                recommendation_results.append(
                    score_animal_record(
                        animal=record,
                        rescue_type=rescue_type,
                    )
                )

            recommendation_frame = (
                pd.DataFrame(
                    recommendation_results,
                    index=frame.index,
                )
            )

            frame[
                "match_score"
            ] = recommendation_frame[
                "match_score"
            ]

            frame[
                "match_level"
            ] = recommendation_frame[
                "match_level"
            ]

            frame[
                "match_reasons"
            ] = recommendation_frame[
                "match_reasons"
            ]

            # Highest recommendation scores appear first.
            #
            # Secondary fields provide predictable ordering for tied
            # scores.
            sort_fields = [
                "match_score",
            ]

            ascending_values = [
                False,
            ]

            if "name" in frame.columns:

                sort_fields.append(
                    "name"
                )

                ascending_values.append(
                    True
                )

            if "animal_id" in frame.columns:

                sort_fields.append(
                    "animal_id"
                )

                ascending_values.append(
                    True
                )

            frame.sort_values(
                by=sort_fields,
                ascending=ascending_values,
                kind="stable",
                inplace=True,
            )

        frame.reset_index(
            drop=True,
            inplace=True,
        )

        return frame

    # ------------------------------------------------------------------
    # TABLE DATA
    # ------------------------------------------------------------------

    @staticmethod
    def table_data(
        frame: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """
        Convert a DataFrame into Dash DataTable-compatible records.

        Only approved display fields are returned. MongoDB internal fields
        such as _id are not exposed to the user interface.

        Args:
            frame:
                Filtered dashboard DataFrame.

        Returns:
            List of row dictionaries.
        """

        if frame is None or frame.empty:
            return []

        available_columns = [
            column
            for column in DISPLAY_COLUMNS
            if column in frame.columns
        ]

        display_frame = frame[
            available_columns
        ].copy()

        # Replace NaN values with None so Dash can serialize the records.
        display_frame = display_frame.where(
            pd.notna(display_frame),
            None,
        )

        return display_frame.to_dict(
            orient="records"
        )

    @staticmethod
    def table_columns(
        include_recommendation_fields: bool = True,
    ) -> list[dict[str, str]]:
        """
        Return Dash DataTable column definitions.

        Numeric columns are explicitly identified so native Dash filtering
        performs numeric comparisons correctly.

        Args:
            include_recommendation_fields:
                Whether recommendation score and explanation fields should
                be displayed.

        Returns:
            Dash-compatible column definitions.
        """

        labels = {
            "animal_id": "Animal ID",
            "name": "Name",
            "breed": "Breed",
            "sex_upon_outcome": "Sex Upon Outcome",
            "age_upon_outcome_in_weeks": "Age (Weeks)",
            "outcome_type": "Outcome",
            "match_score": "Match Score",
            "match_level": "Match Level",
            "match_reasons": "Recommendation Details",
        }

        # Dash DataTable does not automatically infer the intended
        # filtering behavior for each column. Explicitly declaring numeric
        # fields ensures values such as Match Score and Age are filtered
        # numerically rather than as text.
        column_types = {
            "animal_id": "text",
            "name": "text",
            "breed": "text",
            "sex_upon_outcome": "text",
            "age_upon_outcome_in_weeks": "numeric",
            "outcome_type": "text",
            "match_score": "numeric",
            "match_level": "text",
            "match_reasons": "text",
        }

        columns = [
            "animal_id",
            "name",
            "breed",
            "sex_upon_outcome",
            "age_upon_outcome_in_weeks",
            "outcome_type",
        ]

        if include_recommendation_fields:

            columns.extend(
                [
                    "match_score",
                    "match_level",
                    "match_reasons",
                ]
            )

        return [
            {
                "name": labels[column],
                "id": column,
                "type": column_types[column],
            }
            for column in columns
        ]
    # ------------------------------------------------------------------
    # TOP RECOMMENDATION
    # ------------------------------------------------------------------

    @staticmethod
    def top_candidate(
        frame: pd.DataFrame,
    ) -> dict[str, Any] | None:
        """
        Return the strongest ranked candidate.

        Args:
            frame:
                Ranked recommendation DataFrame.

        Returns:
            Dictionary containing the top candidate.

            None when no ranked candidate is available.
        """

        if frame is None or frame.empty:
            return None

        if "match_score" not in frame.columns:
            return None

        top_row = frame.iloc[0]

        score = top_row.get(
            "match_score",
            0,
        )

        try:
            numeric_score = int(score)

        except (TypeError, ValueError):
            numeric_score = 0

        # A Reset/Show All result should not be represented as a ranked
        # recommendation.
        if (
            str(
                top_row.get(
                    "match_level",
                    ""
                )
            )
            == "Not Ranked"
        ):
            return None

        return {
            "animal_id":
                top_row.get(
                    "animal_id",
                    ""
                ),

            "name":
                top_row.get(
                    "name",
                    ""
                ),

            "breed":
                top_row.get(
                    "breed",
                    ""
                ),

            "sex_upon_outcome":
                top_row.get(
                    "sex_upon_outcome",
                    ""
                ),

            "age_upon_outcome_in_weeks":
                top_row.get(
                    "age_upon_outcome_in_weeks"
                ),

            "outcome_type":
                top_row.get(
                    "outcome_type",
                    ""
                ),

            "match_score":
                numeric_score,

            "match_level":
                top_row.get(
                    "match_level",
                    ""
                ),

            "match_reasons":
                top_row.get(
                    "match_reasons",
                    ""
                ),

            "location_lat":
                top_row.get(
                    "location_lat"
                ),

            "location_long":
                top_row.get(
                    "location_long"
                ),
        }

    # ------------------------------------------------------------------
    # RESULT SUMMARY
    # ------------------------------------------------------------------

    @staticmethod
    def result_summary(
        frame: pd.DataFrame,
        rescue_type: str | None,
    ) -> dict[str, Any]:
        """
        Build summary information for the dashboard.

        Args:
            frame:
                Current filtered/ranked results.

            rescue_type:
                Selected rescue category.

        Returns:
            Dictionary containing result counts and match statistics.
        """

        total_results = (
            0
            if frame is None
            else len(frame)
        )

        profile = get_rescue_profile(
            rescue_type
        )

        if profile is None:

            return {
                "total_results":
                    total_results,

                "strong_matches":
                    0,

                "good_matches":
                    0,

                "partial_matches":
                    0,

                "low_matches":
                    0,

                "message": (
                    f"{total_results:,} dog record"
                    f"{'' if total_results == 1 else 's'} "
                    f"available."
                ),
            }

        if (
            frame is None
            or frame.empty
            or "match_level"
            not in frame.columns
        ):

            return {
                "total_results": 0,
                "strong_matches": 0,
                "good_matches": 0,
                "partial_matches": 0,
                "low_matches": 0,
                "message": (
                    "No animals matched the current filters."
                ),
            }

        level_counts = (
            frame["match_level"]
            .value_counts()
            .to_dict()
        )

        strong_matches = int(
            level_counts.get(
                "Strong Match",
                0,
            )
        )

        good_matches = int(
            level_counts.get(
                "Good Match",
                0,
            )
        )

        partial_matches = int(
            level_counts.get(
                "Partial Match",
                0,
            )
        )

        low_matches = int(
            level_counts.get(
                "Low Match",
                0,
            )
        )

        return {
            "total_results":
                total_results,

            "strong_matches":
                strong_matches,

            "good_matches":
                good_matches,

            "partial_matches":
                partial_matches,

            "low_matches":
                low_matches,

            "message": (
                f"{total_results:,} candidate"
                f"{'' if total_results == 1 else 's'} evaluated. "
                f"{strong_matches:,} strong match"
                f"{'' if strong_matches == 1 else 'es'} found."
            ),
        }

    # ------------------------------------------------------------------
    # PROFILE INFORMATION
    # ------------------------------------------------------------------

    @staticmethod
    def profile_information(
        rescue_type: str | None,
    ) -> dict[str, Any]:
        """
        Return user-friendly information about the selected rescue profile.

        Args:
            rescue_type:
                Selected rescue category.

        Returns:
            Profile information generated by rescue_rules.py.
        """

        return get_profile_summary(
            rescue_type
        )

    # ------------------------------------------------------------------
    # TOP CANDIDATES FOR CHART
    # ------------------------------------------------------------------

    @staticmethod
    def top_candidates(
        frame: pd.DataFrame,
        limit: int = 10,
    ) -> pd.DataFrame:
        """
        Return the highest-ranked candidates for visualization.

        This method uses ordinary DataFrame sorting that was already
        completed by filter_and_rank().

        It intentionally does NOT implement the min-heap top-k algorithm
        planned for the later Algorithms and Data Structures enhancement.

        Args:
            frame:
                Ranked recommendation DataFrame.

            limit:
                Maximum number of candidates to return.

        Returns:
            DataFrame containing up to the requested number of candidates.

        Raises:
            ValueError:
                If limit is invalid.
        """

        if (
            not isinstance(limit, int)
            or limit <= 0
        ):
            raise ValueError(
                "Candidate limit must be a positive integer."
            )

        if frame is None or frame.empty:
            return pd.DataFrame()

        if "match_score" not in frame.columns:
            return pd.DataFrame()

        ranked = frame[
            frame["match_level"]
            != "Not Ranked"
        ].copy()

        if ranked.empty:
            return pd.DataFrame()

        return (
            ranked.head(limit)
            .copy()
            .reset_index(drop=True)
        )

    # ------------------------------------------------------------------
    # SELECTED ANIMAL
    # ------------------------------------------------------------------

    @staticmethod
    def selected_animal(
        frame: pd.DataFrame,
        selected_rows: list[int] | None,
    ) -> dict[str, Any] | None:
        """
        Safely retrieve the animal selected in the dashboard table.

        This replaces the original use of fixed numeric DataFrame column
        positions.

        Args:
            frame:
                Current filtered/ranked DataFrame.

            selected_rows:
                Dash DataTable selected row indices.

        Returns:
            Selected animal as a dictionary.

            None when no valid row is selected.
        """

        if (
            frame is None
            or frame.empty
            or not selected_rows
        ):
            return None

        try:
            row_index = int(
                selected_rows[0]
            )

        except (
            TypeError,
            ValueError,
            IndexError,
        ):
            return None

        if (
            row_index < 0
            or row_index >= len(frame)
        ):
            return None

        return frame.iloc[
            row_index
        ].to_dict()

    # ------------------------------------------------------------------
    # MAP COORDINATES
    # ------------------------------------------------------------------

    @staticmethod
    def valid_coordinates(
        animal: dict[str, Any] | None,
    ) -> tuple[float, float] | None:
        """
        Validate latitude and longitude for map display.

        Args:
            animal:
                Selected animal record.

        Returns:
            (latitude, longitude) tuple when coordinates are valid.

            None when geographic information is missing or invalid.
        """

        if not animal:
            return None

        latitude = animal.get(
            "location_lat"
        )

        longitude = animal.get(
            "location_long"
        )

        try:
            latitude = float(
                latitude
            )

            longitude = float(
                longitude
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if pd.isna(
            latitude
        ) or pd.isna(
            longitude
        ):
            return None

        if not (
            -90.0
            <= latitude
            <= 90.0
        ):
            return None

        if not (
            -180.0
            <= longitude
            <= 180.0
        ):
            return None

        return (
            latitude,
            longitude,
        )

    # ------------------------------------------------------------------
    # MAP DISPLAY INFORMATION
    # ------------------------------------------------------------------

    @classmethod
    def map_information(
        cls,
        animal: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """
        Prepare selected-animal information for the map callback.

        Args:
            animal:
                Selected animal record.

        Returns:
            Dictionary containing safe map-display information.

            None if valid coordinates are unavailable.
        """

        coordinates = (
            cls.valid_coordinates(
                animal
            )
        )

        if (
            not animal
            or coordinates is None
        ):
            return None

        latitude, longitude = (
            coordinates
        )

        name = str(
            animal.get(
                "name",
                ""
            )
            or "Unnamed Animal"
        ).strip()

        breed = str(
            animal.get(
                "breed",
                ""
            )
            or "Unknown Breed"
        ).strip()

        animal_id = str(
            animal.get(
                "animal_id",
                ""
            )
            or "Unknown ID"
        ).strip()

        return {
            "latitude":
                latitude,

            "longitude":
                longitude,

            "name":
                name,

            "breed":
                breed,

            "animal_id":
                animal_id,

            "popup_text": (
                f"{name} | "
                f"{animal_id} | "
                f"{breed}"
            ),
        }