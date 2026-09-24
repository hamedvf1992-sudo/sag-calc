from __future__ import annotations

from dataclasses import dataclass, asdict
from math import pi, sqrt
import numpy as np


@dataclass
class LoadCase:
    name: str
    wind: float
    ice: float
    temp: float
    limit_ratio: float
    unit_weight: float = 0.0


DEFAULTS = {
    "UTS": 8850.0,
    "CTemp": 85.0,
    "ATemp": 15.0,
    "E": 8360.0,
    "alpha": 19e-6,
    "Cd": 21.78,
    "CA": 281.03,
    "Cwei": 0.976,
    "Span": 200.0,
    "rho": 913.0,
    "initial_tension_ratio": 0.5,
    "tower_height": 25.0,
}

LIMITS = {
    "High Wind": 0.50,
    "Heavy Ice": 0.50,
    "Wind + Ice": 0.40,
    "Wind Bare": 0.40,
    "NESC": 0.40,
    "EDS": 0.075,
    "Max Temp": 0.25,
    "Min Temp": 0.25,
    "30% Wind": 0.50,
    "50% Wind": 0.50,
}


def build_cases(zone: str, ctemp: float) -> list[LoadCase]:
    zone = zone.strip()
    if zone == "Light":
        raw = [
            ("High Wind", 45, 0, 0), ("Wind + Ice", 22, 6, -5),
            ("Wind Bare", 22, 0, -5), ("NESC", 26.5, 0, -1),
            ("EDS", 0, 0, 25), ("Min Temp", 0, 0, -5),
            ("Max Temp", 0, 0, ctemp), ("30% Wind", 24.6, 0, 15),
            ("50% Wind", 31.8, 0, 15),
        ]
    elif zone == "Medium":
        raw = [
            ("High Wind", 40, 0, 15), ("Heavy Ice", 0, 15, -5),
            ("Wind + Ice", 25, 7, -10), ("Wind Bare", 25, 0, -10),
            ("NESC", 17.8, 6.5, -10), ("EDS", 0, 0, 20),
            ("Min Temp", 0, 0, -20), ("Max Temp", 0, 0, ctemp),
            ("30% Wind", 21.91, 0, 15),
        ]
    elif zone == "Heavy":
        raw = [
            ("High Wind", 40, 0, 15), ("Heavy Ice", 0, 20, -5),
            ("Wind + Ice", 20, 15, -20), ("Wind Bare", 20, 0, -20),
            ("NESC", 17.8, 12.5, -20), ("EDS", 0, 0, 18),
            ("Min Temp", 0, 0, -25), ("Max Temp", 0, 0, ctemp),
            ("30% Wind", 21.91, 0, 15), ("50% Wind", 28.28, 0, 15),
        ]
    elif zone == "VeryHeavy":
        raw = [
            ("High Wind", 40, 0, 15), ("Heavy Ice", 0, 30, -5),
            ("Wind + Ice", 20, 20, -20), ("Wind Bare", 20, 0, -20),
            ("EDS", 0, 0, 15), ("Min Temp", 0, 0, -30),
            ("Max Temp", 0, 0, ctemp), ("30% Wind", 21.91, 0, 15),
            ("50% Wind", 28.28, 0, 15),
        ]
    else:
        raise ValueError("weather_zone must be Light, Medium, Heavy, or VeryHeavy")

    return [LoadCase(name, wind, ice, temp, LIMITS[name]) for name, wind, ice, temp in raw]


def calculate_unit_weight(case: LoadCase, cwei: float, cd_mm: float, rho: float) -> float:
    ice_weight = pi * case.ice * (cd_mm + case.ice) * rho * 1e-6 if case.ice else 0.0
    vertical = cwei + ice_weight
    wind_load = ((case.wind ** 2) / 16.0) * (cd_mm + 2.0 * case.ice) * 1e-3 if case.wind else 0.0
    return sqrt(vertical ** 2 + wind_load ** 2)


