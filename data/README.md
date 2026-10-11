# Data

The dataset is not included in this repository. Download the archive and place the 12 participant CSV files in `data/raw/`. This directory is git-ignored.

---

## Source

| | |
| --- | --- |
| Dataset | *Physical Activity, Heart Rate, and Sleep data collected with a Smartwatch (N=12)* |
| Authors | Igor Matias and Katarzyna Wac, Université de Genève |
| Download | [Yareta archive](https://yareta.unige.ch/archives/19bf7f3c-7d07-48be-8c03-9f754f766906) (use "Download archive") |
| DOI | https://doi.org/10.26037/yareta:mdrfwk26wzhgbfz5bxe4lv3v4i |
| Licence | Creative Commons Attribution 4.0 (CC BY 4.0) |
| Device | Withings ScanWatch |
| Period | 6 July 2021 to 21 April 2022 (290 days) |

See the [main README](../README.md#references) for dataset and publication citations.

---

## Files

The archive contains 12 participant CSV files, named by anonymous participant ID, with daily records. It also contains `ANNOTATORS.csv` (column definitions), `RECORDS.csv` (the list of participant IDs) and metadata files.

---

## Columns

The loader renames the raw columns and converts units.

| App column | Raw column | Unit | Meaning (from `ANNOTATORS.csv`) |
| --- | --- | --- | --- |
| `steps` | `ACTIVITY_steps` | steps/day | Total steps per day |
| `distance_km` | `ACTIVITY_distance` | km/day | Distance walking and running (raw: metres) |
| `soft_activity_min` | `ACTIVITY_soft` | min/day | Time at soft activity level (raw: seconds) |
| `moderate_activity_min` | `ACTIVITY_moderate` | min/day | Time at moderate activity level (raw: seconds) |
| `intense_activity_min` | `ACTIVITY_intense` | min/day | Time at intense activity level (raw: seconds) |
| `hr_day_avg` | `ACTIVITY_hr_average` | bpm | Average heart rate over the entire day |
| `hr_day_min` | `ACTIVITY_hr_min` | bpm | Minimum heart rate over the entire day |
| `hr_day_max` | `ACTIVITY_hr_max` | bpm | Maximum heart rate over the entire day |
| `sleep_hours` | `SLEEP_totalsleeptime` | h/night | Time asleep in the main sleep event of the day, excluding naps (raw: seconds) |
| `time_to_sleep_min` | `SLEEP_durationtosleep` | min | Time in bed until the start of sleep (raw: seconds) |
| `hr_sleep_avg` | `SLEEP_hr_average` | bpm | Average heart rate during the main sleep event |
| `hr_sleep_min` | `SLEEP_hr_min` | bpm | Minimum heart rate during the main sleep event |
| `hr_sleep_max` | `SLEEP_hr_max` | bpm | Maximum heart rate during the main sleep event |
| `wakeups` | `SLEEP_wakeupcount` | count | Number of wake-up moments during the main sleep event |
| `wake_time_min` | `SLEEP_wakeupduration` | min | Time spent awake during the main sleep event |

The loader also retains `participant` (from the filename), `date` and `season`. It derives weekday and month from date rather than using the raw `DAY_OF_THE_WEEK` and `MONTH` columns, which count from zero.

---

## Notes

- Date format: Dates appear as 06.07.21 (day.month.year), although the documentation specifies dd.mm.yyyy.

- Wake-up duration: The documentation does not specify the unit of SLEEP_wakeupduration. Its values are multiples of 60, so the loader assumes seconds and converts them to minutes. This assumption has not been independently verified.

- Missing values: Missingness varies between participants. Values are retained as missing rather than imputed.

- Unusual values: Values flagged during exploration are retained as recorded. See  [notebooks/01_exploration.ipynb](../notebooks/01_exploration.ipynb).
