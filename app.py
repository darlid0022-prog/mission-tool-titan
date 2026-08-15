"""Streamlit interface for the Mission Design Calculator."""

import pandas as pd
import streamlit as st

from app_services import PHYSICS_MODEL_VERSION, compute_cached_trajectory
from mission.capabilities import (
    PLANNED_DESTINATIONS,
    PLANNED_MISSION_FEATURES,
    SUPPORTED_DESTINATIONS,
)
from mission.moon_transfer import compute_saturn_titan_transfer
from mission.sizing import compute_mass_budget

st.set_page_config(page_title="Mission Design - Titan", layout="wide")
st.title(":material/satellite_alt: Mission Design Calculator")
st.caption(
    "Version actuelle : transfert Terre → Saturne et étude préliminaire séparée "
    "de la jambe Saturne → Titan."
)

# -----------------------------------------------------------------------
# 2. ENTRÉES - colonne de gauche : architecture de mission
# -----------------------------------------------------------------------
col_inputs, col_results = st.columns([1, 2])

with col_inputs:
    with st.form("orbital_inputs"):
        st.header("1. Architecture de mission")
        destination = st.selectbox(
            "Destination calculable",
            SUPPORTED_DESTINATIONS,
            help="Seule Saturne est actuellement reliée au moteur de trajectoire.",
        )
        departure_type = st.radio("Type de départ", ["Direct", "LEO"])
        leo_altitude_km = st.number_input(
            "Altitude LEO initiale (km)",
            min_value=100,
            value=250,
            help="Utilisée uniquement lorsque le type de départ est LEO.",
        )
        capture_altitude_km = st.number_input(
            "Altitude de capture à Saturne (km)", min_value=0, value=2000
        )

        st.header("2. Fenêtre de lancement")
        launch_window_start = st.date_input("Date de lancement - début")
        launch_window_end = st.date_input("Date de lancement - fin")
        st.form_submit_button("Calculer la trajectoire", icon=":material/calculate:")

    st.info(
        "Titan n'est pas encore une destination de mission complète. Une étude "
        "préliminaire Saturne → Titan est disponible séparément plus bas."
    )

    with st.expander("Capacités planifiées"):
        st.write("Destinations : " + ", ".join(PLANNED_DESTINATIONS))
        for feature in PLANNED_MISSION_FEATURES:
            st.write(f"- {feature}")

    st.header("3. Propulsion")
    isp_s = st.number_input("Isp moteur principal (s)", min_value=1, value=320)

    st.header("4. Instruments")
    st.caption("Ajoute/édite les lignes directement dans le tableau ci-dessous.")
    default_instruments = pd.DataFrame(
        [
            {
                "Instrument": "",
                "Cible": "Orbiter",
                "Masse (kg)": 0.0,
                "Puissance (W)": 0.0,
                "Débit (bps)": 0.0,
            },
        ]
    )
    instruments_df = st.data_editor(
        default_instruments,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Masse (kg)": st.column_config.NumberColumn(min_value=0.0),
            "Puissance (W)": st.column_config.NumberColumn(min_value=0.0),
            "Débit (bps)": st.column_config.NumberColumn(min_value=0.0),
        },
    )

if launch_window_end < launch_window_start:
    st.error("La date de fin doit être postérieure ou égale à la date de début.")
    st.stop()

with st.spinner("Calcul de la trajectoire Terre → Saturne…"):
    traj = compute_cached_trajectory(
        PHYSICS_MODEL_VERSION,
        destination,
        departure_type,
        launch_window_start,
        launch_window_end,
        leo_altitude_km,
        capture_altitude_km,
    )
mass = compute_mass_budget(traj["dv_total"], isp_s, instruments_df)
mass_ratio = mass["wet_mass_kg"] / mass["dry_mass_kg"] if mass["dry_mass_kg"] > 0 else 1.0

