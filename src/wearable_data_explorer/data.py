"""Load the Geneva ScanWatch dataset (Matias & Wac, 2022).

One CSV per participant, one row per day. Raw columns are renamed to readable
metric names and converted to friendlier units (see the METRICS table).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

SEASONS = ["Summer", "Autumn", "Winter", "Spring"]


@dataclass(frozen=True)
class Metric:
    name: str
    source: str
    divisor: float
    label: str
    unit: str


METRICS = [
    Metric("steps", "ACTIVITY_steps", 1, "Steps", "steps/day"),
    Metric("distance_km", "ACTIVITY_distance", 1000, "Distance", "km/day"),
    Metric("soft_activity_min", "ACTIVITY_soft", 60, "Soft activity", "min/day"),
    Metric("moderate_activity_min", "ACTIVITY_moderate", 60, "Moderate activity", "min/day"),
    Metric("intense_activity_min", "ACTIVITY_intense", 60, "Intense activity", "min/day"),
    Metric("hr_day_avg", "ACTIVITY_hr_average", 1, "Heart rate, daily average", "bpm"),
    Metric("hr_day_min", "ACTIVITY_hr_min", 1, "Heart rate, daily minimum", "bpm"),
    Metric("hr_day_max", "ACTIVITY_hr_max", 1, "Heart rate, daily maximum", "bpm"),
    Metric("sleep_hours", "SLEEP_totalsleeptime", 3600, "Sleep duration", "h/night"),
    Metric("time_to_sleep_min", "SLEEP_durationtosleep", 60, "Time in bed before sleep", "min"),
    Metric("hr_sleep_avg", "SLEEP_hr_average", 1, "Heart rate asleep, average", "bpm"),
    Metric("hr_sleep_min", "SLEEP_hr_min", 1, "Heart rate asleep, minimum", "bpm"),
    Metric("hr_sleep_max", "SLEEP_hr_max", 1, "Heart rate asleep, maximum", "bpm"),
    Metric("wakeups", "SLEEP_wakeupcount", 1, "Wake-ups during sleep", "count"),
    # The dataset documentation gives no unit for this one, multiples of 60 suggest seconds
    Metric("wake_time_min", "SLEEP_wakeupduration", 60, "Time awake during sleep", "min"),
]
METRICS_BY_NAME = {m.name: m for m in METRICS}


def load_participant(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "participant": path.stem,
            "date": pd.to_datetime(raw["DATE"], format="%d.%m.%y"),
            "season": raw["SEASON"].map(dict(enumerate(SEASONS))),
        }
    )
    for m in METRICS:
        out[m.name] = raw[m.source] / m.divisor
    return out


def load_all(folder: str | Path) -> pd.DataFrame:
    folder = Path(folder)
    files = sorted(p for p in folder.glob("*.csv") if p.stem.isdigit())
    if not files:
        raise FileNotFoundError(f"No participant CSV files (e.g. 1487.csv) in {folder}")
    frames = [load_participant(p) for p in files]
    return pd.concat(frames, ignore_index=True).sort_values(
        ["participant", "date"], ignore_index=True
    )


if __name__ == "__main__":
    import sys

    df = load_all(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
    print(f"{df['participant'].nunique()} participants, {len(df)} rows")
    print(f"dates: {df['date'].min().date()} -> {df['date'].max().date()}")
    print("\nmissing share per metric:")
    print(df[[m.name for m in METRICS]].isna().mean().round(3).to_string())
    print("\nfirst rows:")
    print(df.head(3).to_string())
