# REPRISE :
# Prochaine etape : elargir la plage de temps de vol testee
# pour Terre-Saturne a 4-8 ans, puis revalider contre
# v_inf depart ~10.3 km/s theorique.

import math
from datetime import date, datetime

import pykep as pk


def norm(v):
    """Norme d'un vecteur 3D."""
    return math.sqrt(sum(x * x for x in v))


def sub(a, b):
    """Soustraction de deux vecteurs 3D."""
    return [a[i] - b[i] for i in range(3)]


def to_pk_epoch(value):
    """Convertit une date Python en epoch PyKEP."""
    if isinstance(value, datetime):
        return pk.epoch(
            value.strftime("%Y-%m-%d %H:%M:%S")
        )

    if isinstance(value, date):
        return pk.epoch(
            value.strftime("%Y-%m-%d 00:00:00")
        )

    if isinstance(value, pk.epoch):
        return value

    raise TypeError(
        f"Date non supportee: {type(value)}. "
        "Un datetime/date Python est attendu."
    )


def compute_trajectory(
    destination: str,
    departure_type: str,
    launch_start,
    launch_end,
    has_moon_transfer: bool,
    has_landing: bool,
    is_flyby_only: bool,
    dv_per_flyby: float,
) -> dict:

    # Premiere version du moteur:
    # Terre -> Saturne uniquement.
    if destination.lower() != "saturn":
        dv_budget = {
            "dV from LEO": 0.0,
            "dV DSM/Fly-By": 0.0,
            "dV Capture at Destination": 0.0,
            "dV Transfer to Moon": 0.0,
            "dV Capture at Moon": 0.0,
            "dV Lower to Final Orbit": 0.0,
            "dV Break for landing": 0.0,
            "dV Soft Landing": 0.0,
        }

        return {
            "dv_budget": dv_budget,
            "dv_total": 0.0,
            "best_launch_date": None,
            "arrival_date": None,
            "note": (
                f"Destination '{destination}' non encore implemente. "
                "Selectionnez Saturn pour tester le moteur "
                "Terre -> Saturne."
            ),
        }

    # Corps celestes
    earth = pk.planet(pk.udpla.jpl_lp("earth"))
    saturn = pk.planet(pk.udpla.jpl_lp("saturn"))

    # Conversion des dates fournies par app.py
    t_start = to_pk_epoch(launch_start)
    t_end = to_pk_epoch(launch_end)

    launch_window_days = (
        t_end.mjd2000 - t_start.mjd2000
    )

    if launch_window_days < 0:
        raise ValueError(
            "La date de fin de fenetre doit etre posterieure "
            "a la date de debut."
        )

    # Dates de depart a tester.
    n_departures = 12

    if n_departures == 1:
        departure_offsets = [0.0]
    else:
        departure_offsets = [
            launch_window_days * i / (n_departures - 1)
            for i in range(n_departures)
        ]

    # Temps de vol a tester (4-8 ans, pas ~15 jours).
    tof_step_days = 15.0
    tof_min_years = 4.0
    tof_max_years = 8.0
    tof_years_list = []
    tof_years = tof_min_years
    while tof_years <= tof_max_years + 1e-9:
        tof_years_list.append(tof_years)
        tof_years += tof_step_days / 365.25

    best = None

    for departure_offset in departure_offsets:

        departure_mjd2000 = (
            t_start.mjd2000 + departure_offset
        )

        # Etat heliocentrique de la Terre au depart.
        r0, v_earth = earth.eph(departure_mjd2000)

        for tof_years in tof_years_list:

            tof_seconds = tof_years * 365.25 * 86400.0

            arrival_mjd2000 = (
                departure_mjd2000
                + tof_seconds / 86400.0
            )

            # Etat heliocentrique de Saturne a l'arrivee.
            r1, v_saturn = saturn.eph(arrival_mjd2000)

            try:
                lp = pk.lambert_problem(
                    r0,
                    r1,
                    tof_seconds,
                    earth.get_mu_central_body(),
                    multi_revs=0,
                )
            except Exception:
                continue

            if len(lp.v0) == 0:
                continue

            v_depart = lp.v0[0]
            v_arrivee = lp.v1[0]

            # Exces hyperbolique heliocentrique au depart.
            dv_depart = norm(
                sub(v_depart, v_earth)
            )

            # Vitesse relative a Saturne a l'arrivee.
            # Ce n'est PAS encore une vraie capture orbitale.
            v_infinity_saturn = norm(
                sub(v_arrivee, v_saturn)
            )

            if best is None or dv_depart < best["dv_depart"]:
                best = {
                    "dv_depart": dv_depart,
                    "v_infinity_saturn": v_infinity_saturn,
                    "departure_mjd2000": departure_mjd2000,
                    "arrival_mjd2000": arrival_mjd2000,
                    "tof_years": tof_years,
                }

    if best is None:
        raise RuntimeError(
            "Aucune solution Lambert Terre -> Saturne "
            "n'a ete trouvee."
        )

    # Budget compatible avec app.py.
    #
    # ATTENTION:
    # v_infinity_saturn est provisoirement place dans
    # "dV Capture at Destination" uniquement pour
    # conserver le format attendu par l'application.
    # Ce n'est PAS encore un calcul physique de capture
    # autour de Saturne. Il sera remplace plus tard.
    dv_budget = {
        "dV from LEO": best["dv_depart"],
        "dV DSM/Fly-By": 0.0,
        "dV Capture at Destination": best["v_infinity_saturn"],
        "dV Transfer to Moon": 0.0,
        "dV Capture at Moon": 0.0,
        "dV Lower to Final Orbit": 0.0,
        "dV Break for landing": 0.0,
        "dV Soft Landing": 0.0,
    }

    dv_total = sum(dv_budget.values())

    best_launch_date = pk.epoch(
        best["departure_mjd2000"]
    )

    arrival_date = pk.epoch(
        best["arrival_mjd2000"]
    )

    note = (
        "Premiere version Terre -> Saturne avec Lambert "
        "(multi_revs=0). "
        "La vitesse relative a Saturne est affichee "
        "provisoirement dans le budget; la capture "
        "physique sera calculee dans une etape ulterieure. "
        "Saturne -> Titan, flyby, transfert lunaire et "
        "atterrissage ne sont pas encore implementes."
    )

    return {
        "dv_budget": dv_budget,
        "dv_total": dv_total,
        "best_launch_date": best_launch_date,
        "arrival_date": arrival_date,
        "note": note,
    }
