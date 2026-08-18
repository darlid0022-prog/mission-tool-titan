"""Centralized mission-phase color palette, shared by every page and chart.

Colors are assigned by **mission phase**, not by page or chart type, so the
same phase reads as the same color everywhere: 3D trajectory curves and
markers, the connected delta-v budget table, and the phase-labeled section
headers on the Saturn & Titan studies page.

Method: the `dataviz` skill's color-formula (fixed categorical hue slots,
OKLCH lightness/chroma bands, CVD-simulated pairwise separation, WCAG
contrast vs the chart surface). Every hex below is one of the skill's
validated default categorical slots (`references/palette.md`) - not
hand-picked - restricted to the five slots that individually clear 3:1
contrast on BOTH the light and dark chart surface (this app's own
requirement; the skill's default tolerates the other three slots -
yellow/aqua/magenta - at sub-3:1 on light with a "visible label" relief
clause, which this app does not want to rely on).

Our charts are Plotly *lines* (trajectory curves) and *ordered rows* (the
delta-v budget table, mission-phase section headers) in a fixed
chronological order - never a scatter/bubble/small-multiples layout where
any two marks can sit side by side - so the skill's *adjacent*-pairlist
check is the applicable one (not the stricter all-pairs check reserved for
those chart forms). Validated with the skill's validator in the exact
PHASE_ORDER below:

    node scripts/validate_palette.js \
        "#eb6834,#2a78d6,#008300,#4a3aa7,#e34948" --mode light
    node scripts/validate_palette.js \
        "#d95926,#3987e5,#008300,#9085e9,#e66767" --mode dark

Both runs: ALL CHECKS PASS (lightness band, chroma floor, CVD separation,
normal-vision floor, contrast vs surface) - no WARN, in either mode.
tests/test_colors.py re-checks the WCAG contrast leg of that (>= 3:1 for
each phase color against both chart surfaces) on every test run, since that
part is cheap to compute in pure Python; the CVD/lightness legs above are
the skill's own validator output, reproduced here for audit rather than
re-implemented.

The Plotly 3D trajectory scene renders on a fixed dark-navy background
regardless of the Streamlit page theme (see SCENE_BACKGROUND below), so
`trajectory_plot.py` always uses each PhaseColor's `.dark` step. Streamlit-
native elements (tables, badges, metrics) pick `.light`/`.dark` following
the active Streamlit theme instead.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseColor:
    """One mission phase's identity color, with matched light/dark steps."""

    label: str
    light: str
    dark: str
    evokes: str


LAUNCH = PhaseColor(
    label="Launch",
    light="#eb6834",
    dark="#d95926",
    evokes="ignition plasma",
)
INTERPLANETARY_TRANSFER = PhaseColor(
    label="Interplanetary transfer",
    light="#2a78d6",
    dark="#3987e5",
    evokes="deep-space void",
)
ARRIVAL = PhaseColor(
    label="Arrival / orbit insertion",
    light="#008300",
    dark="#008300",
    evokes="captured orbit, planetary limb",
)
LUNAR_TRANSFER = PhaseColor(
    label="Lunar transfer",
    light="#4a3aa7",
    dark="#9085e9",
    evokes="cislunar shadow",
)
LANDING = PhaseColor(
    label="Landing",
    light="#e34948",
    dark="#e66767",
    evokes="regolith heat, entry glow",
)

# Fixed chronological order - also the CVD-safe adjacency order validated
# together (see module docstring). Do not reorder without re-running the
# validator: the CVD/contrast checks above are pairwise on THIS sequence.
PHASE_ORDER: tuple[PhaseColor, ...] = (
    LAUNCH,
    INTERPLANETARY_TRANSFER,
    ARRIVAL,
    LUNAR_TRANSFER,
    LANDING,
)

