"""
callbacks.py
------------
Dash callback logic for the CS 499 enhanced Grazioso Salvare
Rescue Match Recommendation Dashboard.

This module connects user-interface actions to the application service
layer.

Responsibilities include:
- Responding to rescue-type, breed, age, and outcome selections.
- Calling DashboardService to filter, score, and rank candidates.
- Updating the candidate DataTable.
- Updating result summaries.
- Explaining the selected rescue profile.
- Displaying the strongest recommendation.
- Updating the chart based on the selected application mode.
- Storing complete filtered records for map use.
- Updating the interactive map when an animal is selected.
- Handling empty results and application errors safely.

Database access and recommendation logic are intentionally kept outside
this module. This separation improves maintainability, readability,
testability, and separation of concerns.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

from __future__ import annotations

import json
from typing import Any

import dash_leaflet as dl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import (
    Input,
    Output,
    html,
)

from dashboard_service import DashboardService

from rescue_rules import (
    RESET_RESCUE_TYPE,
    SCORE_WEIGHTS,
)


# ----------------------------------------------------------------------
# DISPLAY CONSTANTS
# ----------------------------------------------------------------------

DEFAULT_MAP_CENTER = [
    30.2672,
    -97.7431,
]

DEFAULT_MAP_ZOOM = 9


# ----------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------


def empty_figure(
    title: str,
    message: str,
) -> go.Figure:
    """
    Create a clean Plotly figure containing an informational message.

    Args:
        title:
            Figure title.

        message:
            Message displayed in the center of the graph.

    Returns:
        Plotly Figure.
    """

    figure = go.Figure()

    figure.update_layout(
        title=title,

        xaxis={
            "visible": False,
        },

        yaxis={
            "visible": False,
        },

        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {
                    "size": 16,
                },
            }
        ],

        margin={
            "l": 40,
            "r": 40,
            "t": 70,
            "b": 40,
        },

        height=480,
    )

    return figure


def records_for_store(
    frame: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Convert a DataFrame into JSON-safe records for dcc.Store.

    Using Pandas JSON conversion handles NaN and many NumPy/Pandas values
    more reliably than storing raw DataFrame dictionaries.

    Args:
        frame:
            DataFrame containing the current filtered results.

    Returns:
        JSON-compatible list of dictionaries.
    """

    if frame is None or frame.empty:
        return []

    json_text = frame.to_json(
        orient="records",
        date_format="iso",
    )

    return json.loads(
        json_text
    )


