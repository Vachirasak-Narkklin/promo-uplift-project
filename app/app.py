"""Promo profit simulator.

    streamlit run app/app.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

DATA = Path(__file__).resolve().parent / "data"
GREEN, BLUE, RED, GREY = "#2e7d32", "#1f77b4", "#c62828", "#9e9e9e"

st.set_page_config(page_title="Promo Profit Simulator", layout="wide")


@st.cache_data
def load():
    return (pd.read_parquet(DATA / "curves.parquet"),
            pd.read_parquet(DATA / "current.parquet"),
            pd.read_parquet(DATA / "baseline.parquet"),
            pd.read_parquet(DATA / "uplift.parquet"))


if not (DATA / "curves.parquet").exists():
    st.error("No data found. Run the notebooks, then `python app/prepare_data.py`.")
    st.stop()

curves, current, baseline, uplift = load()


def gross_profit(gross, margin, discount_pct, margin_shift, vendor_share):
    """Profit = list-price value × (margin − share of the discount the store pays)."""
    return gross * (margin + margin_shift - (1 - vendor_share) * discount_pct / 100)


def current_profit(row, margin, margin_shift, vendor_share):
    return (margin + margin_shift) * row["gross"] - (1 - vendor_share) * row["retail_disc"]


def direction(change_pts):
    if change_pts <= -2.5:
        return "discount less"
    if change_pts >= 2.5:
        return "discount more"
    return "about right"


def fmt_money(x):
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"


# ---------------------------------------------------------------- sidebar
st.sidebar.header("Assumptions")
vendor_share = st.sidebar.slider(
    "Supplier-funded share of the discount (%)", 0, 90, 0, step=10,
    help="If a supplier pays half of a 20% discount, the store only gives up 10%.") / 100
margin_shift = st.sidebar.slider(
    "Adjust all margins (points)", -10, 10, 0, step=1,
    help="Margins are assumed by department (25–45%). Shift them to test the sensitivity.") / 100
st.sidebar.caption(
    "Product costs and supplier funding aren't in the data, so both are assumptions. "
    "Profit is gross profit over the 12 most recent weeks (weeks 90–101).")
st.sidebar.markdown("[Full analysis on GitHub](https://github.com/Vachirasak-Narkklin/promo-uplift-project)")

st.title("Promo Profit Simulator")
st.caption("What happens to units, revenue and gross profit if a category's average discount changes? "
           "Built on two years of Dunnhumby grocery data.")

tab_sim, tab_all, tab_base, tab_camp = st.tabs(
    ["Simulator", "All categories", "Baseline vs. promo", "Coupon campaigns"])

# ---------------------------------------------------------------- simulator
with tab_sim:
    items = current.sort_values("revenue", ascending=False)["item"].tolist()
    default = items.index("SOFT DRINKS") if "SOFT DRINKS" in items else 0
    item = st.selectbox("Category", items, index=default)

    c = curves.loc[curves["item"] == item].sort_values("discount_pct").copy()
    cur = current.loc[current["item"] == item].iloc[0]
    margin = c["margin"].iloc[0]
    p05, p95 = c["disc_p05"].iloc[0], c["disc_p95"].iloc[0]

    c["gp"] = gross_profit(c["gross"], margin, c["discount_pct"], margin_shift, vendor_share)
    inside = c.loc[c["discount_pct"].between(p05, p95)]
    best = inside.loc[inside["gp"].idxmax()] if len(inside) else c.loc[c["gp"].idxmax()]
    cur_gp = current_profit(cur, margin, margin_shift, vendor_share)

    grid_values = c["discount_pct"].tolist()
    start = min(grid_values, key=lambda v: abs(v - cur["current_discount"]))
    chosen = st.select_slider("Discount to simulate (%)", options=grid_values, value=start,
                              format_func=lambda v: f"{v:g}%")
    sel = c.loc[c["discount_pct"] == chosen].iloc[0]

    if cur["confidence"] not in (None, "normal") and isinstance(cur["confidence"], str):
        st.warning(f"Low confidence for this category: {cur['confidence']}.")
    if not (p05 <= chosen <= p95):
        st.info(f"{chosen:g}% is outside the range this category has actually been sold at "
                f"({p05:.0f}–{p95:.0f}%), so the model is extrapolating.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Today's avg discount", f"{cur['current_discount']:.1f}%")
    k2.metric("Units (12 wks)", f"{sel['units']:,.0f}", f"{sel['units'] / cur['units'] - 1:+.1%} vs today")
    k3.metric("Revenue (12 wks)", fmt_money(sel["revenue"]), f"{sel['revenue'] / cur['revenue'] - 1:+.1%} vs today")
    k4.metric("Gross profit (12 wks)", fmt_money(sel["gp"]), f"{fmt_money(sel['gp'] - cur_gp)} vs today")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_vrect(x0=p05, x1=p95, fillcolor=GREY, opacity=0.12, line_width=0,
                  annotation_text="tested range", annotation_position="top left")
    fig.add_trace(go.Scatter(x=c["discount_pct"], y=c["gp"], name="gross profit",
                             line=dict(color=GREEN, width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=c["discount_pct"], y=c["units"], name="units",
                             line=dict(color=BLUE, dash="dash")), secondary_y=True)
    fig.add_trace(go.Scatter(x=[best["discount_pct"]], y=[best["gp"]], mode="markers", name="best in tested range",
                             marker=dict(color="black", size=12)), secondary_y=False)
    fig.add_vline(x=cur["current_discount"], line=dict(color=RED, dash="dot"),
                  annotation_text="today", annotation_position="bottom right")
    fig.add_vline(x=chosen, line=dict(color="black", width=1))
    fig.add_hline(y=0, line=dict(color="black", width=0.5))
    fig.update_layout(height=430, margin=dict(t=30, b=10), legend=dict(orientation="h", y=-0.15),
                      plot_bgcolor="white")
    fig.update_xaxes(title_text="average discount %", gridcolor="#eee")
    fig.update_yaxes(title_text="gross profit", secondary_y=False, gridcolor="#eee")
    fig.update_yaxes(title_text="units", secondary_y=True, showgrid=False)
    st.plotly_chart(fig, width="stretch")

    change = best["gp"] - cur_gp
    st.markdown(
        f"**Best discount in the tested range: {best['discount_pct']:g}%** "
        f"(today {cur['current_discount']:.1f}%). Gross profit {fmt_money(best['gp'])} vs. "
        f"{fmt_money(cur_gp)} today, a difference of **{fmt_money(change)}** over 12 weeks. "
        f"Assumed margin {margin + margin_shift:.0%}, supplier funding {vendor_share:.0%}.")

# ---------------------------------------------------------------- all categories
with tab_all:
    only_normal = st.checkbox("Only categories with normal confidence", value=True,
                              help="Excludes seasonal items, small categories and ones that are rarely discounted.")

    a = curves.assign(gp=lambda d: gross_profit(d["gross"], d["margin"], d["discount_pct"], margin_shift, vendor_share))
    a = a.loc[a["discount_pct"].between(a["disc_p05"], a["disc_p95"])]
    best_all = a.loc[a.groupby("item")["gp"].idxmax(), ["item", "discount_pct", "gp", "units", "revenue", "margin"]]
    best_all.columns = ["item", "best_discount", "best_profit", "best_units", "best_revenue", "margin"]

    r = current.merge(best_all, on="item")
    r["current_profit"] = (r["margin"] + margin_shift) * r["gross"] - (1 - vendor_share) * r["retail_disc"]
    r["profit_change"] = r["best_profit"] - r["current_profit"]
    r["recommendation"] = (r["best_discount"] - r["current_discount"]).apply(direction)
    if only_normal:
        r = r.loc[r["confidence"] == "normal"]

    counts = r["recommendation"].value_counts()
    total_now, total_best = r["current_profit"].sum(), r["best_profit"].sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Discount less", int(counts.get("discount less", 0)))
    m2.metric("About right", int(counts.get("about right", 0)))
    m3.metric("Discount more", int(counts.get("discount more", 0)))
    m4.metric("Gross profit at best levels", fmt_money(total_best),
              f"{total_best / total_now - 1:+.1%} vs today" if total_now > 0 else None)

    colors = {"discount less": RED, "discount more": BLUE, "about right": GREY}
    fig = go.Figure()
    for rec, d in r.groupby("recommendation"):
        fig.add_trace(go.Scatter(
            x=d["current_discount"], y=d["best_discount"], mode="markers", name=rec,
            marker=dict(color=colors[rec], size=np.sqrt(d["revenue"]) / np.sqrt(r["revenue"].max()) * 40 + 5, opacity=0.6),
            text=d["item"].str.title(),
            hovertemplate="%{text}<br>today %{x:.1f}% → best %{y:.1f}%<extra></extra>"))
    lim = max(r["current_discount"].max(), r["best_discount"].max()) + 3
    fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", line=dict(color="black", dash="dash", width=1),
                             showlegend=False, hoverinfo="skip"))
    fig.update_layout(height=480, xaxis_title="today's average discount %", yaxis_title="profit-maximising discount %",
                      plot_bgcolor="white", margin=dict(t=30), legend=dict(orientation="h", y=-0.15))
    fig.update_xaxes(gridcolor="#eee")
    fig.update_yaxes(gridcolor="#eee")
    st.plotly_chart(fig, width="stretch")
    st.caption("Below the dashed line = discounting deeper than pays off. Bubble size = revenue.")

    st.subheader("Biggest profit opportunities")
    show = r.nlargest(15, "profit_change")[
        ["item", "department", "current_discount", "best_discount", "current_profit", "best_profit", "profit_change"]]
    st.dataframe(
        show.rename(columns={"item": "category", "current_discount": "today %", "best_discount": "best %",
                             "current_profit": "profit today", "best_profit": "profit at best", "profit_change": "difference"}),
        hide_index=True, width="stretch",
        column_config={c: st.column_config.NumberColumn(format="%.1f") for c in ["today %", "best %"]}
        | {c: st.column_config.NumberColumn(format="$%,.0f") for c in ["profit today", "profit at best", "difference"]})

# ---------------------------------------------------------------- baseline
with tab_base:
    b_items = baseline.groupby("item")["units"].sum().sort_values(ascending=False).index.tolist()
    b_default = b_items.index("SOFT DRINKS") if "SOFT DRINKS" in b_items else 0
    b_item = st.selectbox("Category", b_items, index=b_default, key="baseline_item")
    d = baseline.loc[baseline["item"] == b_item].sort_values("week_no")

    share = d["incremental_units"].sum() / d["units"].sum()
    st.metric("Share of volume driven by promotions", f"{share:.1%}")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.05)
    fig.add_trace(go.Scatter(x=d["week_no"], y=d["baseline_units"], name="baseline", line=dict(color=BLUE, width=2)), 1, 1)
    fig.add_trace(go.Scatter(x=d["week_no"], y=d["units"], name="actual", line=dict(color="black", width=1.5),
                             fill="tonexty", fillcolor="rgba(46,125,50,0.25)"), 1, 1)
    fig.add_trace(go.Bar(x=d["week_no"], y=d["avg_discount_pct"], name="avg discount %",
                         marker_color=RED, opacity=0.6), 2, 1)
    fig.update_layout(height=500, plot_bgcolor="white", margin=dict(t=30), legend=dict(orientation="h", y=-0.12))
    fig.update_yaxes(title_text="units / week", row=1, col=1, gridcolor="#eee")
    fig.update_yaxes(title_text="discount %", row=2, col=1, gridcolor="#eee")
    fig.update_xaxes(title_text="week", row=2, col=1)
    st.plotly_chart(fig, width="stretch")
    st.caption("Green area = units the promotion added on top of what would have sold anyway (model estimate).")

# ---------------------------------------------------------------- campaigns
with tab_camp:
    u = uplift.copy()
    u["w"] = np.where(u["treated"] == 1, 1 / u["ps"], 1 / (1 - u["ps"]))

    def weighted_effect(df, col="y_clip"):
        t, c_ = df[df["treated"] == 1], df[df["treated"] == 0]
        if len(t) == 0 or len(c_) == 0:
            return np.nan
        return np.average(t[col], weights=t["w"]) - np.average(c_[col], weights=c_["w"])

    overall = weighted_effect(u, "y")
    st.metric("Campaign effect (weighted difference-in-differences)", f"${overall:,.2f} per household per week")
    st.markdown(
        "Targeted households spent much more than others, but the store had picked heavier shoppers to begin with. "
        "Comparing the *change* in spend and weighting for who got picked gives the effect above.")

    by_group = (u.groupby("uplift_group", observed=True)
                  .apply(weighted_effect, include_groups=False).rename("actual").reset_index())
    pred = u.groupby("uplift_group", observed=True)["uplift_pred"].mean().reset_index(drop=True)
    fig = go.Figure([
        go.Bar(x=by_group["uplift_group"].astype(str), y=pred, name="predicted", marker_color=GREY),
        go.Bar(x=by_group["uplift_group"].astype(str), y=by_group["actual"], name="actual", marker_color=BLUE),
    ])
    fig.update_layout(barmode="group", height=380, plot_bgcolor="white", margin=dict(t=30),
                      xaxis_title="predicted uplift group", yaxis_title="extra spend per week",
                      legend=dict(orientation="h", y=-0.2))
    fig.update_yaxes(gridcolor="#eee")
    st.plotly_chart(fig, width="stretch")
    st.caption("If the model could pick out strong responders, the blue bars would rise from left to right. "
               "They don't, so I don't use it to narrow targeting. Next step: a random holdout in the next campaign.")