def positive_cubic_root(a: float, b: float, c: float) -> float:
    # x^3 + (a+b)x^2 - c = 0, equivalent to MATLAB vpasolve(...,[0 inf]).
    roots = np.roots([1.0, a + b, 0.0, -c])
    candidates = [float(r.real) for r in roots if abs(r.imag) < 1e-7 and r.real > 0]
    if not candidates:
        raise ArithmeticError("No positive real tension root was found.")
    return min(candidates)


def state_change_tension(
    *, area: float, modulus: float, span: float, alpha: float,
    old_tension: float, old_weight: float, old_temp: float,
    new_weight: float, new_temp: float,
) -> float:
    a = area * modulus * span**2 * old_weight**2 / (24.0 * old_tension**2)
    b = area * modulus * alpha * (new_temp - old_temp) - old_tension
    c = area * modulus * span**2 * new_weight**2 / 24.0
    return positive_cubic_root(a, b, c)


def analyze(inputs: dict) -> dict:
    p = DEFAULTS.copy()
    for key in DEFAULTS:
        if key in inputs:
            p[key] = float(inputs[key])

    zone = inputs.get("weather_zone", "Heavy")
    cases = build_cases(zone, p["CTemp"])
    for case in cases:
        case.unit_weight = calculate_unit_weight(case, p["Cwei"], p["Cd"], p["rho"])

    uts = p["UTS"]
    cten = uts * p["initial_tension_ratio"]
    old_weight = p["Cwei"]
    old_temp = p["ATemp"]
    governing = "Initial"

    # Follow the MATLAB sequence: MinTemp first, then environmental cases.
    order_names = ["Min Temp", "High Wind", "Heavy Ice", "Wind + Ice", "Wind Bare", "NESC", "Max Temp", "EDS", "30% Wind", "50% Wind"]
    by_name = {c.name: c for c in cases}

    for name in order_names:
        case = by_name.get(name)
        if not case:
            continue
        new_tension = state_change_tension(
            area=p["CA"], modulus=p["E"], span=p["Span"], alpha=p["alpha"],
            old_tension=cten, old_weight=old_weight, old_temp=old_temp,
            new_weight=case.unit_weight, new_temp=case.temp,
        )
        limit = case.limit_ratio * uts
        if new_tension / uts > case.limit_ratio:
            cten = limit
            governing = name
        old_weight = case.unit_weight
        old_temp = case.temp

    # Re-base all final load-case tensions on the governing state.
    if governing == "Initial":
        base_weight, base_temp = p["Cwei"], p["ATemp"]
    else:
        g = by_name[governing]
        base_weight, base_temp = g.unit_weight, g.temp

    results = []
    for case in cases:
        if case.name == governing:
            tension = case.limit_ratio * uts
        else:
            tension = state_change_tension(
                area=p["CA"], modulus=p["E"], span=p["Span"], alpha=p["alpha"],
                old_tension=cten, old_weight=base_weight, old_temp=base_temp,
                new_weight=case.unit_weight, new_temp=case.temp,
            )

        sag = case.unit_weight * p["Span"]**2 / (8.0 * tension)
        tension_pct = 100.0 * tension / uts
        row = asdict(case)
        row.update({
            "tension": tension,
            "tension_pct": tension_pct,
            "sag": sag,
            "is_governing": case.name == governing,
        })
        results.append(row)

    # Display the case with the largest sag in the span graphic by default.
    display = max(results, key=lambda r: r["sag"])
    L = p["Span"]
    H = display["tension"]
    w = display["unit_weight"]
    xs = np.linspace(0.0, L, 121)
    # Equal-elevation supports, parabolic conductor approximation.
    sags = w * xs * (L - xs) / (2.0 * H)
    attachment = p["tower_height"]
    ys = attachment - sags

    return {
        "parameters": p,
        "weather_zone": zone,
        "governing_state": governing,
        "governing_tension": cten,
        "display_case": display,
        "curve": {"x": xs.tolist(), "y": ys.tolist()},
        "results": results,
    }
