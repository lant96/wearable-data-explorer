from __future__ import annotations

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from .data import METRICS_BY_NAME
from .query import QuerySpec

TIME_GROUPINGS = ("date", "month")


def make_chart(result: pd.DataFrame, spec: QuerySpec) -> Figure:
    """Draw a grouped result: a line over time, otherwise bars."""

    if spec.metric is None or spec.by == "none":
        raise ValueError("make_chart needs a metric and a grouping.")

    metric = METRICS_BY_NAME[spec.metric]
    title = f"{metric.label}: {spec.agg} by {spec.by}"
    labels = {"value": f"{metric.label} ({metric.unit})", "n": "days recorded"}

    if spec.by in TIME_GROUPINGS:
        fig = px.line(
            result,
            x=spec.by,
            y="value",
            title=title,
            labels=labels,
            hover_data=["n"],
            markers=(spec.by == "month"),
        )
    else:
        fig = px.bar(result, x=spec.by, y="value", title=title, labels=labels, hover_data=["n"])
        fig.update_xaxes(type="category")
    return fig
