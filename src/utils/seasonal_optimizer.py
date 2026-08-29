"""
Seasonal Carbon Footprint Optimizer
====================================
Analyzes seasonal patterns in carbon emissions, projects monthly footprints,
and provides season-specific sustainability recommendations.

Features:
- Season detection and categorization by month
- Monthly emission projections based on season-adjusted factors
- Season-specific energy, transport, and diet recommendations
- Heating/cooling degree-day estimation for energy planning
- Seasonal budget tracking against annual targets
"""

import math
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ── Season Definitions ───────────────────────────────────────────────────────

SEASONS: dict[str, dict[str, Any]] = {
    "Winter": {
        "months": [12, 1, 2],
        "icon": "❄️",
        "color": "#3b82f6",
        "description": "Cold weather increases heating demand and indoor energy use.",
        "energy_multiplier": 1.35,
        "transport_multiplier": 1.10,
        "diet_multiplier": 1.05,
    },
    "Spring": {
        "months": [3, 4, 5],
        "icon": "🌸",
        "color": "#22c55e",
        "description": "Mild temperatures reduce heating/cooling needs.",
        "energy_multiplier": 0.90,
        "transport_multiplier": 0.95,
        "diet_multiplier": 0.98,
    },
    "Summer": {
        "months": [6, 7, 8],
        "icon": "☀️",
        "color": "#f59e0b",
        "description": "Cooling demand rises; outdoor activities increase transport variability.",
        "energy_multiplier": 1.20,
        "transport_multiplier": 1.15,
        "diet_multiplier": 1.02,
    },
    "Autumn": {
        "months": [9, 10, 11],
        "icon": "🍂",
        "color": "#f97316",
        "description": "Transitional season with moderate energy and travel patterns.",
        "energy_multiplier": 0.85,
        "transport_multiplier": 0.90,
        "diet_multiplier": 0.97,
    },
}

# ── Seasonal Recommendations ─────────────────────────────────────────────────

SEASONAL_TIPS: dict[str, list[dict[str, str]]] = {
    "Winter": [
        {"category": "Energy", "tip": "Lower your thermostat by 2°C to save up to 10% on heating energy.",
         "impact": "high", "savings_kg_month": 85.0},
        {"category": "Energy", "tip": "Use draft stoppers on doors and windows to reduce heat loss.",
         "impact": "medium", "savings_kg_month": 30.0},
        {"category": "Transport", "tip": "Bundle errands into single trips to reduce cold-weather driving.",
         "impact": "medium", "savings_kg_month": 25.0},
        {"category": "Diet", "tip": "Eat seasonal root vegetables — lower food-miles and higher nutrition.",
         "impact": "low", "savings_kg_month": 12.0},
        {"category": "Energy", "tip": "Switch to LED holiday lighting to cut seasonal lighting emissions by 80%.",
         "impact": "low", "savings_kg_month": 8.0},
    ],
    "Spring": [
        {"category": "Energy", "tip": "Open windows for natural ventilation instead of running AC.",
         "impact": "high", "savings_kg_month": 60.0},
        {"category": "Transport", "tip": "Switch to biking or walking for short commutes as weather improves.",
         "impact": "high", "savings_kg_month": 95.0},
        {"category": "Diet", "tip": "Start a small garden — growing your own herbs cuts food emissions.",
         "impact": "medium", "savings_kg_month": 18.0},
        {"category": "Energy", "tip": "Service your HVAC system before summer to maximize efficiency.",
         "impact": "medium", "savings_kg_month": 22.0},
        {"category": "Diet", "tip": "Choose locally-grown spring produce at farmers' markets.",
         "impact": "low", "savings_kg_month": 10.0},
    ],
    "Summer": [
        {"category": "Energy", "tip": "Use fans before AC — they use 90% less energy.",
         "impact": "high", "savings_kg_month": 75.0},
        {"category": "Energy", "tip": "Close blinds during peak sun hours to reduce cooling load.",
         "impact": "medium", "savings_kg_month": 40.0},
        {"category": "Transport", "tip": "Plan road trips during off-peak hours to avoid traffic-related idling.",
         "impact": "medium", "savings_kg_month": 30.0},
        {"category": "Diet", "tip": "Eat more cold meals (salads, fruits) — no cooking energy required.",
         "impact": "low", "savings_kg_month": 15.0},
        {"category": "Transport", "tip": "Use public transit for summer events instead of driving.",
         "impact": "medium", "savings_kg_month": 35.0},
    ],
    "Autumn": [
        {"category": "Energy", "tip": "Reverse ceiling fans to push warm air down as temperatures drop.",
         "impact": "medium", "savings_kg_month": 20.0},
        {"category": "Energy", "tip": "Weatherstrip doors and windows before winter arrives.",
         "impact": "high", "savings_kg_month": 55.0},
        {"category": "Transport", "tip": "Carpool to fall events and harvest festivals.",
         "impact": "medium", "savings_kg_month": 28.0},
        {"category": "Diet", "tip": "Buy seasonal squash and apples — lower carbon than imported produce.",
         "impact": "low", "savings_kg_month": 12.0},
        {"category": "Energy", "tip": "Program your thermostat for autumn's fluctuating temperatures.",
         "impact": "medium", "savings_kg_month": 35.0},
    ],
}

