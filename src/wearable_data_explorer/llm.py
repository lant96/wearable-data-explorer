"""Turn a plain-language question into a QuerySpec using the Gemini API.

The model only sees the question plus a description of what exists (metric names,
participant ids, date range). It never sees the data rows and never writes code:
its JSON reply is validated as a QuerySpec, and analysis.py does the computing.
"""

from __future__ import annotations

import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from .analysis import AGGREGATIONS, GROUPINGS, QueryError
from .data import METRICS
from .query import QuerySpec, run

load_dotenv()

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3.8-flash"
RETRY_STATUS = {500, 502, 503, 504}


class LLMError(RuntimeError):
    """The model could not be reached or did not return a usable spec."""


def build_system_prompt(df: pd.DataFrame) -> str:
    metrics = "\n".join(f"- {m.name}: {m.label} ({m.unit})" for m in METRICS)
    participants = sorted(df["participant"].unique())
    return f"""You translate a question about wearable-device data into ONE JSON query spec.
Return ONLY a JSON object. No prose, no markdown.

DATA: daily summaries from a smartwatch study, one row per participant per day.
Some days are missing.
Participants: {participants}
Dates: {df["date"].min().date()} to {df["date"].max().date()}

METRICS (use exactly one of these names):
{metrics}

JSON FIELDS:
- metric: one metric name from the list above
- agg: one of {", ".join(AGGREGATIONS)} (default "mean")
- by: one of {", ".join(GROUPINGS)} (default "none")
- participants: list of participant ids as strings; empty list means everyone
- start, end: "YYYY-MM-DD", inclusive; leave out for the whole period
- explanation: one short sentence on how you understood the question
- unsupported_reason: see the last rule

RULES:
- Use only the metrics, participants and dates listed above. Never invent them.
- Turn relative time expressions ("last month", "the final two weeks") into explicit
  start and end dates, counting back from the last date in the data, not from today.
- Use "mean" unless the question asks for a total, a maximum, a minimum or a median.
- If the question needs data we do not have, asks for a diagnosis or medical advice,
  or is not about this data, leave metric out and write one sentence in unsupported_reason.
"""


def _call_gemini(system: str, user: str, api_key: str, model: str) -> str:
    """Send one question to Gemini and return the text of its reply.

    Temporary errors (like 503 "overloaded") are retried, up to 3 attempts in total.
    """
    url = API_URL.format(model=model)
    headers = {"x-goog-api-key": api_key}
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }

    for attempt in range(1, 4):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=60)
        except requests.RequestException as e:
            raise LLMError(f"Could not reach the Gemini API: {e}") from e

        if response.status_code == 200:
            try:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise LLMError("Gemini returned no answer (it may have been blocked).") from e

        if response.status_code in RETRY_STATUS and attempt < 3:
            time.sleep(2 * attempt)
            continue

        raise LLMError(f"Gemini API error {response.status_code}: {response.text[:800]}")

    raise LLMError("Gemini did not answer.")


def question_to_spec(
    question: str,
    df: pd.DataFrame,
    api_key: str | None = None,
    model: str | None = None,
) -> QuerySpec:
    """Ask the model for a spec. Retries once if the reply is not a valid QuerySpec."""
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMError("No API key. Set the GEMINI_API_KEY environment variable.")
    model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    system = build_system_prompt(df)
    user = question
    for _ in range(2):
        raw = _call_gemini(system, user, api_key, model)
        try:
            return QuerySpec.model_validate_json(raw)
        except ValidationError as e:
            user = (
                f"{question}\n\nYour previous reply was not a valid spec:\n{e}\n"
                "Return ONLY a valid JSON object that follows the field list."
            )
    raise LLMError("The model did not return a valid query spec after two attempts.")


if __name__ == "__main__":
    import sys

    from .data import load_all

    data = load_all("data/raw")
    spec = question_to_spec(" ".join(sys.argv[1:]) or "What is the average number of steps?", data)
    print(spec.model_dump_json(indent=2))
    try:
        print(run(data, spec).round(2).to_string(index=False))
    except QueryError as e:
        print(f"Cannot answer: {e}")
