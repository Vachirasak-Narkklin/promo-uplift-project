"""Export the small tables the dashboard needs from data/processed into app/data.

data/processed is not committed (it's large and rebuilt by the notebooks), so the dashboard
reads compact, aggregated copies from app/data instead. Run this after notebooks 02–05:

    python app/prepare_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)

SIM_WEEKS = range(90, 102)  # must match notebook 04

cw = pd.read_parquet(PROCESSED / "commodity_week.parquet")

# same unique label as notebook 04: some commodity names exist in more than one department
dupes = cw.groupby("commodity_desc")["department"].nunique()
dupes = dupes[dupes > 1].index


def add_item(df):
    df = df.copy()
    df["item"] = np.where(df["commodity_desc"].isin(dupes),
                          df["commodity_desc"] + " (" + df["department"] + ")",
                          df["commodity_desc"])
    return df


# 1. simulated curves, summed over the 12 simulation weeks
grid = pd.read_parquet(PROCESSED / "simulator_grid.parquet")
ranges = (pd.read_parquet(PROCESSED / "simulator_curves.parquet")
            .groupby("item")[["disc_p05", "disc_p95"]].first())
curves = (grid.assign(gross=grid["units"] * grid["list_price"])
              .groupby(["department", "item", "discount_pct"], as_index=False)
              .agg(units=("units", "sum"), gross=("gross", "sum"),
                   revenue=("revenue", "sum"), margin=("margin", "first"))
              .merge(ranges, left_on="item", right_index=True))
curves.to_parquet(OUT / "curves.parquet", index=False)

# 2. what actually happened in the same weeks
reco = pd.read_parquet(PROCESSED / "discount_recommendations.parquet")
current = (add_item(cw.loc[cw["week_no"].isin(SIM_WEEKS)])
             .groupby("item", as_index=False)
             .agg(department=("department", "first"), units=("units", "sum"),
                  gross=("gross_value", "sum"), retail_disc=("retail_disc_amt", "sum"),
                  revenue=("sales_value", "sum")))
current["current_discount"] = current["retail_disc"] / current["gross"] * 100
current = current.merge(reco[["item", "confidence"]], on="item", how="left")
current = current.loc[current["item"].isin(curves["item"])]
current.to_parquet(OUT / "current.parquet", index=False)

# 3. baseline vs actual per week (notebook 03)
baseline = add_item(pd.read_parquet(PROCESSED / "baseline_week.parquet"))
baseline[["item", "department", "week_no", "units", "baseline_units", "incremental_units",
          "avg_discount_pct"]].to_parquet(OUT / "baseline.parquet", index=False)

# 4. campaign uplift scores (notebook 05), without household ids
uplift = pd.read_parquet(PROCESSED / "household_uplift_scores.parquet")
uplift[["campaign", "treated", "ps", "y", "y_clip", "uplift_pred", "uplift_group"]] \
    .to_parquet(OUT / "uplift.parquet", index=False)

for p in sorted(OUT.glob("*.parquet")):
    print(f"{p.name:<20} {p.stat().st_size / 1e3:>8,.0f} KB")
