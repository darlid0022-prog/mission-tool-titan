"""Single, cache-independent CSS entry point for the v0.3 Streamlit shell."""

from __future__ import annotations

import streamlit as st

UI_SHELL_STYLE = """
<style>
/* Only stable Streamlit test IDs and explicit application keys are targeted.
   No remote @font-face, no Google/CDN font import: every face here is
   whatever the browser/OS or Streamlit's own bundled fonts already provide.

   Top padding on stMainBlockContainer is a fixed, generous reserve (not tied
   to any scroll position) so the first heading on every page clears
   Streamlit's own fixed top header bar - identical on desktop and mobile, so
   neither breakpoint is asymmetrically tighter than the other. */
[data-testid="stMainBlockContainer"] {
    width: min(100%, 72rem);
    max-width: 72rem;
    padding-top: 5rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    border-right: 1px solid color-mix(in srgb, currentColor 14%, transparent);
}

/* One shared, 8px-grid vertical rhythm between stacked elements, tighter
   than Streamlit's default gap - applied globally from this single rule
   rather than scattered per-page spacing. */
[data-testid="stVerticalBlock"] {
    gap: 0.5rem;
}

h1 {
    font-size: clamp(2rem, 3vw, 2.5rem) !important;
    line-height: normal !important;
    letter-spacing: -0.025em;
    margin-top: 0 !important;
    margin-bottom: 0.5rem !important;
    overflow: visible;
}

h2 {
    font-size: clamp(1.375rem, 2.5vw, 1.75rem) !important;
    line-height: normal !important;
    margin-top: 1rem !important;
    margin-bottom: 0.5rem !important;
}

h3 {
    font-size: clamp(1.05rem, 2vw, 1.25rem) !important;
    line-height: normal !important;
    margin-top: 0.75rem !important;
    margin-bottom: 0.5rem !important;
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
        padding: 5rem 1rem 2.5rem;
    }

    h1 {
        font-size: clamp(1.75rem, 6vw, 2rem) !important;
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
