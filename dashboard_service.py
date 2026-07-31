"""Application service layer for the Grazioso Salvare dashboard.

Enhancement Two integrates RescueRecommendationEngine with dictionary
indexes, sets, binary search, bounded top-k selection, and caching.

Enhancement Three moves approved dashboard filtering, projections,
distinct-value retrieval, age aggregation, and paginated reads into
MongoDB while preserving the existing recommendation engine.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Databases
"""

from typing import Any

import pandas as pd

from animal_shelter import AnimalShelter
from recommendation import RescueRecommendationEngine
from rescue_rules import (
    RESET_RESCUE_TYPE,
    RESCUE_PROFILES,
    classify_match,
    get_profile_summary,
    get_rescue_profile,
    validate_rescue_type,
)


DISPLAY_COLUMNS: tuple[str, ...] = (
    "recommendation_rank",
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

LOCATION_COLUMNS: tuple[str, ...] = (
    "location_lat",
    "location_long",
)

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

DEFAULT_RECOMMENDATION_LIMIT = 10
MAX_ENGINE_CACHE_SIZE = 8


class DashboardService:
    """Connect database records, recommendation logic, and Dash callbacks."""

    def __init__(self, shelter: AnimalShelter) -> None:
        if shelter is None:
            raise ValueError(
                "DashboardService requires an AnimalShelter instance."
            )

        self.shelter = shelter

        # A cached engine retains its indexes and its internal
        # (rescue_type, limit) recommendation cache.
        self._engine_cache: dict[
            tuple[int, int],
            RescueRecommendationEngine,
        ] = {}

    # ------------------------------------------------------------------
    # Data loading and cleaning
    # ------------------------------------------------------------------

    def load_animals(
        self,
        dogs_only: bool = True,
        *,
        breed: str | None = None,
        age_range: (
            list[float]
            | tuple[float, float]
            | None
        ) = None,
        outcome_type: str | None = None,
    ) -> pd.DataFrame:
        """
        Retrieve projected records using database-side filtering.

        MongoDB returns records in validated pages. All matching pages
        are combined before the Enhancement Two recommendation engine
        builds its indexes and performs top-k ranking.
        """

        animal_type = (
            "Dog"
            if dogs_only
            else None
        )

        records: list[dict[str, Any]] = []

        page = 1
        page_size = 100

        while True:
            page_result = self.shelter.find_animals_page(
                animal_type=animal_type,
                breed=breed,
                outcome_type=outcome_type,
                age_range=age_range,
                page=page,
                page_size=page_size,
                sort_field="animal_id",
            )

            page_records = page_result.get(
                "records",
                [],
            )

            records.extend(page_records)

            total_pages = int(
                page_result.get(
                    "total_pages",
                    0,
                )
                or 0
            )

            if total_pages == 0 or page >= total_pages:
                break

            page += 1

        if not records:
            return self._empty_frame()

        return self._clean_frame(
            pd.DataFrame(records)
        )

    @staticmethod
    def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
        """Clean database records before dashboard processing."""

        cleaned = frame.copy()

        cleaned.drop(
            columns=["_id", "Unnamed: 0", "record_key"],
            errors="ignore",
            inplace=True,
        )

        for column in EXPECTED_COLUMNS:
            if column not in cleaned.columns:
                cleaned[column] = None

        text_columns = (
            "animal_id",
            "animal_type",
            "name",
            "breed",
            "sex_upon_outcome",
            "outcome_type",
        )

        for column in text_columns:
            cleaned[column] = (
                cleaned[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        cleaned["age_upon_outcome_in_weeks"] = pd.to_numeric(
            cleaned["age_upon_outcome_in_weeks"],
            errors="coerce",
        )

        cleaned["location_lat"] = pd.to_numeric(
            cleaned["location_lat"],
            errors="coerce",
        )

        cleaned["location_long"] = pd.to_numeric(
            cleaned["location_long"],
            errors="coerce",
        )

        for numeric_column in (
            "recommendation_rank",
            "match_score",
        ):
            if numeric_column in cleaned.columns:
                cleaned[numeric_column] = pd.to_numeric(
                    cleaned[numeric_column],
                    errors="coerce",
                )

        return cleaned

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        """Return an empty DataFrame with the expected dashboard structure."""

        return pd.DataFrame(
            columns=[
                *EXPECTED_COLUMNS,
                "recommendation_rank",
                "match_score",
                "match_level",
                "match_reasons",
            ]
        )

    # ------------------------------------------------------------------
    # UI filter options
    # ------------------------------------------------------------------

    def available_breeds(self) -> list[str]:
        """Return dog breeds directly from MongoDB."""

        return self.shelter.distinct_values(
            "breed",
            animal_type="Dog",
        )

    def available_outcomes(self) -> list[str]:
        """Return dog outcome values directly from MongoDB."""

        return self.shelter.distinct_values(
            "outcome_type",
            animal_type="Dog",
        )

    def age_bounds(self) -> tuple[float, float]:
        """Return dog age boundaries calculated by MongoDB."""

        bounds = self.shelter.age_bounds(
            animal_type="Dog"
        )

        if bounds is None:
            return 0.0, 1000.0

        minimum_age, maximum_age = bounds

        minimum_age = max(
            0.0,
            float(minimum_age),
        )

        maximum_age = max(
            minimum_age,
            float(maximum_age),
        )

        return minimum_age, maximum_age

    # ------------------------------------------------------------------
    # Filter validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_age_range(
        age_range: Any,
    ) -> tuple[float, float] | None:
        """Validate an optional [minimum, maximum] age selection."""

        if age_range is None:
            return None

        if not isinstance(age_range, (list, tuple)):
            raise ValueError(
                "Age range must contain a minimum and maximum value."
            )

        if len(age_range) != 2:
            raise ValueError(
                "Age range must contain exactly two values."
            )

        try:
            minimum_age = float(age_range[0])
            maximum_age = float(age_range[1])
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Age-range values must be numeric."
            ) from error

        if minimum_age < 0 or maximum_age < 0:
            raise ValueError("Age values cannot be negative.")

        if minimum_age > maximum_age:
            raise ValueError(
                "Minimum age cannot be greater than maximum age."
            )

        return minimum_age, maximum_age

    @staticmethod
    def _validate_optional_text_filter(
        value: Any,
        field_name: str,
    ) -> str | None:
        """Validate an optional dropdown text value."""

        if value in {None, ""}:
            return None

        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a text value.")

        cleaned = value.strip()
        return cleaned or None

    # ------------------------------------------------------------------
    # Recommendation-engine preparation and caching
    # ------------------------------------------------------------------

    @staticmethod
    def _records_for_engine(
        frame: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """Convert a DataFrame to stable records without Pandas NaN values."""

        if frame is None or frame.empty:
            return []

        engine_frame = frame.copy()

        stable_sort_fields = [
            column
            for column in ("animal_id", "name")
            if column in engine_frame.columns
        ]

        if stable_sort_fields:
            engine_frame.sort_values(
                by=stable_sort_fields,
                ascending=True,
                kind="stable",
                inplace=True,
            )

        engine_frame = (
            engine_frame
            .astype(object)
            .where(pd.notna(engine_frame), None)
        )

        return engine_frame.to_dict(orient="records")

    @staticmethod
    def _frame_fingerprint(
        frame: pd.DataFrame,
    ) -> tuple[int, int]:
        """Create a cache key for a filtered animal dataset."""

        if frame is None or frame.empty:
            return 0, 0

        signature_columns = [
            column
            for column in EXPECTED_COLUMNS
            if column in frame.columns
        ]

        signature_frame = (
            frame[signature_columns]
            .astype(object)
            .where(
                pd.notna(frame[signature_columns]),
                None,
            )
        )

        row_hashes = pd.util.hash_pandas_object(
            signature_frame,
            index=False,
        )

        return len(frame), int(row_hashes.sum())

    def _get_recommendation_engine(
        self,
        frame: pd.DataFrame,
    ) -> RescueRecommendationEngine:
        """Return or build an indexed engine for the current result set."""

        cache_key = self._frame_fingerprint(frame)
        cached_engine = self._engine_cache.get(cache_key)

        if cached_engine is not None:
            return cached_engine

        engine = RescueRecommendationEngine(
            records=self._records_for_engine(frame),
            rescue_profiles=RESCUE_PROFILES,
        )

        if len(self._engine_cache) >= MAX_ENGINE_CACHE_SIZE:
            oldest_key = next(iter(self._engine_cache))
            self._engine_cache.pop(oldest_key, None)

        self._engine_cache[cache_key] = engine
        return engine

    def clear_recommendation_cache(self) -> None:
        """Clear cached engines after a known database change."""

        self._engine_cache.clear()

    # ------------------------------------------------------------------
    # Filtering and ranking
    # ------------------------------------------------------------------

    def filter_and_rank(
        self,
        rescue_type: str | None = RESET_RESCUE_TYPE,
        breed: str | None = None,
        age_range: list[float] | tuple[float, float] | None = None,
        outcome_type: str | None = None,
        recommendation_limit: int = DEFAULT_RECOMMENDATION_LIMIT,
    ) -> pd.DataFrame:
        """Filter records and return Reset results or top-k recommendations."""

        validate_rescue_type(rescue_type)

        if (
            not isinstance(recommendation_limit, int)
            or recommendation_limit <= 0
        ):
            raise ValueError(
                "Recommendation limit must be a positive integer."
            )

        selected_breed = self._validate_optional_text_filter(
            breed,
            "Breed filter",
        )

        selected_outcome = self._validate_optional_text_filter(
            outcome_type,
            "Outcome filter",
        )

        validated_age_range = self._validate_age_range(age_range)

        frame = self.load_animals(
            dogs_only=True,
            breed=selected_breed,
            age_range=validated_age_range,
            outcome_type=selected_outcome,
        )

        if frame.empty:
            return self._empty_frame()

        profile = get_rescue_profile(rescue_type)

        if profile is None:
            frame["recommendation_rank"] = None
            frame["match_score"] = 0
            frame["match_level"] = "Not Ranked"
            frame["match_reasons"] = (
                "Select a rescue type to calculate "
                "a recommendation score."
            )

            if "animal_id" in frame.columns:
                frame.sort_values(
                    by=["animal_id"],
                    ascending=True,
                    kind="stable",
                    inplace=True,
                )

            return frame.reset_index(drop=True)

        engine = self._get_recommendation_engine(frame)
        result_limit = min(recommendation_limit, len(frame))

        # The engine was built from the already-filtered DataFrame, so the
        # optional dashboard filters remain hard constraints while the
        # engine performs indexed candidate selection and bounded top-k
        # ranking within that filtered record set.
        recommendation_records = engine.recommend(
            rescue_type=str(rescue_type),
            limit=result_limit,
        )

        if not recommendation_records:
            return self._empty_frame()

        ranked = pd.DataFrame(recommendation_records)

        ranked.drop(
            columns=["_id", "record_key"],
            errors="ignore",
            inplace=True,
        )

        ranked = self._clean_frame(ranked)

        ranked["recommendation_rank"] = pd.to_numeric(
            ranked["recommendation_rank"],
            errors="coerce",
        ).fillna(0).astype(int)

        ranked["match_score"] = pd.to_numeric(
            ranked["match_score"],
            errors="coerce",
        ).fillna(0.0)

        ranked["match_level"] = [
            classify_match(float(score))
            for score in ranked["match_score"]
        ]

        if "match_reasons" not in ranked.columns:
            ranked["match_reasons"] = ""

        ranked.sort_values(
            by=["recommendation_rank"],
            ascending=True,
            kind="stable",
            inplace=True,
        )

        return ranked.reset_index(drop=True)

    # ------------------------------------------------------------------
    # DataTable helpers
    # ------------------------------------------------------------------

    @staticmethod
    def table_data(
        frame: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """Convert approved fields to Dash DataTable records."""

        if frame is None or frame.empty:
            return []

        available_columns = [
            column
            for column in DISPLAY_COLUMNS
            if column in frame.columns
        ]

        display_frame = (
            frame[available_columns]
            .copy()
            .astype(object)
            .where(
                pd.notna(frame[available_columns]),
                None,
            )
        )

        return display_frame.to_dict(orient="records")

    @staticmethod
    def table_columns(
        include_recommendation_fields: bool = True,
    ) -> list[dict[str, str]]:
        """Return typed Dash DataTable column definitions."""

        labels = {
            "recommendation_rank": "Rank",
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

        column_types = {
            "recommendation_rank": "numeric",
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

        base_columns = [
            "animal_id",
            "name",
            "breed",
            "sex_upon_outcome",
            "age_upon_outcome_in_weeks",
            "outcome_type",
        ]

        columns = (
            [
                "recommendation_rank",
                *base_columns,
                "match_score",
                "match_level",
                "match_reasons",
            ]
            if include_recommendation_fields
            else base_columns
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
    # Recommendation and summary helpers
    # ------------------------------------------------------------------

    @staticmethod
    def top_candidate(
        frame: pd.DataFrame,
    ) -> dict[str, Any] | None:
        """Return the first ranked candidate or None."""

        if frame is None or frame.empty:
            return None

        if "match_score" not in frame.columns:
            return None

        top_row = frame.iloc[0]

        if str(top_row.get("match_level", "")) == "Not Ranked":
            return None

        try:
            score_value = float(top_row.get("match_score", 0))
            score: int | float = (
                int(score_value)
                if score_value.is_integer()
                else score_value
            )
        except (TypeError, ValueError):
            score = 0

        return {
            "recommendation_rank": top_row.get("recommendation_rank"),
            "animal_id": top_row.get("animal_id", ""),
            "name": top_row.get("name", ""),
            "breed": top_row.get("breed", ""),
            "sex_upon_outcome": top_row.get("sex_upon_outcome", ""),
            "age_upon_outcome_in_weeks": top_row.get(
                "age_upon_outcome_in_weeks"
            ),
            "outcome_type": top_row.get("outcome_type", ""),
            "match_score": score,
            "match_level": top_row.get("match_level", ""),
            "match_reasons": top_row.get("match_reasons", ""),
            "location_lat": top_row.get("location_lat"),
            "location_long": top_row.get("location_long"),
        }

    @staticmethod
    def result_summary(
        frame: pd.DataFrame,
        rescue_type: str | None,
    ) -> dict[str, Any]:
        """Return result counts and recommendation-level statistics."""

        total_results = 0 if frame is None else len(frame)
        profile = get_rescue_profile(rescue_type)

        if profile is None:
            return {
                "total_results": total_results,
                "strong_matches": 0,
                "good_matches": 0,
                "partial_matches": 0,
                "low_matches": 0,
                "message": (
                    f"{total_results:,} dog record"
                    f"{'' if total_results == 1 else 's'} available."
                ),
            }

        if (
            frame is None
            or frame.empty
            or "match_level" not in frame.columns
        ):
            return {
                "total_results": 0,
                "strong_matches": 0,
                "good_matches": 0,
                "partial_matches": 0,
                "low_matches": 0,
                "message": "No animals matched the current filters.",
            }

        counts = frame["match_level"].value_counts().to_dict()
        strong = int(counts.get("Strong Match", 0))
        good = int(counts.get("Good Match", 0))
        partial = int(counts.get("Partial Match", 0))
        low = int(counts.get("Low Match", 0))

        return {
            "total_results": total_results,
            "strong_matches": strong,
            "good_matches": good,
            "partial_matches": partial,
            "low_matches": low,
            "message": (
                f"{total_results:,} top-ranked candidate"
                f"{'' if total_results == 1 else 's'} displayed. "
                f"{strong:,} strong match"
                f"{'' if strong == 1 else 'es'} found."
            ),
        }

    @staticmethod
    def profile_information(
        rescue_type: str | None,
    ) -> dict[str, Any]:
        """Return display-ready information for a rescue profile."""

        return get_profile_summary(rescue_type)

    @staticmethod
    def top_candidates(
        frame: pd.DataFrame,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Return leading ranked rows for the recommendation chart."""

        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(
                "Candidate limit must be a positive integer."
            )

        if frame is None or frame.empty:
            return pd.DataFrame()

        if "match_score" not in frame.columns:
            return pd.DataFrame()

        ranked = frame[
            frame["match_level"] != "Not Ranked"
        ].copy()

        if ranked.empty:
            return pd.DataFrame()

        return ranked.head(limit).copy().reset_index(drop=True)

    # ------------------------------------------------------------------
    # Selected-row and map helpers
    # ------------------------------------------------------------------

    @staticmethod
    def selected_animal(
        frame: pd.DataFrame,
        selected_rows: list[int] | None,
    ) -> dict[str, Any] | None:
        """Safely retrieve the selected DataTable row."""

        if frame is None or frame.empty or not selected_rows:
            return None

        try:
            row_index = int(selected_rows[0])
        except (TypeError, ValueError, IndexError):
            return None

        if row_index < 0 or row_index >= len(frame):
            return None

        return frame.iloc[row_index].to_dict()

    @staticmethod
    def valid_coordinates(
        animal: dict[str, Any] | None,
    ) -> tuple[float, float] | None:
        """Return validated latitude and longitude values."""

        if not animal:
            return None

        try:
            latitude = float(animal.get("location_lat"))
            longitude = float(animal.get("location_long"))
        except (TypeError, ValueError):
            return None

        if pd.isna(latitude) or pd.isna(longitude):
            return None

        if not -90.0 <= latitude <= 90.0:
            return None

        if not -180.0 <= longitude <= 180.0:
            return None

        return latitude, longitude

    @classmethod
    def map_information(
        cls,
        animal: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Prepare selected-animal information for the map callback."""

        coordinates = cls.valid_coordinates(animal)

        if not animal or coordinates is None:
            return None

        latitude, longitude = coordinates

        name = str(
            animal.get("name", "") or "Unnamed Animal"
        ).strip()

        breed = str(
            animal.get("breed", "") or "Unknown Breed"
        ).strip()

        animal_id = str(
            animal.get("animal_id", "") or "Unknown ID"
        ).strip()

        return {
            "latitude": latitude,
            "longitude": longitude,
            "name": name,
            "breed": breed,
            "animal_id": animal_id,
            "popup_text": f"{name} | {animal_id} | {breed}",
        }