"""Deterministic, presentation-ready PDF export for one computed mission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fpdf import FPDF

from . import colors


@dataclass(frozen=True)
class MissionPdfReport:
    """Already-computed values rendered by the mission-summary PDF."""

    destination: str
    selected_moon: str | None
    launch_window_start: date
    launch_window_end: date
    departure_mjd2000: float
    arrival_mjd2000: float
    mission_duration_days: float
    method: str
    v_inf_depart_m_s: float
    v_inf_arrival_m_s: float
    delta_v_rows: tuple[tuple[str, float], ...]
    delta_v_total_m_s: float

    @property
    def route(self) -> str:
        route = f"Earth -> {self.destination}"
        return f"{route} -> {self.selected_moon}" if self.selected_moon else route


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )


def _pdf_safe(value: object) -> str:
    """Keep built-in Helvetica output deterministic and free of Unicode gaps."""
    return (
        str(value)
        .replace("→", "->")
        .replace("∞", "infinity")
        .replace("—", "-")
        .replace("–", "-")
        .replace("×", "x")
    )


def _section_title(pdf: FPDF, title: str) -> None:
    pdf.set_fill_color(*_rgb(colors.INTERPLANETARY_TRANSFER.light))
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, _pdf_safe(title), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _key_value_row(pdf: FPDF, label: str, value: str, *, fill: bool = False) -> None:
    if fill:
        pdf.set_fill_color(238, 244, 249)
    pdf.set_text_color(25, 38, 55)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(72, 7, _pdf_safe(label), border=1, fill=fill)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(108, 7, _pdf_safe(value), border=1, fill=fill, new_x="LMARGIN", new_y="NEXT")


def generate_mission_summary_pdf(report: MissionPdfReport) -> bytes:
    """Generate a one-page PDF from values already displayed in the application."""
    if not report.delta_v_rows:
        raise ValueError("At least one delta-v row is required for the PDF report.")

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_compression(False)  # Keeps regression-value assertions inspectable.
    pdf.add_page()

    pdf.set_fill_color(*_rgb(colors.INTERPLANETARY_TRANSFER.dark))
    pdf.rect(0, 0, 210, 31, style="F")
    pdf.set_xy(15, 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 8, "Mission design summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, _pdf_safe(report.route), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(37)

    _section_title(pdf, "Mission overview")
    _key_value_row(pdf, "Destination", report.destination, fill=True)
    _key_value_row(pdf, "Moon destination", report.selected_moon or "None")
    _key_value_row(
        pdf,
        "Launch window",
        f"{report.launch_window_start.isoformat()} to {report.launch_window_end.isoformat()}",
        fill=True,
    )
    _key_value_row(pdf, "Mission duration", f"{report.mission_duration_days:,.3f} days")
    pdf.ln(5)

    _section_title(pdf, "Connected propulsive delta-v budget")
    pdf.set_fill_color(*_rgb(colors.ARRIVAL.light))
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(135, 8, "Maneuver", border=1, fill=True)
    pdf.cell(45, 8, "Delta-v (m/s)", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    for index, (label, value_m_s) in enumerate(report.delta_v_rows):
        fill = index % 2 == 0
        if fill:
            pdf.set_fill_color(238, 244, 249)
        pdf.set_text_color(25, 38, 55)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(135, 7, _pdf_safe(label), border=1, fill=fill)
        pdf.cell(
            45,
            7,
            f"{value_m_s:,.3f}",
            border=1,
            fill=fill,
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.set_fill_color(*_rgb(colors.LUNAR_TRANSFER.light))
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(135, 8, "Total connected delta-v", border=1, fill=True)
    pdf.cell(
        45,
        8,
        f"{report.delta_v_total_m_s:,.3f}",
        border=1,
        fill=True,
        align="R",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(5)

    _section_title(pdf, "Trajectory summary")
    _key_value_row(pdf, "Method", report.method, fill=True)
    _key_value_row(pdf, "Selected departure epoch", f"{report.departure_mjd2000:,.6f} MJD2000")
    _key_value_row(
        pdf,
        "Selected arrival epoch",
        f"{report.arrival_mjd2000:,.6f} MJD2000",
        fill=True,
    )
    _key_value_row(pdf, "Departure v-infinity", f"{report.v_inf_depart_m_s:,.3f} m/s")
    _key_value_row(pdf, "Arrival v-infinity", f"{report.v_inf_arrival_m_s:,.3f} m/s", fill=True)

    # The report content fits on one A4 page. Disable the automatic break only
    # for the fixed footer so positioning it in the bottom margin cannot create
    # a spurious footer-only second page.
    pdf.set_auto_page_break(auto=False)
    pdf.set_y(-13)
    pdf.set_text_color(90, 105, 122)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0,
        5,
        "Generated by Titan Mission Tool - values reflect the selected model inputs.",
        align="C",
    )
    return bytes(pdf.output())
