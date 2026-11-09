# Promo Uplift & Profit Simulator

This project started with a question I couldn't shake: online stores run promotions almost every month, but do those promos actually make money, or do they just make the sales chart look good?

When a flash sale drives a spike in orders, most people call it a win. But part of that spike comes from customers who were going to buy anyway. The store gets the same sale, just at a lower margin. Some customers stock up during the promo and then skip the next month. Unless you separate those effects out, you can't really tell which promos are worth running.

## What I want to find out

1. After removing the sales that would have happened anyway (the baseline), how much extra profit does each type of promo actually generate?
2. What discount level still drives meaningful sales without eating up the margin?
3. If we keep running the current promo, where are sales and profit heading? And if we switch to a different promo, how much would the outcome change?
4. For targeted promos (coupons, push notifications, emails), who should get them and who shouldn't?

Question 4 is the part I'm most interested in. A discount given to someone who was already going to buy is just money left on the table.

## Data

I'm using the [Dunnhumby – The Complete Journey](https://www.kaggle.com/datasets/frtgnn/dunnhumby-the-complete-journey) dataset, which covers about two years of purchases from around 2,500 households.

I picked it mainly because it records which households received which campaign (`campaign_table`). Most public retail datasets don't have this, and without it question 4 isn't possible. It also includes coupon data and weekly info on which products were on in-store display or in the mailer (`causal_data`).

The data isn't included in this repo. To run the notebooks, download it from Kaggle and put the files in `data/raw/`.

## Approach

The work is split into three parts.

**1. Estimate the baseline.** Build a model of what sales would look like without any promotion, using trend, seasonality and calendar effects. Subtracting this from actual sales gives the lift the promo really created.

**2. Simulate scenarios.** Build a model that predicts sales for a given promo type and discount level, then run many combinations through it to find the one that maximizes profit, not sales volume.

**3. Pick who gets the promo.** Use uplift modeling to estimate how much more likely each customer is to buy *because of* the promo, instead of just how likely they are to buy at all.

A quick sanity check I keep coming back to: with a normal margin of m and a discount of d, sales need to grow by at least d / (m − d) just to break even. At a 40% margin, a 15% discount needs a 60% lift. That was a lot higher than I expected when I first worked it out.

## Repo structure

```
data/
  raw/            raw files from Kaggle (not committed)
  processed/
notebooks/
  01_data_understanding.ipynb
  02_eda.ipynb
  03_model.ipynb
  04_promo_response_simulator.ipynb
  05_uplift_model.ipynb
sql/              queries for feature preparation
app/              scenario simulator dashboard
```

## Progress

- [x] Define the questions and choose the dataset
- [ ] Data understanding
- [ ] EDA
- [ ] Baseline model
- [ ] Simulator and optimal discount
- [ ] Uplift model
- [ ] Dashboard
- [ ] Findings and recommendations

## Known limitations

- The dataset has no product cost, so I'm assuming margins by product category. Profit figures are estimates, not real numbers, and they'll shift if the assumptions change. I plan to include a sensitivity analysis so you can see how much.
- Stores tend to run promos during periods that are already busy, so the promo effect can't be fully separated from timing. The model's output is a starting point, and anything worth acting on should be confirmed with an A/B test first.
- This is US grocery retail data, so shopping behavior may differ from other markets.

## Contact

Questions or suggestions are welcome. You can reach me at [your email] or [your LinkedIn].
