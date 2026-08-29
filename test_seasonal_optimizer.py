"""
Tests for the Seasonal Carbon Optimizer Engine
"""

import pytest

from src.utils.seasonal_optimizer import (
    get_season, get_season_data, get_month_factors,
    estimate_seasonal_footprint, estimate_heating_cooling_degree_days,
    get_seasonal_recommendations, calculate_seasonal_savings_potential,
    generate_seasonal_plan, SEASONS, MONTHLY_FACTORS,
)

SAMPLE_CONTRIBUTORS = {"Transport": 1800.0, "Electricity": 1400.0, "Diet": 950.0, "Flights": 550.0}


# ── get_season Tests ─────────────────────────────────────────────────────────

class TestGetSeason:
    def test_winter_months(self):
        for m in [12, 1, 2]:
            assert get_season(m) == "Winter"

    def test_spring_months(self):
        for m in [3, 4, 5]:
            assert get_season(m) == "Spring"

    def test_summer_months(self):
        for m in [6, 7, 8]:
            assert get_season(m) == "Summer"

    def test_autumn_months(self):
        for m in [9, 10, 11]:
            assert get_season(m) == "Autumn"

    def test_all_months_covered(self):
        for m in range(1, 13):
            assert get_season(m) in SEASONS


class TestGetSeasonData:
    def test_returns_full_dict(self):
        data = get_season_data("Winter")
        assert {"months", "icon", "color", "energy_multiplier"}.issubset(data.keys())

    def test_unknown_season_fallback(self):
        data = get_season_data("Monsoon")
        assert data == SEASONS["Spring"]


# ── get_month_factors Tests ──────────────────────────────────────────────────

class TestGetMonthFactors:
    def test_all_months_present(self):
        for m in range(1, 13):
            factors = get_month_factors(m)
            assert {"energy", "transport", "diet"}.issubset(factors.keys())

    def test_winter_higher_energy(self):
        winter = get_month_factors(1)["energy"]
        spring = get_month_factors(4)["energy"]
        assert winter > spring

    def test_factors_positive(self):
        for m in range(1, 13):
            for val in get_month_factors(m).values():
                assert val > 0


# ── estimate_seasonal_footprint Tests ────────────────────────────────────────

class TestEstimateSeasonalFootprint:
    def test_single_month(self):
        result = estimate_seasonal_footprint(5000.0, SAMPLE_CONTRIBUTORS, month=1)
        assert result["month"] == 1
        assert result["season"] == "Winter"
        assert result["estimated_monthly_kg"] > 0

    def test_full_projection(self):
        result = estimate_seasonal_footprint(5000.0, SAMPLE_CONTRIBUTORS)
        assert "projections" in result
        assert len(result["projections"]) == 12

    def test_annual_total_positive(self):
        result = estimate_seasonal_footprint(5000.0, SAMPLE_CONTRIBUTORS)
        assert result["annual_total_kg"] > 0

    def test_winter_higher_than_spring(self):
        winter = estimate_seasonal_footprint(5000.0, SAMPLE_CONTRIBUTORS, month=1)
        spring = estimate_seasonal_footprint(5000.0, SAMPLE_CONTRIBUTORS, month=4)
        assert winter["estimated_monthly_kg"] > spring["estimated_monthly_kg"]

    def test_category_breakdown_keys(self):
        result = estimate_seasonal_footprint(5000.0, SAMPLE_CONTRIBUTORS, month=7)
        assert {"Energy", "Transport", "Diet", "Flights"}.issubset(result["category_breakdown"].keys())

    def test_all_months_positive(self):
        result = estimate_seasonal_footprint(5000.0, SAMPLE_CONTRIBUTORS)
        for p in result["projections"]:
            assert p["estimated_monthly_kg"] > 0

    def test_zero_footprint(self):
        result = estimate_seasonal_footprint(0.0, {"Transport": 0, "Electricity": 0, "Diet": 0, "Flights": 0}, month=6)
        assert result["estimated_monthly_kg"] == 0.0


# ── estimate_heating_cooling_degree_days Tests ───────────────────────────────

