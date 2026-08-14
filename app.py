"""
Mission Design Calculator - squelette de départ
=================================================
À lancer avec :  streamlit run app.py

Structure du projet recommandée :
mission_tool/
├── app.py              <- ce fichier (interface + orchestration)
├── trajectory.py        <- TODO Hermès : moteur pykep (Lambert / MGA)
├── sizing.py             <- moteur de dimensionnement (déjà esquissé ici)
└── requirements.txt      <- streamlit, pykep, pandas, numpy

Comportement : Streamlit relance TOUT le script à chaque interaction
(changement de planète, d'instrument, de contrainte) -> effet "tableur live"
sans rien avoir à cliquer sur "recalculer".
"""

import streamlit as st
import pandas as pd
import numpy as np
from trajectory import compute_trajectory

# -----------------------------------------------------------------------
# 1. LISTE DES DESTINATIONS - identique au menu déroulant B6 de l'Excel
#    (Mission Design sheet, plage J4:J19)
# -----------------------------------------------------------------------
PLANETS = [
    "Mercury", "Venus", "Mars", "Phobos", "Deimos", "Ceres",
    "Jupiter", "Io", "Europa", "Ganymede", "Callisto",
    "Saturn", "Titan", "Uranus", "Neptune", "Pluto",
]

st.set_page_config(page_title="Mission Design - Titan", layout="wide")
st.title("🛰️ Mission Design Calculator")

# -----------------------------------------------------------------------
# 2. ENTRÉES - colonne de gauche : architecture de mission
# -----------------------------------------------------------------------
col_inputs, col_results = st.columns([1, 2])

with col_inputs:
    st.header("1. Architecture de mission")
    destination = st.selectbox("Destination", PLANETS, index=PLANETS.index("Titan"))
    departure_type = st.radio("Type de départ", ["Direct", "LEO"])
    if departure_type == "LEO":
        leo_altitude_km = st.number_input("Altitude LEO initiale (km)", min_value=250, value=250)
    capture_altitude_km = st.number_input("Altitude de capture (km)", value=2000)
    final_orbit_altitude_km = st.number_input("Altitude orbite finale (km)", value=100)
    has_moon_transfer = st.checkbox("Transfert vers une lune (ex: Titan autour de Saturne)", value=True)
    has_landing = st.checkbox("Atterrissage (lander)", value=False)
    is_flyby_only = st.checkbox("Survol uniquement (pas de capture orbitale)", value=False)

    st.header("2. Fenêtre de lancement")
    launch_window_start = st.date_input("Date de lancement - début")
    launch_window_end = st.date_input("Date de lancement - fin")

    st.header("3. Propulsion")
    isp_s = st.number_input("Isp moteur principal (s)", value=320)
    dv_per_flyby = st.number_input("ΔV gagné par flyby (m/s)", value=1000)

    st.header("4. Instruments")
    st.caption("Ajoute/édite les lignes directement dans le tableau ci-dessous.")
    default_instruments = pd.DataFrame([
        {"Instrument": "", "Cible": "Orbiter", "Masse (kg)": 0.0, "Puissance (W)": 0.0, "Débit (bps)": 0.0},
    ])
    instruments_df = st.data_editor(default_instruments, num_rows="dynamic", use_container_width=True)

# -----------------------------------------------------------------------
# 3. MOTEUR TRAJECTOIRE  --  TODO HERMÈS : brancher pykep ici
# -----------------------------------------------------------------------

# -----------------------------------------------------------------------
# 4. MOTEUR DE DIMENSIONNEMENT (transcription de la logique Excel)
#    -> celui-ci est déjà fonctionnel, pas besoin d'attendre Hermès
# -----------------------------------------------------------------------
def compute_mass_budget(dv_total: float, isp_s: float, instruments_df: pd.DataFrame,
                         harness_frac=0.10, structure_frac=0.20, margin_frac=0.20) -> dict:
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
traj = compute_trajectory(
    destination, departure_type, launch_window_start, launch_window_end,
    has_moon_transfer, has_landing, is_flyby_only, dv_per_flyby,
)
mass = compute_mass_budget(traj["dv_total"], isp_s, instruments_df)

with col_results:
    st.header("Résultats (mis à jour en direct)")
    st.info(traj["note"])

    st.subheader("Budget (provisoire - valeurs v∞, pas ΔV propulsif)")
    st.caption(
        "Les valeurs affichées sont des vitesses d'exces heliocentriques (v∞) "
        "et non des Delta-V propulsifs complets (LEO escape / capture non calcules)."
    )
    dv_table = pd.DataFrame(traj["dv_budget"].items(), columns=["Manoeuvre", "v∞ (m/s)"])
    st.dataframe(dv_table, use_container_width=True)
    st.metric("Somme des v∞ (provisoire)", f"{traj['dv_total']:.0f} m/s")

    st.subheader("Budget de masse")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Masse instruments", f"{mass['instrument_mass_kg']:.1f} kg")
    c2.metric("Masse sèche", f"{mass['dry_mass_kg']:.1f} kg")
    c3.metric("Masse d'ergols", f"{mass['propellant_mass_kg']:.1f} kg")
    c4.metric("Masse totale (wet)", f"{mass['wet_mass_kg']:.1f} kg")