# st.badge()'s `color` argument only accepts this fixed named set - it has
# no hex/custom-color option - but it is already a theme-aware Streamlit
# component (correct contrast in both the light and dark Streamlit theme
# without this app tracking which one is active). Mapping each phase to the
# badge color of the *same hue family* keeps phase identity visually
# consistent between native Streamlit widgets and the hex-controlled Plotly
# charts, even though the two won't be byte-identical hex.
BADGE_COLOR: dict[str, str] = {
    LAUNCH.label: "orange",
    INTERPLANETARY_TRANSFER.label: "blue",
    ARRIVAL.label: "green",
    LUNAR_TRANSFER.label: "violet",
    LANDING.label: "red",
}

# The 3D-animation phase names map onto phase colors so the live spacecraft
# marker (and its badge) always match the rest of the app. Two distinct
# string vocabularies name the same three phases and both are mapped here:
# mission/trajectory_visualization.py's SpacecraftPosition3D.phase_name
# (drives the marker/hover) and pages/trajectory_3d.py's
# ANIMATION_PHASE_OPTIONS (drives the segmented-control widget and the
# "Current mission phase" badge) - "Saturn arrival → staging" is the one
# string shared by both.
ANIMATION_PHASE_COLORS: dict[str, PhaseColor] = {
    "Earth → Saturn transfer": INTERPLANETARY_TRANSFER,
    "Saturn arrival → staging": ARRIVAL,
    "Saturn → Titan transfer": LUNAR_TRANSFER,
    "Earth → Saturn cruise": INTERPLANETARY_TRANSFER,
    "Saturn → Titan": LUNAR_TRANSFER,
}


@dataclass(frozen=True)
class ChromeColor:
    """A non-phase chart/UI color with matched light/dark steps."""

    light: str
    dark: str


# Reference/context elements: celestial-body orbit paths and landmark
# markers. Deliberately desaturated and NOT phase colors, so a reference
# orbit or a body marker is never mistaken for a spacecraft phase. Values
# unchanged from the pre-centralization figure - the 3D scene has always
# rendered on a fixed dark background regardless of Streamlit's theme (see
# SCENE_BACKGROUND), so there is no separate light-mode step to define here.
REFERENCE_ORBIT = "#7C8DA6"
REFERENCE_ORBIT_WARM = "#D9A441"
LANDMARK_SUN = "#FFD166"
LANDMARK_BODY = "#D9A441"
LANDMARK_MOON = "#E8D9B5"
SCENE_BACKGROUND = "rgba(13, 20, 33, 0.75)"
GRIDLINE = "rgba(160, 174, 192, 0.25)"
AXIS_ZERO_LINE = "rgba(255, 255, 255, 0.35)"
MARKER_RIM = "#ffffff"
MARKER_RIM_TRANSLUCENT = "rgba(255,255,255,0.55)"

# Trade-space (Pareto) highlight markers encode a *status* distinction
# (current baseline vs. the delta-v optimum), not a mission phase - kept on
# steps distinct from every PHASE_ORDER color so neither is ever mistaken
# for one. STATUS_GOOD reuses the skill's fixed, reserved status palette;
# NEUTRAL_BASELINE reuses its "secondary ink" text token.
STATUS_GOOD = ChromeColor(light="#0ca30c", dark="#0ca30c")
NEUTRAL_BASELINE = ChromeColor(light="#52514e", dark="#c3c2b7")

# Chart surfaces the WCAG contrast checks below (and tests/test_colors.py)
# measure every phase color against - the skill's own validated defaults.
LIGHT_SURFACE = "#fcfcfb"
DARK_SURFACE = "#1a1a19"


def _srgb_to_linear(channel: float) -> float:
    c = channel / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r_lin, g_lin, b_lin = (_srgb_to_linear(c) for c in (r, g, b))
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def wcag_contrast_ratio(hex_a: str, hex_b: str) -> float:
    """Return the WCAG 2.1 contrast ratio between two opaque hex colors.

    Formula: (L1 + 0.05) / (L2 + 0.05) with L1 the lighter relative
    luminance - symmetric, always >= 1.0. Used to check phase colors as
    graphical marks (curve lines, markers): WCAG's >= 3:1 non-text/large-text
    threshold, not the >= 4.5:1 normal-text one, since these colors are
    never used to color small body text in this app.
    """
    luminance_a = _relative_luminance(hex_a)
    luminance_b = _relative_luminance(hex_b)
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)