def prepare_table_records(
    service: DashboardService,
    frame: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Create DataTable records and add a stable Dash row identifier.

    The hidden "id" value allows the selected animal to remain identifiable
    even when the user sorts or filters the DataTable.

    Args:
        service:
            Dashboard service.

        frame:
            Current filtered/ranked DataFrame.

    Returns:
        Dash DataTable-compatible records.
    """

    records = service.table_data(
        frame
    )

    for index, record in enumerate(
        records
    ):

        animal_id = str(
            record.get(
                "animal_id",
                ""
            )
            or ""
        ).strip()

        # Prefer animal_id as the stable Dash row ID.
        # A fallback is provided in case an incomplete record has no ID.
        record["id"] = (
            animal_id
            if animal_id
            else f"row-{index}"
        )

    return records


# ----------------------------------------------------------------------
# PROFILE DISPLAY
# ----------------------------------------------------------------------


def build_profile_summary(
    profile_info: dict[str, Any],
) -> list[Any]:
    """
    Build a user-friendly explanation of the selected rescue profile.

    Args:
        profile_info:
            Profile information returned by DashboardService.

    Returns:
        Dash components explaining the profile and score weights.
    """

    label = profile_info.get(
        "label",
        "All Animals",
    )

    description = profile_info.get(
        "description",
        "",
    )

    preferred_breeds = profile_info.get(
        "preferred_breeds",
        [],
    )

    age_range = profile_info.get(
        "age_range"
    )

    preferred_sex = profile_info.get(
        "preferred_sex"
    )

    preferred_outcome = profile_info.get(
        "preferred_outcome"
    )

    children: list[Any] = [
        html.H3(
            label,
            style={
                "marginTop": "0",
                "marginBottom": "8px",
            },
        ),

        html.P(
            description,
            style={
                "lineHeight": "1.5",
            },
        ),
    ]

    # Reset mode does not have a rescue recommendation profile.
    if not preferred_breeds:

        children.append(
            build_scoring_weights()
        )

        return children

    breed_text = ", ".join(
        preferred_breeds
    )

    if age_range:

        age_text = (
            f"{age_range[0]:g}"
            f"–"
            f"{age_range[1]:g} weeks"
        )

    else:

        age_text = (
            "No preferred age range"
        )

    children.extend(
        [
            html.Ul(
                [
                    html.Li(
                        [
                            html.Strong(
                                "Preferred breeds: "
                            ),
                            breed_text,
                        ]
                    ),

                    html.Li(
                        [
                            html.Strong(
                                "Preferred age range: "
                            ),
                            age_text,
                        ]
                    ),

                    html.Li(
                        [
                            html.Strong(
                                "Preferred sex: "
                            ),
                            (
                                preferred_sex
                                or "No preference"
                            ),
                        ]
                    ),

                    html.Li(
                        [
                            html.Strong(
                                "Preferred outcome: "
                            ),
                            (
                                preferred_outcome
                                or "No preference"
                            ),
                        ]
                    ),
                ],
                style={
                    "lineHeight": "1.7",
                },
            ),

            build_scoring_weights(),
        ]
    )

    return children


def build_scoring_weights() -> html.Div:
    """
    Build a compact explanation of the 100-point scoring model.

    Returns:
        Dash component.
    """

    return html.Div(
        [
            html.H4(
                "Scoring Model",
                style={
                    "marginBottom": "10px",
                },
            ),

            html.P(
                [
                    html.Strong(
                        f"{SCORE_WEIGHTS['breed']} points"
                    ),
                    " — preferred breed | ",

                    html.Strong(
                        f"{SCORE_WEIGHTS['age']} points"
                    ),
                    " — preferred age | ",

                    html.Strong(
                        f"{SCORE_WEIGHTS['sex']} points"
                    ),
                    " — preferred sex | ",

                    html.Strong(
                        f"{SCORE_WEIGHTS['outcome']} points"
                    ),
                    " — preferred outcome",
                ],
                style={
                    "lineHeight": "1.7",
                    "marginBottom": "0",
                },
            ),
        ]
    )


# ----------------------------------------------------------------------
# TOP RECOMMENDATION CARD
# ----------------------------------------------------------------------


def build_recommendation_card(
    candidate: dict[str, Any] | None,
    rescue_type: str | None,
) -> list[Any]:
    """
    Build the strongest-candidate recommendation card.

    Args:
        candidate:
            Top candidate returned by DashboardService.

        rescue_type:
            Current rescue-category selection.

    Returns:
        Dash components for recommendation-card.
    """

    if (
        rescue_type in {
            None,
            "",
            RESET_RESCUE_TYPE,
        }
    ):

        return [
            html.P(
                (
                    "Select a rescue type to calculate recommendation "
                    "scores and identify the strongest candidate."
                ),
                style={
                    "margin": "0",
                    "lineHeight": "1.5",
                },
            )
        ]

    if candidate is None:

        return [
            html.P(
                (
                    "No recommendation is available for the current "
                    "selection."
                ),
                style={
                    "margin": "0",
                },
            )
        ]

    name = (
        str(
            candidate.get(
                "name",
                ""
            )
        ).strip()
        or "Unnamed Animal"
    )

    animal_id = (
        str(
            candidate.get(
                "animal_id",
                ""
            )
        ).strip()
        or "Unknown ID"
    )

    breed = (
        str(
            candidate.get(
                "breed",
                ""
            )
        ).strip()
        or "Unknown Breed"
    )

    score = candidate.get(
        "match_score",
        0,
    )

    level = candidate.get(
        "match_level",
        "",
    )

    reasons = candidate.get(
        "match_reasons",
        "",
    )

    sex = candidate.get(
        "sex_upon_outcome",
        "",
    )

    outcome = candidate.get(
        "outcome_type",
        "",
    )

    age = candidate.get(
        "age_upon_outcome_in_weeks"
    )

    try:

        age_display = (
            f"{float(age):g} weeks"
        )

    except (
        TypeError,
        ValueError,
    ):

        age_display = "Unknown"

    return [
        html.Div(
            [
                html.Div(
                    [
                        html.H3(
                            name,
                            style={
                                "marginTop": "0",
                                "marginBottom": "4px",
                            },
                        ),

                        html.P(
                            f"Animal ID: {animal_id}",
                            style={
                                "marginTop": "0",
                                "marginBottom": "5px",
                            },
                        ),

                        html.P(
                            breed,
                            style={
                                "fontWeight": "bold",
                                "marginBottom": "12px",
                            },
                        ),
                    ]
                ),

                html.Div(
                    [
                        html.Div(
                            f"{score} / 100",
                            style={
                                "fontSize": "30px",
                                "fontWeight": "bold",
                            },
                        ),

                        html.Div(
                            level,
                            style={
                                "fontSize": "18px",
                                "fontWeight": "bold",
                            },
                        ),
                    ],
                    style={
                        "textAlign": "right",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "gap": "20px",
                "flexWrap": "wrap",
            },
        ),

        html.Hr(),

        html.Div(
            [
                html.P(
                    [
                        html.Strong(
                            "Sex: "
                        ),
                        str(
                            sex
                            or "Unknown"
                        ),
                    ]
                ),

                html.P(
                    [
                        html.Strong(
                            "Age: "
                        ),
                        age_display,
                    ]
                ),

                html.P(
                    [
                        html.Strong(
                            "Outcome: "
                        ),
                        str(
                            outcome
                            or "Unknown"
                        ),
                    ]
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": (
                    "repeat(auto-fit, minmax(160px, 1fr))"
                ),
                "gap": "8px",
            },
        ),

        html.H4(
            "Why This Animal Was Recommended",
            style={
                "marginBottom": "8px",
            },
        ),

        html.P(
            str(
                reasons
                or "No recommendation details are available."
            ),
            style={
                "lineHeight": "1.6",
                "marginBottom": "0",
            },
        ),
    ]


# ----------------------------------------------------------------------
# RESULT SUMMARY DISPLAY
# ----------------------------------------------------------------------


def build_result_summary(
    summary: dict[str, Any],
    rescue_type: str | None,
) -> list[Any]:
    """
    Build the dashboard result-summary display.

    Args:
        summary:
            Summary returned by DashboardService.

        rescue_type:
            Selected rescue profile.

    Returns:
        Dash components.
    """

    message = summary.get(
        "message",
        ""
    )

    if (
        rescue_type in {
            None,
            "",
            RESET_RESCUE_TYPE,
        }
    ):

        return [
            html.P(
                message,
                style={
                    "margin": "0",
                },
            )
        ]

    return [
        html.P(
            message,
            style={
                "marginTop": "0",
            },
        ),

        html.Div(
            [
                html.Span(
                    (
                        f"Strong: "
                        f"{summary.get('strong_matches', 0):,}"
                    )
                ),

                html.Span(
                    (
                        f"Good: "
                        f"{summary.get('good_matches', 0):,}"
                    )
                ),

                html.Span(
                    (
                        f"Partial: "
                        f"{summary.get('partial_matches', 0):,}"
                    )
                ),

                html.Span(
                    (
                        f"Low: "
                        f"{summary.get('low_matches', 0):,}"
                    )
                ),
            ],
            style={
                "display": "flex",
                "gap": "16px",
                "flexWrap": "wrap",
                "fontWeight": "bold",
            },
        ),
    ]


# ----------------------------------------------------------------------
# ACTIVE FILTER LABEL
# ----------------------------------------------------------------------


def build_filter_label(
    rescue_type: str | None,
    breed: str | None,
    age_range: list[float] | None,
    outcome_type: str | None,
) -> str:
    """
    Create a readable description of the active dashboard filters.

    Returns:
        Filter summary text.
    """

    parts = []

    if (
        rescue_type
        and rescue_type
        != RESET_RESCUE_TYPE
    ):

        parts.append(
            f"Rescue profile: {rescue_type}"
        )

    else:

        parts.append(
            "Showing all dog records"
        )

    if breed:

        parts.append(
            f"Breed: {breed}"
        )

    if (
        age_range
        and len(age_range) == 2
    ):

        parts.append(
            (
                f"Age: "
                f"{age_range[0]:g}"
                f"–"
                f"{age_range[1]:g} weeks"
            )
        )

    if outcome_type:

        parts.append(
            f"Outcome: {outcome_type}"
        )

    return " | ".join(
        parts
    )


# ----------------------------------------------------------------------
# CHART BUILDERS
# ----------------------------------------------------------------------


def build_breed_distribution_chart(
    frame: pd.DataFrame,
) -> go.Figure:
    """
    Create a breed-distribution chart for Reset / Show All mode.

    To keep the chart readable, only the ten most frequently represented
    breed descriptions are displayed.

    Args:
        frame:
            Current result DataFrame.

    Returns:
        Plotly figure.
    """

    if (
        frame is None
        or frame.empty
        or "breed" not in frame.columns
    ):

        return empty_figure(
            "Breed Distribution",
            "No animal records are available.",
        )

    breed_counts = (
        frame["breed"]
        .replace(
            "",
            "Unknown Breed"
        )
        .fillna(
            "Unknown Breed"
        )
        .value_counts()
        .head(10)
        .reset_index()
    )

    breed_counts.columns = [
        "breed",
        "count",
    ]

    figure = px.pie(
        breed_counts,
        names="breed",
        values="count",
        title="Top 10 Breed Distribution",
        hole=0.35,
    )

    figure.update_layout(
        legend_title_text="Breed",
        margin={
            "l": 30,
            "r": 30,
            "t": 70,
            "b": 30,
        },
        height=480,
    )

    return figure


def build_recommendation_chart(
    service: DashboardService,
    frame: pd.DataFrame,
    rescue_type: str,
) -> go.Figure:
    """
    Create a horizontal bar chart of the strongest rescue candidates.

    Args:
        service:
            Dashboard service.

        frame:
            Ranked recommendation DataFrame.

        rescue_type:
            Selected rescue profile.

    Returns:
        Plotly figure.
    """

    top_frame = service.top_candidates(
        frame,
        limit=10,
    )

    if top_frame.empty:

        return empty_figure(
            f"Top {rescue_type} Candidates",
            "No ranked candidates match the current filters.",
        )

    top_frame = top_frame.copy()

    top_frame["display_name"] = (
        top_frame["name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    unnamed_mask = (
        top_frame["display_name"]
        == ""
    )

    top_frame.loc[
        unnamed_mask,
        "display_name",
    ] = top_frame.loc[
        unnamed_mask,
        "animal_id",
    ].fillna(
        "Unnamed Animal"
    )

    # Reverse for a horizontal bar chart so the strongest candidate appears
    # at the top of the visualization.
    chart_frame = (
        top_frame
        .iloc[::-1]
        .copy()
    )

    figure = px.bar(
        chart_frame,
        x="match_score",
        y="display_name",
        orientation="h",
        text="match_score",
        hover_data={
            "breed": True,
            "match_level": True,
            "animal_id": True,
            "match_score": False,
        },
        title=(
            f"Top {len(top_frame)} "
            f"{rescue_type} Candidates"
        ),
        labels={
            "match_score": "Match Score",
            "display_name": "Animal",
        },
    )

    figure.update_traces(
        texttemplate="%{text}/100",
        textposition="outside",
        cliponaxis=False,
    )

    figure.update_xaxes(
        range=[
            0,
            105,
        ],
        title="Match Score (0–100)",
    )

    figure.update_yaxes(
        title="",
    )

    figure.update_layout(
        margin={
            "l": 40,
            "r": 60,
            "t": 70,
            "b": 50,
        },
        height=480,
    )

    return figure


# ----------------------------------------------------------------------
# MAP BUILDERS
# ----------------------------------------------------------------------


def empty_map_message(
    message: str,
) -> html.Div:
    """
    Build an informational placeholder for the map area.

    Args:
        message:
            User-facing message.

    Returns:
        Dash component.
    """

    return html.Div(
        [
            html.P(
                message,
                style={
                    "margin": "0",
                },
            )
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "minHeight": "480px",
            "border": "1px solid #dfe3e6",
            "borderRadius": "8px",
            "padding": "20px",
            "textAlign": "center",
        },
    )


def build_animal_map(
    map_info: dict[str, Any],
) -> dl.Map:
    """
    Build an interactive Leaflet map for a selected animal.

    Args:
        map_info:
            Validated map information from DashboardService.

    Returns:
        Dash Leaflet map.
    """

    latitude = map_info[
        "latitude"
    ]

    longitude = map_info[
        "longitude"
    ]

    name = map_info.get(
        "name",
        "Unnamed Animal",
    )

    animal_id = map_info.get(
        "animal_id",
        "Unknown ID",
    )

    breed = map_info.get(
        "breed",
        "Unknown Breed",
    )

    return dl.Map(
        [
            dl.TileLayer(),

            dl.Marker(
                position=[
                    latitude,
                    longitude,
                ],

                children=[
                    dl.Tooltip(
                        name
                    ),

                    dl.Popup(
                        [
                            html.H4(
                                name,
                                style={
                                    "marginBottom": "5px",
                                },
                            ),

                            html.P(
                                [
                                    html.Strong(
                                        "Animal ID: "
                                    ),
                                    animal_id,
                                ]
                            ),

                            html.P(
                                [
                                    html.Strong(
                                        "Breed: "
                                    ),
                                    breed,
                                ]
                            ),
                        ]
                    ),
                ],
            ),
        ],

        center=[
            latitude,
            longitude,
        ],

        zoom=12,

        style={
            "width": "100%",
            "height": "480px",
            "borderRadius": "8px",
        },
    )


# ----------------------------------------------------------------------
# CALLBACK REGISTRATION
# ----------------------------------------------------------------------


def register_callbacks(
    app: Any,
    service: DashboardService,
) -> None:
    """
    Register all Dash callbacks for the enhanced application.

    Args:
        app:
            Dash application instance.

        service:
            Configured DashboardService instance.
    """

    # ------------------------------------------------------------------
    # MAIN DASHBOARD UPDATE CALLBACK
    # ------------------------------------------------------------------

    @app.callback(
        Output(
            "filtered-data-store",
            "data",
        ),

        Output(
            "datatable-id",
            "data",
        ),

        Output(
            "datatable-id",
            "columns",
        ),

        Output(
            "datatable-id",
            "selected_rows",
        ),

        Output(
            "datatable-id",
            "selected_row_ids",
        ),

        Output(
            "filter-label",
            "children",
        ),

        Output(
            "result-summary",
            "children",
        ),

        Output(
            "profile-summary",
            "children",
        ),

        Output(
            "recommendation-card",
            "children",
        ),

        Output(
            "graph-id",
            "figure",
        ),

        Input(
            "filter-type",
            "value",
        ),

        Input(
            "breed-filter",
            "value",
        ),

        Input(
            "age-filter",
            "value",
        ),

        Input(
            "outcome-filter",
            "value",
        ),
    )
    def update_dashboard(
        rescue_type: str | None,
        breed: str | None,
        age_range: list[float] | None,
        outcome_type: str | None,
    ):
        """
        Update the dashboard when any primary filter changes.
        """

        try:

            # ----------------------------------------------------------
            # FILTER AND RANK
            # ----------------------------------------------------------

            frame = service.filter_and_rank(
                rescue_type=rescue_type,
                breed=breed,
                age_range=age_range,
                outcome_type=outcome_type,
            )

            # ----------------------------------------------------------
            # STORE FULL RECORDS
            # ----------------------------------------------------------

            stored_records = (
                records_for_store(
                    frame
                )
            )

            # ----------------------------------------------------------
            # DATA TABLE
            # ----------------------------------------------------------

            table_records = (
                prepare_table_records(
                    service,
                    frame,
                )
            )

            include_recommendation = (
                rescue_type
                not in {
                    None,
                    "",
                    RESET_RESCUE_TYPE,
                }
            )

            table_columns = (
                service.table_columns(
                    include_recommendation_fields=(
                        include_recommendation
                    )
                )
            )

            # ----------------------------------------------------------
            # ACTIVE FILTER LABEL
            # ----------------------------------------------------------

            filter_label = (
                build_filter_label(
                    rescue_type=rescue_type,
                    breed=breed,
                    age_range=age_range,
                    outcome_type=outcome_type,
                )
            )

            # ----------------------------------------------------------
            # RESULT SUMMARY
            # ----------------------------------------------------------

            summary = (
                service.result_summary(
                    frame,
                    rescue_type,
                )
            )

            result_children = (
                build_result_summary(
                    summary,
                    rescue_type,
                )
            )

            # ----------------------------------------------------------
            # RESCUE PROFILE EXPLANATION
            # ----------------------------------------------------------

            profile_info = (
                service.profile_information(
                    rescue_type
                )
            )

            profile_children = (
                build_profile_summary(
                    profile_info
                )
            )

            # ----------------------------------------------------------
            # TOP RECOMMENDATION
            # ----------------------------------------------------------

            top_candidate = (
                service.top_candidate(
                    frame
                )
            )

            recommendation_children = (
                build_recommendation_card(
                    candidate=top_candidate,
                    rescue_type=rescue_type,
                )
            )

            # ----------------------------------------------------------
            # VISUALIZATION
            # ----------------------------------------------------------

            if (
                rescue_type
                in {
                    None,
                    "",
                    RESET_RESCUE_TYPE,
                }
            ):

                figure = (
                    build_breed_distribution_chart(
                        frame
                    )
                )

            else:

                figure = (
                    build_recommendation_chart(
                        service=service,
                        frame=frame,
                        rescue_type=rescue_type,
                    )
                )

            # Clear any previous row selection whenever filters change.
            return (
                stored_records,
                table_records,
                table_columns,
                [],
                [],
                filter_label,
                result_children,
                profile_children,
                recommendation_children,
                figure,
            )

        except ValueError as error:

            # Validation failures are safe to display because these
            # messages do not expose database credentials or internals.

            error_message = (
                f"Unable to apply the selected filters: {error}"
            )

            return (
                [],
                [],
                service.table_columns(
                    include_recommendation_fields=True
                ),
                [],
                [],
                "Invalid filter selection",
                [
                    html.P(
                        error_message
                    )
                ],
                [
                    html.P(
                        (
                            "Please correct the filter selection "
                            "and try again."
                        )
                    )
                ],
                [
                    html.P(
                        (
                            "A recommendation cannot be generated "
                            "until the filter values are valid."
                        )
                    )
                ],
                empty_figure(
                    "Candidate Visualization",
                    error_message,
                ),
            )

        except Exception:

            # Do not expose exception details, database configuration,
            # credentials, file paths, or stack traces to end users.

            safe_message = (
                "The dashboard could not complete the request. "
                "Please verify that the database is available and "
                "try again."
            )

            return (
                [],
                [],
                service.table_columns(
                    include_recommendation_fields=True
                ),
                [],
                [],
                "Unable to load results",
                [
                    html.P(
                        safe_message
                    )
                ],
                [
                    html.P(
                        (
                            "Rescue profile information is temporarily "
                            "unavailable."
                        )
                    )
                ],
                [
                    html.P(
                        (
                            "No recommendation is currently available."
                        )
                    )
                ],
                empty_figure(
                    "Candidate Visualization",
                    safe_message,
                ),
            )

    # ------------------------------------------------------------------
    # MAP CALLBACK
    # ------------------------------------------------------------------

    @app.callback(
        Output(
            "map-id",
            "children",
        ),

        Input(
            "filtered-data-store",
            "data",
        ),

        Input(
            "datatable-id",
            "selected_row_ids",
        ),
    )
    def update_map(
        stored_records: list[dict[str, Any]] | None,
        selected_row_ids: list[str] | None,
    ):
        """
        Update the map when an animal is selected.

        Using a stable animal ID rather than fixed DataFrame row/column
        positions prevents map behavior from breaking when the table is
        sorted, filtered, or reorganized.
        """

        if not stored_records:

            return empty_map_message(
                (
                    "No animal records are available for the "
                    "current selection."
                )
            )

        if not selected_row_ids:

            return empty_map_message(
                (
                    "Select an animal from the table to display "
                    "available location information."
                )
            )

        selected_id = str(
            selected_row_ids[0]
        )

        selected_animal = None

        # Locate the selected animal by its stable animal identifier.
        for record in stored_records:

            record_id = str(
                record.get(
                    "animal_id",
                    ""
                )
            )

            if (
                record_id
                == selected_id
            ):

                selected_animal = record

                break

        if selected_animal is None:

            return empty_map_message(
                (
                    "The selected animal could not be found in the "
                    "current result set."
                )
            )

        map_info = (
            service.map_information(
                selected_animal
            )
        )

        if map_info is None:

            return empty_map_message(
                (
                    "The selected animal does not have valid "
                    "location coordinates."
                )
            )

        return build_animal_map(
            map_info
        )