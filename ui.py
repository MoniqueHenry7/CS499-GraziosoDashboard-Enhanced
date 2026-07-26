"""
ui.py
-----
User-interface layout for the CS 499 enhanced Grazioso Salvare
Rescue Match Recommendation Dashboard.

This module is responsible only for presentation.

It creates:
- Grazioso Salvare branding and application heading.
- Rescue-type selection controls.
- Breed, age, and outcome filters.
- Active-filter and result summaries.
- Rescue-profile scoring explanation.
- Top-recommendation card.
- Ranked candidate data table.
- Recommendation/breed visualization area.
- Interactive map area.

Business logic is intentionally handled by dashboard_service.py and
rescue_rules.py. User interaction is handled by callbacks.py.

Separating the interface from database access and business logic improves
modularity, maintainability, readability, testing, and future expansion.

Author: Monique Henry
Course: CS 499 Computer Science Capstone
Enhancement: Software Design and Engineering
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Iterable

from dash import dash_table, dcc, html

from rescue_rules import (
    RESET_RESCUE_TYPE,
    RESCUE_PROFILES,
    SCORE_WEIGHTS,
)


# ----------------------------------------------------------------------
# APPLICATION DISPLAY CONSTANTS
# ----------------------------------------------------------------------

APPLICATION_TITLE = (
    "Grazioso Salvare Rescue Match Recommendation Dashboard"
)

APPLICATION_SUBTITLE = (
    "Interactive decision-support system for identifying and comparing "
    "potential rescue-training candidates."
)


# ----------------------------------------------------------------------
# VISUAL STYLE CONSTANTS
# ----------------------------------------------------------------------

# Styles are centralized so the layout does not repeat large inline
# style definitions throughout every component.

PAGE_STYLE = {
    "fontFamily": (
        "Arial, Helvetica, sans-serif"
    ),
    "maxWidth": "1500px",
    "margin": "0 auto",
    "padding": "20px",
    "backgroundColor": "#f5f7f9",
    "minHeight": "100vh",
}


HEADER_STYLE = {
    "backgroundColor": "#ffffff",
    "padding": "24px",
    "borderRadius": "10px",
    "marginBottom": "20px",
    "boxShadow": (
        "0 2px 8px rgba(0, 0, 0, 0.08)"
    ),
}


CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "padding": "20px",
    "borderRadius": "10px",
    "marginBottom": "20px",
    "boxShadow": (
        "0 2px 8px rgba(0, 0, 0, 0.06)"
    ),
}


SECTION_TITLE_STYLE = {
    "marginTop": "0",
    "marginBottom": "14px",
}


LABEL_STYLE = {
    "display": "block",
    "fontWeight": "bold",
    "marginBottom": "6px",
}


GRID_TWO_COLUMNS_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat(auto-fit, minmax(300px, 1fr))"
    ),
    "gap": "20px",
}


GRID_FOUR_COLUMNS_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat(auto-fit, minmax(220px, 1fr))"
    ),
    "gap": "16px",
}


SUMMARY_CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "padding": "16px",
    "borderRadius": "8px",
    "border": "1px solid #dfe3e6",
}


RECOMMENDATION_CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "padding": "20px",
    "borderRadius": "10px",
    "border": "1px solid #dfe3e6",
    "minHeight": "175px",
}


# ----------------------------------------------------------------------
# IMAGE HELPER
# ----------------------------------------------------------------------


def encode_image(
    image_path: str | Path | None,
) -> str | None:
    """
    Convert a local image file into a base64 data URI for Dash.

    Encoding the image allows the dashboard to display the supplied
    Grazioso Salvare logo without relying on an external image server.

    Args:
        image_path:
            Path to the image file.

    Returns:
        Base64 data URI when the file exists.

        None when the image path is missing, invalid, or cannot be read.
    """

    if not image_path:
        return None

    path = Path(image_path)

    if not path.exists() or not path.is_file():
        return None

    try:
        encoded_image = base64.b64encode(
            path.read_bytes()
        ).decode("ascii")

    except OSError:
        return None

    extension = (
        path.suffix
        .lower()
        .lstrip(".")
    )

    mime_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }

    mime_type = mime_types.get(
        extension,
        "image/png",
    )

    return (
        f"data:{mime_type};"
        f"base64,{encoded_image}"
    )


# ----------------------------------------------------------------------
# DROPDOWN OPTION HELPERS
# ----------------------------------------------------------------------


def create_text_options(
    values: Iterable[str],
) -> list[dict[str, str]]:
    """
    Convert strings into Dash dropdown options.

    Args:
        values:
            Iterable of text values.

    Returns:
        Dash-compatible dropdown option dictionaries.
    """

    return [
        {
            "label": value,
            "value": value,
        }
        for value in values
        if value
    ]


def rescue_type_options() -> list[dict[str, str]]:
    """
    Create rescue-category dropdown options.

    Returns:
        Reset/Show All plus each configured rescue profile.
    """

    options = [
        {
            "label": "Reset / Show All Dogs",
            "value": RESET_RESCUE_TYPE,
        }
    ]

    options.extend(
        {
            "label": profile.label,
            "value": rescue_key,
        }
        for rescue_key, profile
        in RESCUE_PROFILES.items()
    )

    return options


# ----------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------


def build_header(
    logo_path: str | Path | None,
) -> html.Div:
    """
    Build the application header.

    Args:
        logo_path:
            Optional local path to the Grazioso Salvare logo.

    Returns:
        Dash HTML header component.
    """

    encoded_logo = encode_image(
        logo_path
    )

    header_children = []

    if encoded_logo:

        header_children.append(
            html.Img(
                src=encoded_logo,
                alt="Grazioso Salvare logo",
                style={
                    "maxWidth": "230px",
                    "width": "100%",
                    "height": "auto",
                    "marginBottom": "15px",
                },
            )
        )

    header_children.extend(
        [
            html.H1(
                APPLICATION_TITLE,
                style={
                    "marginTop": "0",
                    "marginBottom": "8px",
                },
            ),

            html.P(
                APPLICATION_SUBTITLE,
                style={
                    "margin": "0",
                    "fontSize": "17px",
                    "lineHeight": "1.5",
                },
            ),
        ]
    )

    return html.Div(
        header_children,
        style=HEADER_STYLE,
    )


# ----------------------------------------------------------------------
# FILTER PANEL
# ----------------------------------------------------------------------


def build_filter_panel(
    available_breeds: list[str],
    available_outcomes: list[str],
    minimum_age: float,
    maximum_age: float,
) -> html.Div:
    """
    Build the interactive dashboard filtering controls.

    Args:
        available_breeds:
            Available breed values from the database.

        available_outcomes:
            Available shelter outcome values.

        minimum_age:
            Minimum age represented in the dataset.

        maximum_age:
            Maximum age represented in the dataset.

    Returns:
        Dash component containing the filtering controls.
    """

    # Dash RangeSlider values should be manageable numeric values.
    minimum_age = max(
        0,
        int(minimum_age),
    )

    maximum_age = max(
        minimum_age + 1,
        int(maximum_age),
    )

    # Avoid overwhelming the slider with hundreds of labels.
    slider_step = max(
        1,
        int(
            (
                maximum_age
                - minimum_age
            )
            / 5
        ),
    )

    marks = {}

    current_mark = minimum_age

    while current_mark < maximum_age:

        marks[current_mark] = (
            str(current_mark)
        )

        current_mark += slider_step

    marks[maximum_age] = (
        str(maximum_age)
    )

    return html.Div(
        [
            html.H2(
                "Candidate Search and Rescue Profile",
                style=SECTION_TITLE_STYLE,
            ),

            html.P(
                (
                    "Select a rescue profile to evaluate and rank "
                    "candidates. Optional breed, age, and outcome filters "
                    "can be used to narrow the displayed results."
                ),
                style={
                    "marginTop": "0",
                    "marginBottom": "20px",
                    "lineHeight": "1.5",
                },
            ),

            html.Div(
                [
                    # --------------------------------------------------
                    # RESCUE TYPE
                    # --------------------------------------------------

                    html.Div(
                        [
                            html.Label(
                                "Rescue Type",
                                htmlFor="filter-type",
                                style=LABEL_STYLE,
                            ),

                            dcc.Dropdown(
                                id="filter-type",
                                options=(
                                    rescue_type_options()
                                ),
                                value=(
                                    RESET_RESCUE_TYPE
                                ),
                                clearable=False,
                                searchable=False,
                                placeholder=(
                                    "Select rescue type"
                                ),
                            ),
                        ]
                    ),

                    # --------------------------------------------------
                    # BREED
                    # --------------------------------------------------

                    html.Div(
                        [
                            html.Label(
                                "Breed",
                                htmlFor="breed-filter",
                                style=LABEL_STYLE,
                            ),

                            dcc.Dropdown(
                                id="breed-filter",
                                options=(
                                    create_text_options(
                                        available_breeds
                                    )
                                ),
                                value=None,
                                clearable=True,
                                searchable=True,
                                placeholder=(
                                    "All breeds"
                                ),
                            ),
                        ]
                    ),

                    # --------------------------------------------------
                    # OUTCOME
                    # --------------------------------------------------

                    html.Div(
                        [
                            html.Label(
                                "Outcome Type",
                                htmlFor=(
                                    "outcome-filter"
                                ),
                                style=LABEL_STYLE,
                            ),

                            dcc.Dropdown(
                                id="outcome-filter",
                                options=(
                                    create_text_options(
                                        available_outcomes
                                    )
                                ),
                                value=None,
                                clearable=True,
                                searchable=True,
                                placeholder=(
                                    "All outcomes"
                                ),
                            ),
                        ]
                    ),

                    # --------------------------------------------------
                    # AGE RANGE
                    # --------------------------------------------------

                    html.Div(
                        [
                            html.Label(
                                "Age Range (Weeks)",
                                htmlFor="age-filter",
                                style=LABEL_STYLE,
                            ),

                            dcc.RangeSlider(
                                id="age-filter",
                                min=minimum_age,
                                max=maximum_age,
                                step=1,
                                value=[
                                    minimum_age,
                                    maximum_age,
                                ],
                                marks=marks,
                                tooltip={
                                    "placement":
                                        "bottom",

                                    "always_visible":
                                        False,
                                },
                                allowCross=False,
                            ),
                        ]
                    ),
                ],
                style=GRID_FOUR_COLUMNS_STYLE,
            ),
        ],
        style=CARD_STYLE,
    )


# ----------------------------------------------------------------------
# SUMMARY SECTION
# ----------------------------------------------------------------------


def build_summary_section() -> html.Div:
    """
    Build the dashboard's result-summary area.

    Callback functions will update the component contents.

    Returns:
        Dash summary-section component.
    """

    return html.Div(
        [
            html.Div(
                [
                    html.H3(
                        "Active View",
                        style={
                            "marginTop": "0",
                            "marginBottom": "8px",
                        },
                    ),

                    html.Div(
                        id="filter-label",
                        children=(
                            "Showing all available dog records."
                        ),
                    ),
                ],
                style=SUMMARY_CARD_STYLE,
            ),

            html.Div(
                [
                    html.H3(
                        "Results",
                        style={
                            "marginTop": "0",
                            "marginBottom": "8px",
                        },
                    ),

                    html.Div(
                        id="result-summary",
                        children=(
                            "Loading animal records..."
                        ),
                    ),
                ],
                style=SUMMARY_CARD_STYLE,
            ),
        ],
        style={
            **GRID_TWO_COLUMNS_STYLE,
            "marginBottom": "20px",
        },
    )


# ----------------------------------------------------------------------
# PROFILE EXPLANATION
# ----------------------------------------------------------------------


def build_profile_section() -> html.Div:
    """
    Build the rescue-profile explanation section.

    The callback will update profile-summary when a rescue category is
    selected.

    Returns:
        Dash profile-information component.
    """

    return html.Div(
        [
            html.H2(
                "How Rescue Candidates Are Evaluated",
                style=SECTION_TITLE_STYLE,
            ),

            html.Div(
                id="profile-summary",
                children=[
                    html.P(
                        (
                            "Select a rescue type to evaluate animals "
                            "against the rescue-training profile."
                        )
                    ),

                    build_score_weight_display(),
                ],
            ),
        ],
        style=CARD_STYLE,
    )


def build_score_weight_display() -> html.Div:
    """
    Display the recommendation scoring weights.

    Returns:
        Dash component showing the 100-point scoring model.
    """

    return html.Div(
        [
            html.H4(
                "Recommendation Scoring",
                style={
                    "marginBottom": "12px",
                },
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Strong(
                                str(
                                    SCORE_WEIGHTS[
                                        "breed"
                                    ]
                                )
                                + " Points"
                            ),

                            html.Br(),

                            html.Span(
                                "Preferred Breed"
                            ),
                        ],
                        style=SUMMARY_CARD_STYLE,
                    ),

                    html.Div(
                        [
                            html.Strong(
                                str(
                                    SCORE_WEIGHTS[
                                        "age"
                                    ]
                                )
                                + " Points"
                            ),

                            html.Br(),

                            html.Span(
                                "Preferred Age Range"
                            ),
                        ],
                        style=SUMMARY_CARD_STYLE,
                    ),

                    html.Div(
                        [
                            html.Strong(
                                str(
                                    SCORE_WEIGHTS[
                                        "sex"
                                    ]
                                )
                                + " Points"
                            ),

                            html.Br(),

                            html.Span(
                                "Preferred Sex"
                            ),
                        ],
                        style=SUMMARY_CARD_STYLE,
                    ),

                    html.Div(
                        [
                            html.Strong(
                                str(
                                    SCORE_WEIGHTS[
                                        "outcome"
                                    ]
                                )
                                + " Points"
                            ),

                            html.Br(),

                            html.Span(
                                "Preferred Outcome"
                            ),
                        ],
                        style=SUMMARY_CARD_STYLE,
                    ),
                ],
                style=GRID_FOUR_COLUMNS_STYLE,
            ),

            html.P(
                (
                    "Maximum recommendation score: "
                    "100 points."
                ),
                style={
                    "marginBottom": "0",
                    "marginTop": "14px",
                    "fontWeight": "bold",
                },
            ),
        ]
    )


# ----------------------------------------------------------------------
# TOP RECOMMENDATION
# ----------------------------------------------------------------------


def build_recommendation_section() -> html.Div:
    """
    Build the top-recommendation display area.

    Returns:
        Dash recommendation card container.
    """

    return html.Div(
        [
            html.H2(
                "Top Recommendation",
                style=SECTION_TITLE_STYLE,
            ),

            html.Div(
                id="recommendation-card",
                children=[
                    html.P(
                        (
                            "Select a rescue type to generate "
                            "candidate recommendations."
                        ),
                        style={
                            "margin": "0",
                        },
                    )
                ],
                style=RECOMMENDATION_CARD_STYLE,
            ),
        ],
        style=CARD_STYLE,
    )


# ----------------------------------------------------------------------
# DATA TABLE
# ----------------------------------------------------------------------


def build_data_table() -> html.Div:
    """
    Build the ranked animal-candidate table.

    The callback will supply the table data and columns.

    Returns:
        Dash DataTable section.
    """

    return html.Div(
        [
            html.H2(
                "Animal Candidates",
                style=SECTION_TITLE_STYLE,
            ),

            html.P(
                (
                    "Select a row to view the animal's available "
                    "location information on the map."
                ),
                style={
                    "marginTop": "0",
                    "marginBottom": "15px",
                },
            ),

            dash_table.DataTable(
                id="datatable-id",

                data=[],

                columns=[],

                selected_rows=[],

                row_selectable="single",

                sort_action="native",

                filter_action="native",

                page_action="native",

                page_current=0,

                page_size=10,

                style_table={
                    "overflowX": "auto",
                    "width": "100%",
                },

                style_header={
                    "fontWeight": "bold",
                    "textAlign": "left",
                    "whiteSpace": "normal",
                    "height": "auto",
                },

                style_cell={
                    "textAlign": "left",
                    "padding": "10px",
                    "minWidth": "100px",
                    "maxWidth": "280px",
                    "whiteSpace": "normal",
                    "height": "auto",
                    "fontFamily": (
                        "Arial, Helvetica, sans-serif"
                    ),
                    "fontSize": "14px",
                },

                style_data_conditional=[
                    {
                        "if": {
                            "state": "selected"
                        },
                        "fontWeight": "bold",
                    }
                ],
            ),
        ],
        style=CARD_STYLE,
    )


# ----------------------------------------------------------------------
# CHART AND MAP
# ----------------------------------------------------------------------


def build_visualization_section() -> html.Div:
    """
    Build the visualization and interactive-map containers.

    The callbacks will determine whether the graph displays:
    - Breed distribution in Reset mode, or
    - Top rescue recommendations when a rescue profile is selected.

    Returns:
        Two-column chart/map layout.
    """

    return html.Div(
        [
            # ----------------------------------------------------------
            # CHART
            # ----------------------------------------------------------

            html.Div(
                [
                    html.H2(
                        "Candidate Visualization",
                        style=SECTION_TITLE_STYLE,
                    ),

                    dcc.Graph(
                        id="graph-id",
                        figure={
                            "data": [],
                            "layout": {
                                "title": (
                                    "Loading visualization..."
                                )
                            },
                        },
                        config={
                            "displayModeBar": True,
                            "responsive": True,
                        },
                        style={
                            "width": "100%",
                            "minHeight": "480px",
                        },
                    ),
                ],
                style=CARD_STYLE,
            ),

            # ----------------------------------------------------------
            # MAP
            # ----------------------------------------------------------

            html.Div(
                [
                    html.H2(
                        "Selected Animal Location",
                        style=SECTION_TITLE_STYLE,
                    ),

                    html.Div(
                        id="map-id",
                        children=[
                            html.Div(
                                [
                                    html.P(
                                        (
                                            "Select an animal from the "
                                            "table to display available "
                                            "location information."
                                        ),
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
                                    "border": (
                                        "1px solid #dfe3e6"
                                    ),
                                    "borderRadius": "8px",
                                    "padding": "20px",
                                    "textAlign": "center",
                                },
                            )
                        ],
                    ),
                ],
                style=CARD_STYLE,
            ),
        ],
        style=GRID_TWO_COLUMNS_STYLE,
    )


# ----------------------------------------------------------------------
# STORES
# ----------------------------------------------------------------------


def build_internal_stores() -> html.Div:
    """
    Build client-side Dash stores used by callbacks.

    filtered-data-store keeps the current result set available for
    multiple callbacks without displaying internal map-coordinate fields
    in the DataTable.

    Returns:
        Hidden Dash Store container.
    """

    return html.Div(
        [
            dcc.Store(
                id="filtered-data-store",
                data=[],
                storage_type="memory",
            ),
        ]
    )


# ----------------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------------


def build_footer() -> html.Footer:
    """
    Build the dashboard footer.

    Returns:
        Dash footer component.
    """

    return html.Footer(
        [
            html.Hr(),

            html.P(
                (
                    "CS 499 Computer Science Capstone | "
                    "Software Design and Engineering Enhancement | "
                    "Monique Henry"
                ),
                style={
                    "textAlign": "center",
                    "fontSize": "13px",
                    "marginBottom": "0",
                },
            ),
        ],
        style={
            "paddingTop": "10px",
            "paddingBottom": "20px",
        },
    )


# ----------------------------------------------------------------------
# MAIN LAYOUT
# ----------------------------------------------------------------------


def build_layout(
    available_breeds: list[str] | None = None,
    available_outcomes: list[str] | None = None,
    age_bounds: tuple[float, float] | None = None,
    logo_path: str | Path | None = None,
) -> html.Div:
    """
    Build the complete Grazioso Salvare dashboard layout.

    Args:
        available_breeds:
            Breed values retrieved by DashboardService.

        available_outcomes:
            Shelter outcome values retrieved by DashboardService.

        age_bounds:
            Tuple containing minimum and maximum age values in weeks.

        logo_path:
            Path to the supplied Grazioso Salvare logo.

    Returns:
        Complete Dash layout.
    """

    available_breeds = (
        available_breeds
        if available_breeds is not None
        else []
    )

    available_outcomes = (
        available_outcomes
        if available_outcomes is not None
        else []
    )

    if age_bounds is None:

        minimum_age = 0.0
        maximum_age = 1000.0

    else:

        try:
            minimum_age = float(
                age_bounds[0]
            )

            maximum_age = float(
                age_bounds[1]
            )

        except (
            TypeError,
            ValueError,
            IndexError,
        ):

            minimum_age = 0.0
            maximum_age = 1000.0

    return html.Div(
        [
            # Internal state storage.
            build_internal_stores(),

            # Branding and title.
            build_header(
                logo_path
            ),

            # Rescue type and additional filters.
            build_filter_panel(
                available_breeds=(
                    available_breeds
                ),
                available_outcomes=(
                    available_outcomes
                ),
                minimum_age=minimum_age,
                maximum_age=maximum_age,
            ),

            # Active filters and result counts.
            build_summary_section(),

            # Explanation of selected rescue profile.
            build_profile_section(),

            # Highest-ranked recommendation.
            build_recommendation_section(),

            # Ranked candidate table.
            build_data_table(),

            # Chart and map.
            build_visualization_section(),

            # Course/artifact identification.
            build_footer(),
        ],
        style=PAGE_STYLE,
    )