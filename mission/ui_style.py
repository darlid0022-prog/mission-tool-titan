"""Single, cache-independent CSS entry point for the v0.3 Streamlit shell."""

from __future__ import annotations

import streamlit as st

UI_SHELL_STYLE = """
<style>
/* Only stable Streamlit test IDs and explicit application keys are targeted. */
[data-testid="stMainBlockContainer"] {
    width: min(100%, 72rem);
    max-width: 72rem;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    border-right: 1px solid color-mix(in srgb, currentColor 14%, transparent);
}

h1 {
    font-size: clamp(2rem, 3vw, 2.5rem) !important;
    line-height: 1.08 !important;
    letter-spacing: -0.025em;
    margin-bottom: 0.5rem !important;
}

h2 {
    font-size: clamp(1.35rem, 2.5vw, 1.75rem) !important;
    line-height: 1.2 !important;
    margin-top: 1.5rem !important;
}

h3 {
    font-size: clamp(1.05rem, 2vw, 1.25rem) !important;
    line-height: 1.25 !important;
}

div[data-testid="stMetricValue"] > div {
    white-space: normal;
    overflow-wrap: anywhere;
    font-size: clamp(1.25rem, 3vw, 1.8rem);
    line-height: 1.15;
}

.st-key-trajectory_direct_card,
.st-key-trajectory_launch_card {
    min-width: min(100%, 19rem);
}

@media (max-width: 48rem) {
    [data-testid="stMainBlockContainer"] {
        width: 100%;
        padding: 3.5rem 1rem 2.5rem;
    }

    h1 {
        font-size: clamp(1.8rem, 10vw, 2.1rem) !important;
    }

    .st-key-trajectory_direct_card,
    .st-key-trajectory_launch_card {
        min-width: 100%;
    }
}
</style>
"""


def apply_ui_shell_style() -> None:
    """Load the complete shell style once, before the selected page renders."""
    st.html(UI_SHELL_STYLE)
