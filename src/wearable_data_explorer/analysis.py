from __future__ import annotations

from datetime import date

import pandas as pd

from .data import METRICS_BY_NAME, SEASONS

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
AGGREGATIONS = ("mean", "median", "min", "max", "sum")
GROUPINGS = ("none", "weekday", "month", "season", "participant", "date")


class QueryError(ValueError):
    """The request is well-formed but cannot be answered with this data."""


def add_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add ordered `weekday` and `month` columns derived from the date."""
    out = df.copy()
    out["weekday"] = pd.Categorical(
        out["date"].dt.dayofweek.map(dict(enumerate(WEEKDAYS))),
        categories=WEEKDAYS,
        ordered=True,
    )
    out["month"] = out["date"].dt.to_period("M").astype(str)
    out["season"] = pd.Categorical(out["season"], categories=SEASONS, ordered=True)
    return out


def select(
    df: pd.DataFrame,
    participants: list[str] | None = None,
    start: str | date | None = None,
    end: str | date | None = None,
) -> pd.DataFrame:
    """Keep only the chosen participants and the (inclusive) date window."""
    if participants:
        unknown = sorted(set(participants) - set(df["participant"]))
        if unknown:
            raise QueryError(f"Unknown participant(s): {unknown}")
        df = df[df["participant"].isin(participants)]
    if start:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end:
        df = df[df["date"] <= pd.Timestamp(end)]
    if df.empty:
        raise QueryError("No data for that selection.")
    return df


def summarise(df: pd.DataFrame, metric: str, agg: str = "mean", by: str = "none") -> pd.DataFrame:
    """Aggregate one metric, optionally grouped.

    Returns columns [<by>, value, n], where n is the number of recorded days the
    value rests on (missing days are skipped, so n shows how solid a number is).
    """
    if metric not in METRICS_BY_NAME:
        raise QueryError(f"Unknown metric {metric!r}. Available: {list(METRICS_BY_NAME)}")
    if agg not in AGGREGATIONS:
        raise QueryError(f"Unknown aggregation {agg!r}. Available: {list(AGGREGATIONS)}")
    if by not in GROUPINGS:
        raise QueryError(f"Unknown grouping {by!r}. Available: {list(GROUPINGS)}")

    data = add_time_columns(df).dropna(subset=[metric])
    if data.empty:
        raise QueryError(f"No recorded values of {metric!r} in this selection.")

    if by == "none":
        return pd.DataFrame({"value": [data[metric].agg(agg)], "n": [len(data)]})
    return data.groupby(by, observed=True)[metric].agg(value=agg, n="count").reset_index()
