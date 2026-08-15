"""Streamlit interface for the Mission Design Calculator."""

import numpy as np
import pandas as pd
import streamlit as st

from mission.capabilities import (
    PLANNED_DESTINATIONS,
    PLANNED_MISSION_FEATURES,
    SUPPORTED_DESTINATIONS,
)
from trajectory import compute_trajectory

st.set_page_config(page_title="Mission Design - Titan", layout="wide")
st.title(":material/satellite_alt: Mission Design Calculator")
st.caption(
    "Version actuelle : transfert Terre → Saturne. "
    "La jambe Saturne → Titan est la prochaine capacité planifiée."
)

# -----------------------------------------------------------------------
# 2. ENTRÉES - colonne de gauche : architecture de mission
# -----------------------------------------------------------------------
col_inputs, col_results = st.columns([1, 2])

with col_inputs:
    st.header("1. Architecture de mission")
    destination = st.selectbox(
        "Destination calculable",
        SUPPORTED_DESTINATIONS,
        help="Seule Saturne est actuellement reliée au moteur de trajectoire.",
    )
    st.info(
        "Titan est planifié, mais son transfert depuis Saturne n'est pas encore "
        "implémenté. Aucun résultat Titan n'est présenté comme calculé."
    )
    departure_type = st.radio("Type de départ", ["Direct", "LEO"])
    # Expose LEO altitude when relevant; provide a default value so the
    # compute_trajectory() call always receives the parameter.
    if departure_type == "LEO":
        leo_altitude_km = st.number_input("Altitude LEO initiale (km)", min_value=100, value=250)
    else:
        leo_altitude_km = 250
    capture_altitude_km = st.number_input(
        "Altitude de capture à Saturne (km)", min_value=0, value=2000
    )

    with st.expander("Capacités planifiées"):
        st.write("Destinations : " + ", ".join(PLANNED_DESTINATIONS))
        for feature in PLANNED_MISSION_FEATURES:
            st.write(f"- {feature}")

    st.header("2. Fenêtre de lancement")
    launch_window_start = st.date_input("Date de lancement - début")
    launch_window_end = st.date_input("Date de lancement - fin")

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


# -----------------------------------------------------------------------
# 4. MOTEUR DE DIMENSIONNEMENT (transcription de la logique Excel)
#    -> celui-ci est déjà fonctionnel, pas besoin d'attendre Hermès
# -----------------------------------------------------------------------
def compute_mass_budget(
    dv_total: float,
    isp_s: float,
    instruments_df: pd.DataFrame,
    harness_frac=0.10,
    structure_frac=0.20,
    margin_frac=0.20,
) -> dict:
    g0 = 9.80665
    instrument_mass = instruments_df["Masse (kg)"].fillna(0).sum()

    # Masse sèche = instruments + sous-systèmes estimés en % (comme l'onglet Dry Mass)
    subsystems_mass = instrument_mass  # TODO affiner avec Data Handling/Comm/Thermal/etc.
    dry_mass_before_margin = subsystems_mass * (1 + harness_frac + structure_frac)
    dry_mass = dry_mass_before_margin * (1 + margin_frac)

    # Équation de Tsiolkovski pour la masse d'ergols
    if dv_total > 0 and isp_s > 0:
        mass_ratio = np.exp(dv_total / (isp_s * g0))
        wet_mass = dry_mass * mass_ratio
        propellant_mass = wet_mass - dry_mass
    else:
        wet_mass = dry_mass
        propellant_mass = 0.0

    return {
        "instrument_mass_kg": instrument_mass,
        "dry_mass_kg": dry_mass,
        "propellant_mass_kg": propellant_mass,
        "wet_mass_kg": wet_mass,
    }


# -----------------------------------------------------------------------
# 5. CALCUL EN DIRECT (relancé automatiquement par Streamlit)
# -----------------------------------------------------------------------
if launch_window_end < launch_window_start:
    st.error("La date de fin doit être postérieure ou égale à la date de début.")
    st.stop()

with st.spinner("Calcul de la trajectoire Terre → Saturne…"):
    traj = compute_trajectory(
        destination,
        departure_type,
        launch_window_start,
        launch_window_end,
        False,  # Moon transfer is not exposed until it is implemented.
        False,  # Landing is not exposed until it is implemented.
        False,  # Flyby-only mode is not exposed until it is implemented.
        0.0,  # No artificial flyby credit is applied.
        leo_altitude_km,
        capture_altitude_km,
    )
mass = compute_mass_budget(traj["dv_total"], isp_s, instruments_df)

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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Masse instruments", f"{mass['instrument_mass_kg']:.1f} kg")
    c2.metric("Masse sèche", f"{mass['dry_mass_kg']:.1f} kg")
    c3.metric("Masse d'ergols", f"{mass['propellant_mass_kg']:.1f} kg")
    c4.metric("Masse totale (wet)", f"{mass['wet_mass_kg']:.1f} kg")
