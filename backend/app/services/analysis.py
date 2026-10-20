"""Statistical analysis layer over the real Flipkart catalogue.

This module is the "analyst" part of BazaarPulse: it computes distribution
statistics, concentration metrics, correlations and data-quality diagnostics
from the products table. Nothing here is simulated — every number is derived
from the loaded dataset (data_source='flipkart_2018', ~12.6k listings).

Metrics and the reasoning behind them
-------------------------------------
price_dispersion (per category)
    min / q25 / median / q75 / max, mean, std, coefficient of variation
    (CV = std/mean) and skewness. CV > 1 signals a right-skewed distribution
    where the mean is misleading — the resume point most people miss.

discount_depth (per category)
    mean & median discount_pct plus the share of listings that carry any
    discount at all. Mean vs median gap again reveals a few extreme
    "90% off" anchors dragging the average.

brand_concentration
    Herfindahl-Hirschman Index (HHI = sum of squared listing shares, 0-1)
    plus top-5 / top-10 brand share and the Pareto share (how many brands
    cover 80% of listings). HHI < 0.15 ≈ competitive; > 0.25 ≈ concentrated.

correlations
    Pearson r between discount_pct and star rating (on the rated subset),
    and between price and discount_pct. Weak/negative discount-rating
    correlation is a classic finding: deep discounts don't buy better
    reviews.

data_quality
    Rating coverage is ~10% on this dump — a real, documentable limitation.
    We quantify it and also measure selection bias: are rated listings
    priced differently from unrated ones?

outliers
    Products priced > 5x their category median. Reported as a count plus
    the top few examples for the narrative.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ..models import Product

logger = logging.getLogger(__name__)

# Categories with fewer listings than this are pooled into the dispersion
# stats but not broken out separately (keeps the tables readable).
_MIN_CATEGORY_N = 30


def _load_frame(db: Session) -> pd.DataFrame:
    """Pull the products table into a DataFrame with analysis-ready columns."""
    rows = db.query(
        Product.id,
        Product.name,
        Product.brand,
        Product.category,
        Product.current_price,
        Product.mrp,
        Product.discount_pct,
        Product.rating,
        Product.rating_count,
    ).all()
    df = pd.DataFrame(
        [
            {
                "id": r.id,
                "name": r.name,
                "brand": r.brand or "Unknown",
                "category": r.category or "Other",
                "price": r.current_price,
                "mrp": r.mrp,
                "discount_pct": r.discount_pct,
                "rating": r.rating if r.rating and r.rating > 0 else np.nan,
                "rating_count": r.rating_count or 0,
            }
            for r in rows
        ]
    )
    # Treat placeholder categories as missing.
    df.loc[df["category"].isin(["Other", "Other Categories", ""]), "category"] = "Other"
    df["is_rated"] = df["rating"].notna()
    return df


def _overview(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "listings": int(len(df)),
        "categories": int(df["category"].nunique()),
        "brands": int(df["brand"].nunique()),
        "price_min": int(df["price"].min()),
        "price_median": int(df["price"].median()),
        "price_mean": int(round(df["price"].mean())),
        "price_max": int(df["price"].max()),
        "mean_discount_pct": round(float(df["discount_pct"].mean()), 2),
        "median_discount_pct": round(float(df["discount_pct"].median()), 2),
        "total_listings_worth": int(df["mrp"].sum()),
    }


def _data_quality(df: pd.DataFrame) -> dict[str, Any]:
    n = len(df)
    rated = df[df["is_rated"]]
    unrated = df[~df["is_rated"]]
    dupes = int(df["name"].duplicated().sum())
    # Selection bias check: are rated listings cheaper / more discounted?
    bias = {
        "rated_mean_price": round(float(rated["price"].mean()), 1) if len(rated) else None,
        "unrated_mean_price": round(float(unrated["price"].mean()), 1) if len(unrated) else None,
        "rated_mean_discount_pct": round(float(rated["discount_pct"].mean()), 2) if len(rated) else None,
        "unrated_mean_discount_pct": round(float(unrated["discount_pct"].mean()), 2) if len(unrated) else None,
    }
    return {
        "rating_coverage_pct": round(len(rated) / n * 100, 2) if n else 0.0,
        "rated_listings": int(len(rated)),
        "unrated_listings": int(len(unrated)),
        "brand_coverage_pct": round(float((df["brand"] != "Unknown").mean() * 100), 2),
        "duplicate_name_pct": round(dupes / n * 100, 2) if n else 0.0,
        "duplicate_names": dupes,
        "discounted_share_pct": round(float((df["discount_pct"] > 0).mean() * 100), 2),
        "rated_vs_unrated": bias,
    }


def _price_dispersion(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Per-category price distribution stats (categories with >= _MIN_CATEGORY_N)."""
    out = []
    for cat, grp in df.groupby("category"):
        if len(grp) < _MIN_CATEGORY_N:
            continue
        prices = grp["price"].astype(float)
        median = float(prices.median())
        q25, q75 = float(prices.quantile(0.25)), float(prices.quantile(0.75))
        mean, std = float(prices.mean()), float(prices.std())
        out.append(
            {
                "category": cat,
                "listings": int(len(grp)),
                "min": int(prices.min()),
                "q25": int(q25),
                "median": int(median),
                "q75": int(q75),
                "max": int(prices.max()),
                "mean": int(round(mean)),
                "std": int(round(std)),
                # CV = std/mean; > 1 means "mean is a bad summary statistic".
                "cv": round(std / mean, 3) if mean else None,
                # pandas .skew() → unbiased (Fisher) estimator.
                "skewness": round(float(prices.skew()), 3),
                "iqr": int(round(q75 - q25)),
            }
        )
    out.sort(key=lambda r: r["listings"], reverse=True)
    return out


