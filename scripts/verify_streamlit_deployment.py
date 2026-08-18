#!/usr/bin/env python3
"""Production smoke test for the Streamlit Community Cloud environment."""

from __future__ import annotations

import argparse
import importlib
import math
import os
import resource
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CACHE_ROOT = Path(tempfile.gettempdir()) / "mission-tool-deployment-cache"
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_ROOT / "xdg"))
for cache_dir in (Path(os.environ["MPLCONFIGDIR"]), Path(os.environ["XDG_CACHE_HOME"])):
    cache_dir.mkdir(parents=True, exist_ok=True)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _verify_imports() -> None:
    modules = (
        "streamlit",
        "pandas",
        "numpy",
        "plotly",
        "pykep",
        "fpdf",
        "app_services",
        "mission.launch_search",
        "mission.trajectory_plot",
        "mission.pdf_report",
    )
    for module in modules:
        importlib.import_module(module)
    print(f"imports: OK ({len(modules)} modules)")


def _reference_search(*, detailed: bool) -> object:
    from mission.launch_search import search_direct_earth_saturn_titan
    from mission.launch_search_models import LaunchSearchConfig, SearchObjective

    config = LaunchSearchConfig(
        launch_start=date(2028, 1, 1),
        launch_end=date(2032, 1, 1),
        min_time_of_flight_days=1_600.0,
        max_time_of_flight_days=3_200.0,
        departure_step_days=60.0,
        arrival_step_days=60.0,
        objective=SearchObjective.MINIMUM_TOTAL_DELTA_V,
        keep_count=5,
        refinement_count=3 if detailed else 0,
        fast_mode=not detailed,
    )
    started = time.perf_counter()
    result = search_direct_earth_saturn_titan(config)
    elapsed = time.perf_counter() - started
    if len(result.solutions) != 5:
        raise AssertionError("Reference search must retain exactly five candidates.")
    best = result.solutions[0]
    if not detailed:
        if best.launch_date != "2028-06-29":
            raise AssertionError(f"Unexpected reference launch date: {best.launch_date}")
        if not math.isclose(best.total_delta_v_m_s, 12_554.539828782317, abs_tol=0.1):
            raise AssertionError(f"Unexpected reference delta-v: {best.total_delta_v_m_s}")
    mode = "detailed" if detailed else "fast"
    print(
        f"search-{mode}: OK; {elapsed:.2f} s; {result.evaluated_pair_count} pairs; "
        f"best={best.launch_date}, {best.total_delta_v_m_s:.3f} m/s"
    )
    return best


def _verify_exports(scenario: object) -> None:
    from mission.pdf_report import MissionPdfReport, generate_mission_summary_pdf
    from mission.trajectory_plot import build_scene_figure, scene_figure_to_standalone_html
    from mission.trajectory_scene import segments_from_launch_search

    html_sizes: list[int] = []
    for frame, unit in (("heliocentric", "AU"), ("saturn_centred", "km")):
        source = tuple(
            segment
            for segment in scenario.segments
            if segment.frame == frame and segment.unit == unit
        )
        if not source:
            raise AssertionError(f"Missing {frame}/{unit} trajectory segments.")
        segments = segments_from_launch_search(source, reference_frame=frame, distance_unit=unit)
        figure = build_scene_figure(segments, unit_label=unit)
        html = scene_figure_to_standalone_html(figure)
        if "plotly" not in html.lower():
            raise AssertionError("Standalone trajectory export is incomplete.")
        html_sizes.append(len(html.encode("utf-8")))

    report = MissionPdfReport(
        destination="Saturn",
        selected_moon="Titan",
        launch_window_start=date(2028, 1, 1),
        launch_window_end=date(2032, 1, 1),
        departure_mjd2000=scenario.launch_mjd2000,
        arrival_mjd2000=scenario.saturn_arrival_mjd2000,
        mission_duration_days=scenario.total_duration_days,
        method="Direct Lambert search",
        v_inf_depart_m_s=scenario.earth_v_infinity_m_s,
        v_inf_arrival_m_s=scenario.saturn_v_infinity_m_s,
        delta_v_rows=scenario.delta_v_by_manoeuvre_m_s,
        delta_v_total_m_s=scenario.total_delta_v_m_s,
    )
    pdf = generate_mission_summary_pdf(report)
    if not pdf.startswith(b"%PDF"):
        raise AssertionError("PDF export is invalid.")
    print(f"exports: OK; HTML={html_sizes} bytes; PDF={len(pdf)} bytes")


def _verify_share_urls() -> None:
    from app_services import build_mission_share_url

    public_url = build_mission_share_url(
        "https://mission-tool-titan.streamlit.app/", {"mission": "test-token"}
    )
    local_url = build_mission_share_url("http://localhost:8501/", {"mission": "test-token"})
    if public_url != "https://mission-tool-titan.streamlit.app/?mission=test-token":
        raise AssertionError(f"Unexpected public share URL: {public_url}")
    if local_url != "http://localhost:8501/?mission=test-token":
        raise AssertionError(f"Unexpected local share URL: {local_url}")
    print("share-urls: OK")


def _verify_server() -> None:
    port = _free_port()
    command = (
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless=true",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    )
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
    )
    deadline = time.monotonic() + 60.0
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Streamlit exited with status {process.returncode}.")
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/_stcore/health", timeout=2.0
                ) as response:
                    health = response.read().decode("utf-8")
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2.0) as response:
                    main_page = response.read()
                if health.strip().lower() == "ok" and main_page:
                    print(f"streamlit-server: OK; port={port}")
                    return
            except OSError:
                time.sleep(0.25)
        raise TimeoutError("Streamlit did not become healthy within 60 seconds.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Use the refined search instead of the fast UI reference search.",
    )
    parser.add_argument("--skip-server", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    _verify_imports()
    scenario = _reference_search(detailed=args.detailed)
    _verify_exports(scenario)
    _verify_share_urls()
    if not args.skip_server:
        _verify_server()
    max_rss_native = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(
        f"verification: OK; {time.perf_counter() - started:.2f} s; maxrss_native={max_rss_native}"
    )


if __name__ == "__main__":
    main()