class TestEstimateHeatingDegreeDays:
    def test_winter_heating_dominant(self):
        result = estimate_heating_cooling_degree_days(1, "temperate")
        assert result["dominant_need"] == "heating"
        assert result["heating_degree_days"] > 0

    def test_summer_cooling_or_mild(self):
        result = estimate_heating_cooling_degree_days(7, "continental")
        assert result["cooling_degree_days"] > 0

    def test_tropical_little_heating(self):
        result = estimate_heating_cooling_degree_days(1, "tropical")
        assert result["heating_degree_days"] < 50

    def test_all_months(self):
        for m in range(1, 13):
            result = estimate_heating_cooling_degree_days(m, "temperate")
            assert result["month"] == m
            assert result["heating_degree_days"] >= 0
            assert result["cooling_degree_days"] >= 0

    def test_unknown_band_fallback(self):
        result = estimate_heating_cooling_degree_days(1, "arctic")
        assert result["latitude_band"] == "temperate"  # fallback


# ── get_seasonal_recommendations Tests ───────────────────────────────────────

class TestGetSeasonalRecommendations:
    def test_returns_tips(self):
        tips = get_seasonal_recommendations("Winter")
        assert len(tips) > 0
        assert all("tip" in t for t in tips)

    def test_filter_by_impact(self):
        high = get_seasonal_recommendations("Summer", impact_filter="high")
        assert all(t["impact"] == "high" for t in high)

    def test_unknown_season_empty(self):
        tips = get_seasonal_recommendations("Monsoon")
        assert tips == []

    def test_each_season_has_tips(self):
        for season in SEASONS:
            tips = get_seasonal_recommendations(season)
            assert len(tips) >= 3, f"{season} should have at least 3 tips"


# ── calculate_seasonal_savings_potential Tests ───────────────────────────────

class TestCalculateSeasonalSavingsPotential:
    def test_returns_positive(self):
        result = calculate_seasonal_savings_potential(SAMPLE_CONTRIBUTORS, "Winter")
        assert result["monthly_potential_kg"] > 0
        assert result["annual_potential_kg"] > 0

    def test_savings_percent(self):
        result = calculate_seasonal_savings_potential(SAMPLE_CONTRIBUTORS, "Spring")
        assert result["savings_percent"] > 0

    def test_num_tips(self):
        result = calculate_seasonal_savings_potential(SAMPLE_CONTRIBUTORS, "Summer")
        assert result["num_tips"] > 0


# ── generate_seasonal_plan Tests ─────────────────────────────────────────────

class TestGenerateSeasonalPlan:
    def test_all_keys_present(self):
        plan = generate_seasonal_plan(5000.0, SAMPLE_CONTRIBUTORS, target_month=1)
        expected = {"current_month", "current_season", "monthly_projections",
                    "annual_projected_kg", "degree_days", "savings_potential",
                    "recommendations", "peak_month", "low_month", "generated_at"}
        assert expected.issubset(plan.keys())

    def test_projections_count(self):
        plan = generate_seasonal_plan(5000.0, SAMPLE_CONTRIBUTORS)
        assert len(plan["monthly_projections"]) == 12

    def test_peak_and_low_months_valid(self):
        plan = generate_seasonal_plan(5000.0, SAMPLE_CONTRIBUTORS)
        assert 1 <= plan["peak_month"]["month"] <= 12
        assert 1 <= plan["low_month"]["month"] <= 12

    def test_with_custom_month(self):
        plan = generate_seasonal_plan(5000.0, SAMPLE_CONTRIBUTORS, target_month=7)
        assert plan["current_season"] == "Summer"

    def test_recommendations_non_empty(self):
        plan = generate_seasonal_plan(5000.0, SAMPLE_CONTRIBUTORS, target_month=1)
        assert len(plan["recommendations"]) > 0


# ── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_zero_footprint_plan(self):
        plan = generate_seasonal_plan(0.0, {"Transport": 0, "Electricity": 0, "Diet": 0, "Flights": 0})
        assert plan["annual_projected_kg"] == 0.0

    def test_very_large_footprint(self):
        plan = generate_seasonal_plan(50000.0, SAMPLE_CONTRIBUTORS)
        assert plan["annual_projected_kg"] > 0

    def test_monthly_factors_sum(self):
        """Verify monthly factors average roughly to 1.0."""
        for cat in ["energy", "transport", "diet"]:
            avg = sum(MONTHLY_FACTORS[m][cat] for m in range(1, 13)) / 12
            assert 0.8 < avg < 1.3, f"{cat} average factor out of range"

    def test_season_multipliers(self):
        for season, data in SEASONS.items():
            assert data["energy_multiplier"] > 0
            assert data["transport_multiplier"] > 0