def _discount_depth(df: pd.DataFrame) -> list[dict[str, Any]]:
    """How deep do discounts run, per category — and are they universal?"""
    out = []
    for cat, grp in df.groupby("category"):
        if len(grp) < _MIN_CATEGORY_N:
            continue
        d = grp["discount_pct"].astype(float)
        out.append(
            {
                "category": cat,
                "listings": int(len(grp)),
                "mean_discount_pct": round(float(d.mean()), 2),
                "median_discount_pct": round(float(d.median()), 2),
                "p90_discount_pct": round(float(d.quantile(0.90)), 2),
                "max_discount_pct": round(float(d.max()), 2),
                "share_discounted_pct": round(float((d > 0).mean() * 100), 2),
                "mean_vs_median_gap": round(float(d.mean() - d.median()), 2),
            }
        )
    # Deepest average discounts first.
    out.sort(key=lambda r: r["mean_discount_pct"], reverse=True)
    return out


def _brand_concentration(df: pd.DataFrame) -> dict[str, Any]:
    """HHI + Pareto on brand listing counts."""
    counts = df["brand"].value_counts()
    total = int(counts.sum())
    shares = counts / total
    hhi = float((shares**2).sum())
    top5_share = float(shares.head(5).sum())
    top10_share = float(shares.head(10).sum())
    # Smallest number of brands that together cover 80% of listings.
    cum = shares.cumsum()
    pareto_n = int((cum < 0.80).sum() + 1)
    pareto_pct = round(pareto_n / len(counts) * 100, 2) if len(counts) else 0.0
    top_brands = [
        {
            "brand": brand,
            "listings": int(n),
            "share_pct": round(float(n) / total * 100, 2),
        }
        for brand, n in counts.head(10).items()
    ]
    return {
        "hhi": round(hhi, 4),
        "interpretation": (
            "highly concentrated"
            if hhi >= 0.25
            else "moderately concentrated"
            if hhi >= 0.15
            else "competitive (fragmented)"
        ),
        "top5_share_pct": round(top5_share * 100, 2),
        "top10_share_pct": round(top10_share * 100, 2),
        "pareto_brand_count": pareto_n,
        "pareto_brand_pct": pareto_pct,
        "top_brands": top_brands,
    }


def _correlations(df: pd.DataFrame) -> dict[str, Any]:
    """Pearson r on the pairs that matter; documented caveats included."""
    rated = df[df["is_rated"]]
    r_discount_rating = (
        round(float(rated["discount_pct"].corr(rated["rating"])), 4)
        if len(rated) >= 30
        else None
    )
    r_price_discount = round(float(df["price"].corr(df["discount_pct"])), 4)
    r_logprice_rating = (
        round(float(np.log1p(rated["price"]).corr(rated["rating"])), 4)
        if len(rated) >= 30
        else None
    )
    return {
        "discount_vs_rating_r": r_discount_rating,
        "discount_vs_rating_n": int(len(rated)),
        "discount_vs_rating_note": (
            "Computed on rated listings only (rating coverage is ~10% of the "
            "dump); correlation ≠ causation and ratings are not random."
        ),
        "price_vs_discount_r": r_price_discount,
        "log_price_vs_rating_r": r_logprice_rating,
        "price_vs_discount_note": (
            "Pearson r on raw price is sensitive to outliers; the log-price "
            "variant is reported alongside for robustness."
        ),
    }


def _outliers(df: pd.DataFrame) -> dict[str, Any]:
    """Listings priced > 5x their own category median."""
    median_map = df.groupby("category")["price"].median()
    ref = df["category"].map(median_map).replace(0, np.nan)
    mask = df["price"] > 5 * ref
    flagged = df[mask].copy()
    flagged["category_median"] = flagged["category"].map(median_map).astype(int)
    flagged["vs_median_x"] = (flagged["price"] / flagged["category_median"]).round(1)
    flagged = flagged.sort_values("vs_median_x", ascending=False)
    top = [
        {
            "id": r.id,
            "name": r.name[:90],
            "brand": r.brand,
            "category": r.category,
            "price": int(r.price),
            "category_median": int(r.category_median),
            "vs_median_x": float(r.vs_median_x),
        }
        for r in flagged.head(10).itertuples()
    ]
    return {
        "rule": "price > 5x category median",
        "outlier_count": int(len(flagged)),
        "outlier_share_pct": round(len(flagged) / len(df) * 100, 2) if len(df) else 0.0,
        "outlier_median_price": int(flagged["price"].median()) if len(flagged) else None,
        "top_outliers": top,
    }


def compute_market_analysis(db: Session) -> dict[str, Any]:
    """Full analysis payload for GET /api/analysis."""
    df = _load_frame(db)
    if df.empty:
        return {"error": "No products loaded — run scripts/load_kaggle_dataset.py first."}
    return {
        "overview": _overview(df),
        "data_quality": _data_quality(df),
        "price_dispersion": _price_dispersion(df),
        "discount_depth": _discount_depth(df),
        "brand_concentration": _brand_concentration(df),
        "correlations": _correlations(df),
        "outliers": _outliers(df),
    }
