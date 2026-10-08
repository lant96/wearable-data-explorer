from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from wearable_data_explorer.analysis import WEEKDAYS, QueryError, select, summarise
from wearable_data_explorer.data import load_all


@pytest.fixture
def small():
    """Two participants, 14 days (2021-07-05 is a Monday). Fully predictable."""
    dates = pd.date_range("2021-07-05", periods=14)
    frames = []
    for pid, base in (("1", 1000), ("2", 2000)):
        d = pd.DataFrame({"participant": pid, "date": dates, "season": "Summer"})
        d["steps"] = base + np.arange(14)
        d["sleep_hours"] = 7.0
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df.loc[0, "steps"] = np.nan
    return df


def test_mean_overall_skips_missing(small):
    r = summarise(small, "steps").iloc[0]
    assert r["n"] == 27
    assert r["value"] == pytest.approx(small["steps"].mean())


def test_weekday_order_and_counts(small):
    r = summarise(small, "steps", by="weekday")
    assert list(r["weekday"]) == WEEKDAYS
    assert r.set_index("weekday").loc["Mon", "n"] == 3
    assert r["n"].sum() == 27


def test_by_participant_sum(small):
    r = summarise(small, "steps", agg="sum", by="participant").set_index("participant")
    assert r.loc["2", "value"] == sum(2000 + i for i in range(14))


def test_select_window_and_participants(small):
    s = select(small, participants=["2"], start="2021-07-05", end="2021-07-11")
    assert len(s) == 7 and set(s["participant"]) == {"2"}


@pytest.mark.parametrize(
    "call",
    [
        lambda d: summarise(d, "blood_pressure"),
        lambda d: summarise(d, "steps", agg="mode"),
        lambda d: summarise(d, "steps", by="year"),
        lambda d: select(d, participants=["999"]),
        lambda d: select(d, start="2030-01-01"),
    ],
)
def test_bad_requests_raise(small, call):
    with pytest.raises(QueryError):
        call(small)


RAW = Path(__file__).parent.parent / "data" / "raw"


@pytest.mark.skipif(not any(RAW.glob("[0-9]*.csv")), reason="real data not present")
def test_real_data_weekday_matches_manual_pandas():
    df = load_all(RAW)
    r = summarise(df, "steps", by="weekday").set_index("weekday")
    manual = df.dropna(subset=["steps"]).groupby(df["date"].dt.dayofweek)["steps"].mean()
    assert r["value"].tolist() == pytest.approx(manual.tolist())