# ── Monthly Emission Factors (relative to annual average = 1.0) ──────────────

MONTHLY_FACTORS: dict[int, dict[str, float]] = {
    1:  {"energy": 1.40, "transport": 1.05, "diet": 1.08},   # January
    2:  {"energy": 1.30, "transport": 1.02, "diet": 1.05},   # February
    3:  {"energy": 1.05, "transport": 0.95, "diet": 1.00},   # March
    4:  {"energy": 0.85, "transport": 0.90, "diet": 0.98},   # April
    5:  {"energy": 0.80, "transport": 0.92, "diet": 0.96},   # May
    6:  {"energy": 1.10, "transport": 1.12, "diet": 1.00},   # June
    7:  {"energy": 1.25, "transport": 1.18, "diet": 1.03},   # July
    8:  {"energy": 1.22, "transport": 1.15, "diet": 1.02},   # August
    9:  {"energy": 0.88, "transport": 0.92, "diet": 0.97},   # September
    10: {"energy": 0.82, "transport": 0.88, "diet": 0.96},   # October
    11: {"energy": 1.00, "transport": 0.95, "diet": 1.02},   # November
    12: {"energy": 1.35, "transport": 1.08, "diet": 1.06},   # December
}


# ── Core Functions ───────────────────────────────────────────────────────────

def get_season(month: int) -> str:
    """Return the season name for a given month number."""
    for name, data in SEASONS.items():
        if month in data["months"]:
            return name
    return "Spring"  # fallback


def get_season_data(season: str) -> dict[str, Any]:
    """Get full data dict for a named season."""
    return SEASONS.get(season, SEASONS["Spring"])


def get_month_factors(month: int) -> dict[str, float]:
    """Return per-category emission multipliers for a given month."""
    return MONTHLY_FACTORS.get(month, {"energy": 1.0, "transport": 1.0, "diet": 1.0})


def estimate_seasonal_footprint(
    annual_footprint: float,
    contributors: dict[str, float],
    month: int | None = None,
) -> dict[str, Any]:
    """
    Estimate the seasonal breakdown of a user's carbon footprint.

    If month is provided, estimates that specific month's emissions.
    Otherwise returns a full 12-month projection.
    """
    if month is not None:
        factors = get_month_factors(month)
        season = get_season(month)
        season_data = get_season_data(season)

        energy_annual = contributors.get("Electricity", annual_footprint * 0.30)
        transport_annual = contributors.get("Transport", annual_footprint * 0.35)
        diet_annual = contributors.get("Diet", annual_footprint * 0.20)
        flights_annual = contributors.get("Flights", annual_footprint * 0.15)

        # Monthly estimates (annual / 12 * monthly factor)
        energy_monthly = (energy_annual / 12) * factors["energy"]
        transport_monthly = (transport_annual / 12) * factors["transport"]
        diet_monthly = (diet_annual / 12) * factors["diet"]
        flights_monthly = flights_annual / 12  # Flights don't vary seasonally in this model

        total_monthly = energy_monthly + transport_monthly + diet_monthly + flights_monthly

        return {
            "month": month,
            "season": season,
            "season_icon": season_data["icon"],
            "season_color": season_data["color"],
            "estimated_monthly_kg": round(total_monthly, 2),
            "category_breakdown": {
                "Energy": round(energy_monthly, 2),
                "Transport": round(transport_monthly, 2),
                "Diet": round(diet_monthly, 2),
                "Flights": round(flights_monthly, 2),
            },
            "factors": factors,
        }

    # Full 12-month projection
    projections = []
    for m in range(1, 13):
        proj = estimate_seasonal_footprint(annual_footprint, contributors, month=m)
        projections.append(proj)

    return {"projections": projections, "annual_total_kg": round(sum(p["estimated_monthly_kg"] for p in projections), 2)}


