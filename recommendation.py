"""Algorithms and data structures for rescue recommendations.

This module builds reusable indexes from animal records, identifies
appropriate rescue candidates, calculates weighted suitability scores,
and uses a bounded min-heap to retain the highest-ranked animals.
"""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from heapq import heappush, heapreplace
from typing import Any


class RescueRecommendationEngine:
    """Index, evaluate, and rank animal rescue candidates."""

    def __init__(
        self,
        records: list[dict[str, Any]],
        rescue_profiles: dict[str, Any],
    ) -> None:
        """Initialize the recommendation engine.

        Args:
            records:
                Animal records retrieved from the database.

            rescue_profiles:
                Rescue categories and their preferred animal
                characteristics. Profiles may be dictionaries or
                RescueProfile dataclass objects.
        """

        # Normalize dictionary-based test profiles and RescueProfile
        # dataclass objects into one internal dictionary structure.
        self.rescue_profiles: dict[str, dict[str, Any]] = {
            rescue_type: self._normalize_profile(profile)
            for rescue_type, profile in rescue_profiles.items()
        }

        # Main dictionary:
        # unique internal record key -> complete animal record
        self.records: dict[str, dict[str, Any]] = {}

        # Dictionary indexes:
        # normalized field value -> set of matching record keys
        self.breed_index: dict[str, set[str]] = defaultdict(set)
        self.sex_index: dict[str, set[str]] = defaultdict(set)
        self.outcome_index: dict[str, set[str]] = defaultdict(set)

        # Sorted age structures used for binary search.
        self.sorted_age_records: list[tuple[float, str]] = []
        self.sorted_age_values: list[float] = []

        # Cache:
        # (rescue type, result limit) -> recommendation results
        self.cache: dict[
            tuple[str, int],
            list[dict[str, Any]],
        ] = {}

        self._build_indexes(records)

    # ------------------------------------------------------------------
    # Data normalization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(value: Any) -> str:
        """Normalize text for reliable comparisons.

        The method converts values to lowercase strings, removes leading
        and trailing spaces, and replaces repeated spaces with one space.

        Args:
            value:
                A value that may contain text.

        Returns:
            A normalized string.
        """

        return " ".join(
            str(value or "").strip().lower().split()
        )

    @staticmethod
    def _safe_number(value: Any) -> float | None:
        """Convert a value to a floating-point number safely.

        Args:
            value:
                A possible numeric value.

        Returns:
            The converted number, or None when conversion is not possible.
        """

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_profile(
        profile: Any,
    ) -> dict[str, Any]:
        """Convert a dictionary or RescueProfile object to one format.

        The recommendation tests use dictionary-based rescue profiles,
        while the dashboard's rescue_rules.py module uses frozen
        RescueProfile dataclass objects. This method supports both
        representations.

        Args:
            profile:
                A dictionary or RescueProfile-compatible object.

        Returns:
            A dictionary containing the normalized profile fields.

        Raises:
            ValueError:
                If the profile does not contain valid minimum and
                maximum age values.
        """

        if isinstance(profile, dict):
            breeds = profile.get(
                "breeds",
                profile.get(
                    "preferred_breeds",
                    (),
                ),
            )

            minimum_age = profile.get(
                "minimum_age_weeks",
                profile.get(
                    "min_age_weeks",
                ),
            )

            maximum_age = profile.get(
                "maximum_age_weeks",
                profile.get(
                    "max_age_weeks",
                ),
            )

            preferred_sex = profile.get(
                "preferred_sex"
            )

            preferred_outcome = profile.get(
                "preferred_outcome"
            )

        else:
            breeds = getattr(
                profile,
                "preferred_breeds",
                (),
            )

            minimum_age = getattr(
                profile,
                "min_age_weeks",
                None,
            )

            maximum_age = getattr(
                profile,
                "max_age_weeks",
                None,
            )

            preferred_sex = getattr(
                profile,
                "preferred_sex",
                None,
            )

            preferred_outcome = getattr(
                profile,
                "preferred_outcome",
                None,
            )

        if minimum_age is None or maximum_age is None:
            raise ValueError(
                "Rescue profile must define minimum "
                "and maximum ages."
            )

        return {
            "breeds": tuple(breeds),
            "minimum_age_weeks": float(
                minimum_age
            ),
            "maximum_age_weeks": float(
                maximum_age
            ),
            "preferred_sex": str(
                preferred_sex or ""
            ),
            "preferred_outcome": str(
                preferred_outcome or ""
            ),
        }

    # ------------------------------------------------------------------
    # Index construction
    # ------------------------------------------------------------------

    def _build_indexes(
        self,
        records: list[dict[str, Any]],
    ) -> None:
        """Build dictionary, set, and sorted-age indexes.

        Each animal is stored in the main records dictionary. Secondary
        dictionary indexes associate breeds, sex values, and outcome
        values with sets of matching record keys.

        Valid ages are stored in a sorted list so age-range boundaries
        can later be located with binary search.

        Args:
            records:
                Animal records to index.
        """

        known_breeds = {
            self._normalize(breed)
            for profile in self.rescue_profiles.values()
            for breed in profile.get(
                "breeds",
                (),
            )
        }

        for position, original_record in enumerate(records):
            # Work with a copy so the source database record is not changed.
            record = dict(original_record)

            animal_id = str(
                record.get(
                    "animal_id",
                    "unknown",
                )
            )

            mongo_id = record.get("_id")

            # MongoDB's _id is preferred when present. The animal ID and
            # list position provide a unique fallback for test records.
            if mongo_id is not None:
                record_key = str(mongo_id)
            else:
                record_key = (
                    f"{animal_id}:{position}"
                )

            record["record_key"] = record_key
            self.records[record_key] = record

            breed_text = self._normalize(
                record.get("breed")
            )

            sex = self._normalize(
                record.get(
                    "sex_upon_outcome"
                )
            )

            outcome = self._normalize(
                record.get("outcome_type")
            )

            age = self._safe_number(
                record.get(
                    "age_upon_outcome_in_weeks"
                )
            )

            # A breed field may contain values such as
            # "Labrador Retriever Mix." Substring matching allows the
            # profile breed to match the complete database description.
            for breed_term in known_breeds:
                if (
                    breed_term
                    and breed_term in breed_text
                ):
                    self.breed_index[
                        breed_term
                    ].add(record_key)

            if sex:
                self.sex_index[
                    sex
                ].add(record_key)

            if outcome:
                self.outcome_index[
                    outcome
                ].add(record_key)

            if age is not None:
                self.sorted_age_records.append(
                    (
                        age,
                        record_key,
                    )
                )

        # Sorting occurs once during engine initialization.
        self.sorted_age_records.sort(
            key=lambda item: item[0]
        )

        # A separate age-only list is used by the bisect functions.
        self.sorted_age_values = [
            age
            for age, _ in self.sorted_age_records
        ]

        # Index rebuilding invalidates previous cached recommendations.
        self.cache.clear()

    # ------------------------------------------------------------------
    # Binary-search and dictionary lookup methods
    # ------------------------------------------------------------------

    def _find_age_ids(
        self,
        minimum_age: float,
        maximum_age: float,
    ) -> set[str]:
        """Find animal record keys within an inclusive age range.

        Binary search identifies the left and right boundaries of the
        requested range in the sorted age list.

        Args:
            minimum_age:
                Inclusive minimum age in weeks.

            maximum_age:
                Inclusive maximum age in weeks.

        Returns:
            A set of matching record keys.
        """

        if minimum_age > maximum_age:
            return set()

        left_boundary = bisect_left(
            self.sorted_age_values,
            minimum_age,
        )

        right_boundary = bisect_right(
            self.sorted_age_values,
            maximum_age,
        )

        return {
            record_key
            for _, record_key
            in self.sorted_age_records[
                left_boundary:right_boundary
            ]
        }

    def _find_breed_ids(
        self,
        preferred_breeds: tuple[str, ...],
    ) -> set[str]:
        """Find animals matching any preferred breed.

        Set union combines the record keys for every acceptable breed.

        Args:
            preferred_breeds:
                Breed names accepted by a rescue profile.

        Returns:
            A set containing all matching record keys.
        """

        matching_ids: set[str] = set()

        for breed in preferred_breeds:
            breed_key = self._normalize(
                breed
            )

            matching_ids.update(
                self.breed_index.get(
                    breed_key,
                    set(),
                )
            )

        return matching_ids

    # ------------------------------------------------------------------
    # Set-based candidate selection
    # ------------------------------------------------------------------

    def _find_candidates(
        self,
        profile: dict[str, Any],
        requested_count: int,
    ) -> set[str]:
        """Create a candidate pool using indexed set operations.

        A strict intersection is attempted first. When the strict set
        does not contain enough candidates, a broader union is used and
        the scoring algorithm determines the strongest partial matches.

        Args:
            profile:
                Rescue requirements and preferred characteristics.

            requested_count:
                Number of recommendations requested.

        Returns:
            A set of candidate record keys.
        """

        breed_ids = self._find_breed_ids(
            tuple(
                profile.get(
                    "breeds",
                    (),
                )
            )
        )

        preferred_sex = self._normalize(
            profile.get(
                "preferred_sex"
            )
        )

        preferred_outcome = self._normalize(
            profile.get(
                "preferred_outcome"
            )
        )

        sex_ids = self.sex_index.get(
            preferred_sex,
            set(),
        )

        outcome_ids = self.outcome_index.get(
            preferred_outcome,
            set(),
        )

        age_ids = self._find_age_ids(
            profile[
                "minimum_age_weeks"
            ],
            profile[
                "maximum_age_weeks"
            ],
        )

        # Intersection retains only animals appearing in every set.
        strict_matches = (
            breed_ids
            & sex_ids
            & outcome_ids
            & age_ids
        )

        if len(strict_matches) >= requested_count:
            return strict_matches

        # Union creates a larger pool containing animals that match one
        # or more preferred breed, sex, or age requirements.
        broader_matches = (
            breed_ids
            | sex_ids
            | age_ids
        )

        # Continue requiring the preferred outcome when matching
        # outcome records are available.
        if outcome_ids:
            broader_matches &= outcome_ids

        if broader_matches:
            return broader_matches

        # Final fallback prevents an empty application result when no
        # indexed characteristics match the requested profile.
        return set(
            self.records.keys()
        )

    # ------------------------------------------------------------------
    # Weighted scoring algorithm
    # ------------------------------------------------------------------

    def _calculate_score(
        self,
        record: dict[str, Any],
        profile: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Calculate a weighted rescue suitability score.

        Scoring weights:

        - Preferred breed: 40 points
        - Preferred age range: 25 points
        - Preferred sex: 20 points
        - Preferred outcome: 15 points

        Args:
            record:
                One animal record.

            profile:
                Requirements for the selected rescue category.

        Returns:
            A tuple containing the score and a list of match reasons.
        """

        score = 0.0
        reasons: list[str] = []

        breed_text = self._normalize(
            record.get("breed")
        )

        sex = self._normalize(
            record.get(
                "sex_upon_outcome"
            )
        )

        outcome = self._normalize(
            record.get("outcome_type")
        )

        age = self._safe_number(
            record.get(
                "age_upon_outcome_in_weeks"
            )
        )

        preferred_breeds = [
            self._normalize(breed)
            for breed in profile.get(
                "breeds",
                (),
            )
        ]

        # Breed match: 40 points
        if any(
            breed
            and breed in breed_text
            for breed in preferred_breeds
        ):
            score += 40

            reasons.append(
                "Preferred rescue breed"
            )

        # Sex match: 20 points
        if sex == self._normalize(
            profile.get(
                "preferred_sex"
            )
        ):
            score += 20

            reasons.append(
                "Preferred sex"
            )

        # Outcome match: 15 points
        if outcome == self._normalize(
            profile.get(
                "preferred_outcome"
            )
        ):
            score += 15

            reasons.append(
                "Preferred outcome type"
            )

        # Age match: up to 25 points
        if age is not None:
            minimum_age = profile[
                "minimum_age_weeks"
            ]

            maximum_age = profile[
                "maximum_age_weeks"
            ]

            if minimum_age <= age <= maximum_age:
                score += 25

                reasons.append(
                    "Age within preferred range"
                )

            else:
                # Partial credit is awarded when the age is reasonably
                # close to the preferred range.
                distance_from_range = min(
                    abs(
                        age
                        - minimum_age
                    ),
                    abs(
                        age
                        - maximum_age
                    ),
                )

                partial_age_score = max(
                    0.0,
                    25.0
                    - (
                        distance_from_range
                        * 0.25
                    ),
                )

                score += partial_age_score

                if partial_age_score > 0:
                    reasons.append(
                        "Age near preferred range"
                    )

        return (
            round(score, 2),
            reasons,
        )

    # ------------------------------------------------------------------
    # Bounded min-heap ranking
    # ------------------------------------------------------------------

    def _select_top_candidates(
        self,
        candidate_ids: set[str],
        profile: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Retain the highest-scoring candidates with a min-heap.

        The heap never contains more than the requested number of
        recommendations. Its root represents the lowest score currently
        retained. A stronger candidate replaces that root.

        Args:
            candidate_ids:
                Candidate record keys.

            profile:
                Requirements for the selected rescue category.

            limit:
                Maximum number of results to return.

        Returns:
            Ranked recommendation records.
        """

        heap: list[
            tuple[float, str]
        ] = []

        score_details: dict[
            str,
            tuple[
                float,
                list[str],
            ],
        ] = {}

        for record_key in candidate_ids:
            record = self.records[
                record_key
            ]

            score, reasons = self._calculate_score(
                record=record,
                profile=profile,
            )

            score_details[
                record_key
            ] = (
                score,
                reasons,
            )

            # Including record_key creates a deterministic tie breaker.
            heap_entry = (
                score,
                record_key,
            )

            if len(heap) < limit:
                heappush(
                    heap,
                    heap_entry,
                )

            elif heap_entry > heap[0]:
                heapreplace(
                    heap,
                    heap_entry,
                )

        # The heap is not maintained in descending display order, so
        # only the small retained top-k set is sorted for presentation.
        ranked_entries = sorted(
            heap,
            key=lambda item: (
                -item[0],
                item[1],
            ),
        )

        recommendations: list[
            dict[str, Any]
        ] = []

        for rank, (
            score,
            record_key,
        ) in enumerate(
            ranked_entries,
            start=1,
        ):
            record = dict(
                self.records[
                    record_key
                ]
            )

            _, reasons = score_details[
                record_key
            ]

            record[
                "recommendation_rank"
            ] = rank

            record[
                "match_score"
            ] = score

            record[
                "match_reasons"
            ] = ", ".join(reasons)

            recommendations.append(
                record
            )

        return recommendations

    # ------------------------------------------------------------------
    # Public recommendation method
    # ------------------------------------------------------------------

    def recommend(
        self,
        rescue_type: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return ranked recommendations for a rescue category.

        Args:
            rescue_type:
                Name of a rescue profile.

            limit:
                Maximum number of recommendations to return.

        Returns:
            Ranked recommendation records.

        Raises:
            ValueError:
                If the rescue profile is unknown or the limit is not
                a positive integer.
        """

        if rescue_type not in self.rescue_profiles:
            raise ValueError(
                f"Unknown rescue profile: "
                f"{rescue_type}"
            )

        if (
            not isinstance(limit, int)
            or limit <= 0
        ):
            raise ValueError(
                "Recommendation limit must "
                "be positive."
            )

        cache_key = (
            rescue_type,
            limit,
        )

        if cache_key in self.cache:
            # Return copies so callers cannot modify the stored cache.
            return [
                dict(record)
                for record in self.cache[
                    cache_key
                ]
            ]

        profile = self.rescue_profiles[
            rescue_type
        ]

        candidate_ids = self._find_candidates(
            profile=profile,
            requested_count=limit,
        )

        recommendations = (
            self._select_top_candidates(
                candidate_ids=candidate_ids,
                profile=profile,
                limit=limit,
            )
        )

        # Store copies so external changes do not alter cached records.
        self.cache[cache_key] = [
            dict(record)
            for record in recommendations
        ]

        return [
            dict(record)
            for record in recommendations
        ]