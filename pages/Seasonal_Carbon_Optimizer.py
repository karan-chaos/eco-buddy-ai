"""
Seasonal Carbon Optimizer Page
==============================
Analyze seasonal patterns in your carbon footprint and get
season-specific recommendations for reducing emissions.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

from src.utils.seasonal_optimizer import (
    generate_seasonal_plan, get_season, get_season_data,
    get_seasonal_recommendations, SEASONS, MONTHLY_FACTORS,
)

MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render_monthly_projection_chart(projections: list[dict]) -> None:
    """Stacked bar chart of monthly emission projections by category."""
    months = [MONTH_NAMES[p["month"]] for p in projections]
    categories = list(projections[0]["category_breakdown"].keys())
    colors = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6"]

    fig = go.Figure()
    for i, cat in enumerate(categories):
        vals = [p["category_breakdown"][cat] for p in projections]
        fig.add_trace(go.Bar(name=cat, x=months, y=vals, marker_color=colors[i]))

    fig.update_layout(barmode="stack", height=350, margin=dict(t=30, b=30),
                      yaxis_title="kg CO₂", legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, use_container_width=True)


def render_season_ring_chart(projections: list[dict]) -> None:
    """Donut chart showing total emissions by season."""
    season_totals = {}
    for p in projections:
        s = get_season(p["month"])
        season_totals[s] = season_totals.get(s, 0) + p["estimated_monthly_kg"]

    labels = list(season_totals.keys())
    values = [round(v, 1) for v in season_totals.values()]
    colors = [SEASONS[s]["color"] for s in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.45,
        marker_colors=colors,
        textinfo="label+percent",
        textfont=dict(size=13),
    ))
    fig.update_layout(height=300, margin=dict(t=20, b=20),
                      annotations=[dict(text=f"{sum(values):,.0f}<br>kg/year",
                                         x=0.5, y=0.5, font_size=16, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True)


def render_degree_day_chart(dd_data: dict) -> None:
    """Bar chart showing heating vs cooling degree days."""
    labels = ["Heating", "Cooling"]
    values = [dd_data["heating_degree_days"], dd_data["cooling_degree_days"]]
    colors = ["#3b82f6", "#ef4444"]

    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors,
                           text=[f"{v:.0f}" for v in values], textposition="auto"))
    fig.update_layout(height=220, margin=dict(t=20, b=20), yaxis_title="Degree Days")
    st.plotly_chart(fig, use_container_width=True)


def render_tip_cards(tips: list[dict]) -> None:
    """Render recommendation tip cards grouped by category."""
    impact_colors = {"high": "#22c55e", "medium": "#f59e0b", "low": "#6b7280"}
    impact_icons = {"high": "🟢", "medium": "🟡", "low": "⚪"}

    for tip in tips:
        st.markdown(
            f"<div style='padding:12px 16px; margin:8px 0; border-radius:10px; "
            f"border-left:4px solid {impact_colors.get(tip['impact'], '#6b7280')}; "
            f"background:rgba(255,255,255,0.05);'>"
            f"<strong>{impact_icons.get(tip['impact'], '⚪')} [{tip['category']}]</strong> "
            f"{tip['tip']}<br>"
            f"<small style='color:#9ca3af;'>Potential: −{tip['savings_kg_month']:.0f} kg CO₂/month</small>"
            f"</div>",
            unsafe_allow_html=True,
        )


def render_savings_gauge(potential: dict) -> None:
    """Gauge showing savings potential as percentage of current footprint."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=potential["savings_percent"],
        number={"suffix": "%", "font": {"size": 36}},
        title={"text": "Savings Potential", "font": {"size": 16}},
        gauge={"axis": {"range": [0, 50]}, "bar": {"color": "#22c55e"},
               "steps": [{"range": [0, 15], "color": "#dcfce7"},
                         {"range": [15, 30], "color": "#bbf7d0"},
                         {"range": [30, 50], "color": "#86efac"}]},
    ))
    fig.update_layout(height=250, margin=dict(t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def render_seasonal_optimizer():
    """Main page render function."""
    st.markdown(
        "<div class='section-header'>🌦️ Seasonal Carbon Optimizer</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Understand how your carbon footprint changes across seasons "
        "and get tailored tips for each time of year."
    )

    # ── Input Section ───────────────────────────────────────────────────
    st.subheader("🔧 Your Footprint Data")

    c1, c2 = st.columns(2)
    with c1:
        annual_footprint = st.number_input(
            "Annual Carbon Footprint (kg CO₂)", min_value=0.0,
            max_value=100000.0, value=5000.0, step=100.0,
        )
        target_month = st.selectbox(
            "Analyze Month", list(range(1, 13)), index=datetime.now().month - 1,
            format_func=lambda m: f"{MONTH_NAMES[m]} — {get_season(m)}",
        )
    with c2:
        cat_t = st.number_input("Transport (kg/yr)", min_value=0.0, value=1800.0, step=50.0)
        cat_e = st.number_input("Electricity (kg/yr)", min_value=0.0, value=1400.0, step=50.0)
        cat_d = st.number_input("Diet (kg/yr)", min_value=0.0, value=950.0, step=50.0)
        cat_f = st.number_input("Flights (kg/yr)", min_value=0.0, value=550.0, step=50.0)

    contributors = {"Transport": cat_t, "Electricity": cat_e, "Diet": cat_d, "Flights": cat_f}
    latitude_band = st.selectbox("Climate Zone", ["temperate", "continental", "tropical"], index=0)

    if st.button("🌦️ Analyze Seasonal Patterns", use_container_width=True):
        plan = generate_seasonal_plan(annual_footprint, contributors, latitude_band, target_month)

        # ── Season Overview ─────────────────────────────────────────
        st.divider()
        season = plan["current_season"]
        sd = SEASONS[season]
        st.markdown(
            f"### {sd['icon']} {season} Mode (Month {plan['current_month']})"
        )
        st.markdown(plan["season_description"])

        # ── Key Metrics ─────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Est. This Month", f"{plan['monthly_projections'][plan['current_month']-1]['estimated_monthly_kg']:,.0f} kg")
        m2.metric("Annual Projected", f"{plan['annual_projected_kg']:,.0f} kg")
        peak = plan["peak_month"]
        low = plan["low_month"]
        m3.metric("Peak Month", f"{MONTH_NAMES[peak['month']]} ({peak['kg']:,.0f} kg)")
        m4.metric("Low Month", f"{MONTH_NAMES[low['month']]} ({low['kg']:,.0f} kg)")

        # ── Monthly Projections ─────────────────────────────────────
        st.divider()
        st.subheader("📊 Monthly Emission Projections")
        render_monthly_projection_chart(plan["monthly_projections"])

        # ── Seasonal Distribution ───────────────────────────────────
        sc1, sc2 = st.columns(2)
        with sc1:
            st.subheader("🗓️ Seasonal Distribution")
            render_season_ring_chart(plan["monthly_projections"])
        with sc2:
            st.subheader("🌡️ Climate Data")
            render_degree_day_chart(plan["degree_days"])
            st.caption(
                f"Based on **{plan['latitude_band']}** climate zone. "
                f"Dominant need: **{plan['degree_days']['dominant_need']}**."
            )

        # ── Savings Potential ───────────────────────────────────────
        st.divider()
        st.subheader("💰 Seasonal Savings Potential")
        sp = plan["savings_potential"]
        sg1, sg2 = st.columns([1, 2])
        with sg1:
            render_savings_gauge(sp)
        with sg2:
            st.metric("Monthly Savings Potential", f"{sp['monthly_potential_kg']:,.0f} kg")
            st.metric("Annualized Savings", f"{sp['annual_potential_kg']:,.0f} kg")
            st.metric("Tips Available", str(sp["num_tips"]))
            st.caption(
                f"Implementing all {sp['num_tips']} seasonal tips could reduce your "
                f"annual footprint by **{sp['savings_percent']:.1f}%**."
            )

        # ── Seasonal Recommendations ────────────────────────────────
        st.divider()
        st.subheader(f"💡 {sd['icon']} {season} Recommendations")

        filter_impact = st.radio(
            "Filter by impact", ["all", "high", "medium", "low"],
            horizontal=True, key="impact_filter",
        )
        tips = plan["recommendations"]
        if filter_impact != "all":
            tips = [t for t in tips if t["impact"] == filter_impact]

        if tips:
            render_tip_cards(tips)
        else:
            st.info("No tips match the selected filter.")

        # ── Season Comparison Table ─────────────────────────────────
        st.divider()
        st.subheader("📋 Season Comparison")

        season_summary = {}
        for p in plan["monthly_projections"]:
            s = get_season(p["month"])
            if s not in season_summary:
                season_summary[s] = {"total_kg": 0, "count": 0}
            season_summary[s]["total_kg"] += p["estimated_monthly_kg"]
            season_summary[s]["count"] += 1

        st.markdown("| Season | Icon | Total (kg) | Avg/Month (kg) | Multiplier |")
        st.markdown("|--------|------|-----------|----------------|------------|")
        for s_name in ["Winter", "Spring", "Summer", "Autumn"]:
            if s_name in season_summary:
                ss = season_summary[s_name]
                avg = ss["total_kg"] / ss["count"] if ss["count"] else 0
                mult = SEASONS[s_name]["energy_multiplier"]
                icon = SEASONS[s_name]["icon"]
                highlight = "**" if s_name == season else ""
                st.markdown(
                    f"| {highlight}{s_name}{highlight} | {icon} | "
                    f"{ss['total_kg']:,.0f} | {avg:,.0f} | {mult:.2f}x |"
                )

        # ── Action Plan ─────────────────────────────────────────────
        st.divider()
        st.subheader("🚀 Seasonal Action Plan")
        high_tips = [t for t in plan["recommendations"] if t["impact"] == "high"]
        for i, tip in enumerate(high_tips, 1):
            st.markdown(f"**{i}.** {tip['tip']} (−{tip['savings_kg_month']:.0f} kg/month)")

        if not high_tips:
            st.info("All seasonal tips are moderate or low impact — still worth doing!")

        st.markdown(
            f"\n**Next season ({get_season((plan['current_month'] % 12) + 1)}):** "
            f"{SEASONS[get_season((plan['current_month'] % 12) + 1)]['description']}"
        )
    else:
        st.info("👆 Enter your footprint data and click **Analyze Seasonal Patterns** to begin.")


if __name__ == "__main__":
    st.set_page_config(page_title="Seasonal Carbon Optimizer — EcoBuddy AI", page_icon="🌦️", layout="wide")
    render_seasonal_optimizer()
else:
    render_seasonal_optimizer()