def estimate_heating_cooling_degree_days(
    month: int,
    latitude_band: str = "temperate",
) -> dict[str, float]:
    """
    Estimate heating and cooling degree days for a given month.
    Based on simplified climate zone models.
    """
    # Base temperatures by latitude band (°C)
    base_temps = {
        "tropical": {"heating_base": 18.0, "cooling_base": 24.0,
                     "avg_temps": {1: 27, 2: 28, 3: 29, 4: 30, 5: 29, 6: 28,
                                   7: 27, 8: 27, 9: 27, 10: 28, 11: 28, 12: 27}},
        "temperate": {"heating_base": 18.0, "cooling_base": 24.0,
                      "avg_temps": {1: 2, 2: 3, 3: 7, 4: 11, 5: 15, 6: 19,
                                    7: 21, 8: 20, 9: 17, 10: 12, 11: 7, 12: 3}},
        "continental": {"heating_base": 18.0, "cooling_base": 24.0,
                        "avg_temps": {1: -5, 2: -3, 3: 3, 4: 10, 5: 16, 6: 21,
                                      7: 24, 8: 22, 9: 17, 10: 10, 11: 3, 12: -3}},
    }

    zone = base_temps.get(latitude_band, base_temps["temperate"])
    avg_temp = zone["avg_temps"].get(month, 15.0)
    days_in_month = 30.44  # average

    hdd = max(0, (zone["heating_base"] - avg_temp) * days_in_month)
    cdd = max(0, (avg_temp - zone["cooling_base"]) * days_in_month)

    return {
        "month": month,
        "latitude_band": latitude_band,
        "avg_temp_c": avg_temp,
        "heating_degree_days": round(hdd, 1),
        "cooling_degree_days": round(cdd, 1),
        "dominant_need": "heating" if hdd > cdd else ("cooling" if cdd > hdd else "none"),
    }


def get_seasonal_recommendations(season: str, impact_filter: str | None = None) -> list[dict[str, str]]:
    """
    Get season-specific sustainability tips, optionally filtered by impact level.
    """
    tips = SEASONAL_TIPS.get(season, [])
    if impact_filter:
        tips = [t for t in tips if t["impact"] == impact_filter]
    return tips


def calculate_seasonal_savings_potential(
    contributors: dict[str, float],
    season: str,
) -> dict[str, Any]:
    """
    Calculate the total potential savings if the user follows all seasonal tips.
    """
    tips = SEASONAL_TIPS.get(season, [])
    total_potential = sum(t["savings_kg_month"] for t in tips)

    # Annualize (4 seasons * tips_per_season average savings)
    annual_potential = total_potential * 3

    current_annual = sum(contributors.values())
    savings_pct = (annual_potential / current_annual * 100) if current_annual > 0 else 0

    return {
        "season": season,
        "monthly_potential_kg": round(total_potential, 2),
        "annual_potential_kg": round(annual_potential, 2),
        "current_annual_kg": round(current_annual, 2),
        "savings_percent": round(savings_pct, 1),
        "num_tips": len(tips),
    }


def generate_seasonal_plan(
    annual_footprint: float,
    contributors: dict[str, float],
    latitude_band: str = "temperate",
    target_month: int | None = None,
) -> dict[str, Any]:
    """
    Main entry point — generates a comprehensive seasonal optimization plan.
    """
    now = datetime.utcnow()
    current_month = target_month or now.month
    current_season = get_season(current_month)

    # Monthly projections
    projections = estimate_seasonal_footprint(annual_footprint, contributors)

    # Degree-day estimate for current month
    degree_days = estimate_heating_cooling_degree_days(current_month, latitude_band)

    # Seasonal savings potential
    savings = calculate_seasonal_savings_potential(contributors, current_season)

    # Current season tips
    tips = get_seasonal_recommendations(current_season)

    # Peak and low emission months
    monthly_totals = [(p["month"], p["estimated_monthly_kg"]) for p in projections["projections"]]
    peak_month = max(monthly_totals, key=lambda x: x[1])
    low_month = min(monthly_totals, key=lambda x: x[1])

    return {
        "current_month": current_month,
        "current_season": current_season,
        "season_icon": SEASONS[current_season]["icon"],
        "season_description": SEASONS[current_season]["description"],
        "monthly_projections": projections["projections"],
        "annual_projected_kg": projections["annual_total_kg"],
        "degree_days": degree_days,
        "savings_potential": savings,
        "recommendations": tips,
        "peak_month": {"month": peak_month[0], "kg": peak_month[1],
                       "season": get_season(peak_month[0])},
        "low_month": {"month": low_month[0], "kg": low_month[1],
                      "season": get_season(low_month[0])},
        "latitude_band": latitude_band,
        "generated_at": datetime.utcnow().isoformat(),
    }
