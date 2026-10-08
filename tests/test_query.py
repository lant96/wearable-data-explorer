from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from wearable_data_explorer.analysis import QueryError
from wearable_data_explorer.query import QuerySpec, run


@pytest.fixture
def df():
    """Two participants, 4 days from 2021-07-05 (a Monday), steps known by hand."""
    dates = pd.date_range("2021-07-05", periods=4)
    rows = [("1", d, "Summer", 1000 + i) for i, d in enumerate(dates)]
    rows += [("2", d, "Summer", 2000 + i) for i, d in enumerate(dates)]
    return pd.DataFrame(rows, columns=["participant", "date", "season", "steps"])


def test_run_applies_filters_then_summary(df):
    spec = QuerySpec(
        metric="steps", agg="sum", by="participant", participants=["2"], start=date(2021, 7, 6)
    )
    r = run(df, spec)
    assert r["participant"].tolist() == ["2"]
    assert r["value"].tolist() == [2001 + 2002 + 2003]
    assert r["n"].tolist() == [3]


def test_defaults_mean_overall(df):
    r = run(df, QuerySpec(metric="steps"))
    assert r["value"].iloc[0] == pytest.approx(df["steps"].mean())


def test_unsupported_and_missing_metric_raise(df):
    with pytest.raises(QueryError, match="blood pressure"):
        run(df, QuerySpec(unsupported_reason="We have no blood pressure data."))
    with pytest.raises(QueryError, match="metric"):
        run(df, QuerySpec())


def test_spec_rejects_unknown_fields_and_bad_dates():
    with pytest.raises(ValidationError):
        QuerySpec.model_validate({"metric": "steps", "sql": "DROP TABLE x"})
    with pytest.raises(ValidationError):
        QuerySpec.model_validate({"metric": "steps", "start": "2021-13-45"})


def test_json_roundtrip_for_the_editable_spec():
    spec = QuerySpec(metric="sleep_hours", by="weekday", start=date(2021, 8, 1), explanation="x")
    assert QuerySpec.model_validate_json(spec.model_dump_json()) == spec
