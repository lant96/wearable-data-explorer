from __future__ import annotations

from datetime import date

import pandas as pd
from pydantic import BaseModel, ConfigDict

from .analysis import QueryError, select, summarise


class QuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str | None = None
    agg: str = "mean"
    by: str = "none"
    participants: list[str] = []
    start: date | None = None
    end: date | None = None
    explanation: str = ""
    unsupported_reason: str = ""


def run(df: pd.DataFrame, spec: QuerySpec) -> pd.DataFrame:
    """Execute a spec. Raises QueryError if it cannot be answered."""
    if spec.unsupported_reason:
        raise QueryError(spec.unsupported_reason)
    if spec.metric is None:
        raise QueryError("The query does not name a metric.")
    selected = select(df, spec.participants, spec.start, spec.end)
    return summarise(selected, spec.metric, spec.agg, spec.by)