with col_results:
    st.header("Résultats (mis à jour en direct)")
    st.info(traj["note"])

    st.subheader("Budget (provisoire)")
    st.caption(
        "Les valeurs affichées incluent désormais les ΔV propulsifs calcules pour "
        "l'evasion depuis LEO (si selection LEO) et la capture a Saturne. Les autres "
        "lignes restent provisoires."
    )
    dv_table = pd.DataFrame(traj["dv_budget"].items(), columns=["Manoeuvre", "Valeur (m/s)"])
    st.dataframe(dv_table, width="stretch")
    st.metric("Somme des ΔV / valeurs budget", f"{traj['dv_total']:.0f} m/s")

    st.subheader("Budget de masse")
    if departure_type == "Direct":
        st.warning(
            "Le mode Direct traite encore le v∞ de départ comme un ΔV équivalent "
            "provisoire. Le budget de masse ne constitue pas un dimensionnement de lanceur."
        )
    if mass_ratio > 20:
        st.warning(
            f"Rapport de masse estimé : {mass_ratio:,.0f}. Une propulsion chimique à "
            f"{isp_s:.0f} s est irréaliste pour ce budget de ΔV sans architecture multi-étages."
        )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Masse instruments", f"{mass['instrument_mass_kg']:.1f} kg")
    c2.metric("Masse sèche", f"{mass['dry_mass_kg']:.1f} kg")
    c3.metric("Masse d'ergols", f"{mass['propellant_mass_kg']:.1f} kg")
    c4.metric("Masse totale (wet)", f"{mass['wet_mass_kg']:.1f} kg")

st.divider()
st.header("Saturne → Titan — modèle préliminaire")
st.warning(
    "Budget partiel : la phase entre l'arrivée/capture à Saturne et l'orbite "
    "d'attente autour de Saturne n'est pas modélisée. Les résultats ci-dessous "
    "ne sont donc pas ajoutés au budget global ni au dimensionnement de masse."
)

with st.container(border=True):
    st.subheader("Paramètres de l'étude")
    titan_input_1, titan_input_2 = st.columns(2)
    with titan_input_1:
        saturn_staging_radius_km = st.number_input(
            "Rayon de l'orbite d'attente autour de Saturne (km)",
            min_value=480_001,
            max_value=1_221_899,
            value=600_000,
            step=1_000,
            help=(
                "Rayon mesuré depuis le centre de Saturne. La limite basse est "
                "placée au-delà de la garde préliminaire des anneaux."
            ),
        )
    with titan_input_2:
        titan_capture_altitude_km = st.number_input(
            "Altitude de capture autour de Titan (km)",
            min_value=1_000,
            value=1_500,
            step=100,
            help=(
                "Altitude au-dessus du rayon moyen de Titan. Le modèle impose "
                "une garde non atmosphérique préliminaire de 1 000 km."
            ),
        )

    titan_transfer = compute_saturn_titan_transfer(
        saturn_staging_radius_m=float(saturn_staging_radius_km) * 1_000.0,
        titan_capture_altitude_m=float(titan_capture_altitude_km) * 1_000.0,
    )

    st.caption(
        f"Méthode : `{titan_transfer.method}` · Source : `{titan_transfer.source}` · "
        "Calcul circulaire, coplanaire et impulsif."
    )
    with st.container(horizontal=True):
        st.metric(
            "ΔV de départ depuis l'orbite d'attente",
            f"{titan_transfer.departure_delta_v_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            "v∞ relatif à Titan (non propulsif)",
            f"{titan_transfer.v_infinity_titan_m_s:,.1f} m/s",
            help="Vitesse hyperbolique d'arrivée, distincte d'un ΔV propulsif.",
            border=True,
        )
        st.metric(
            "ΔV de capture à Titan",
            f"{titan_transfer.capture_delta_v_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            "ΔV total modélisé (partiel)",
            f"{titan_transfer.total_delta_v_m_s:,.1f} m/s",
            border=True,
        )

    st.metric(
        "Temps de vol Saturne → Titan",
        f"{titan_transfer.time_of_flight_days:.3f} jours",
        help=f"{titan_transfer.time_of_flight_s:,.0f} secondes.",
        border=True,
    )

    with st.expander("Hypothèses et exclusions du modèle"):
        st.markdown("**Hypothèses**")
        for assumption in titan_transfer.assumptions:
            st.write(f"- {assumption}")
        st.markdown("**Exclusions**")
        for exclusion in titan_transfer.exclusions:
            st.write(f"- {exclusion}")
