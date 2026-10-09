"""Streamlit app: ask a question about the wearable data in plain language."""

import streamlit as st
from pydantic import ValidationError

from wearable_data_explorer.analysis import QueryError
from wearable_data_explorer.data import METRICS_BY_NAME, load_all
from wearable_data_explorer.llm import LLMError, question_to_spec
from wearable_data_explorer.query import QuerySpec, run
from wearable_data_explorer.visualisation import make_chart

EXAMPLES = [
    "What was the average sleep per weekday?",
    "Compare average steps between participants",
    "How did average heart rate change by month?",
]

st.set_page_config(page_title="Wearable Data Explorer", layout="wide")


@st.cache_data
def load_data():
    return load_all("data/raw")


def ask(question: str) -> None:
    """Ask the model for a spec and put it in the editable text box."""
    try:
        spec = question_to_spec(question, df)
    except LLMError as e:
        st.error(str(e))
        return
    st.session_state["spec_text"] = spec.model_dump_json(indent=2)


try:
    df = load_data()
except FileNotFoundError:
    st.error("No data found. Put the participant CSV files in data/raw/ and reload.")
    st.stop()

st.title("Wearable Data Explorer")
st.write(
    "Ask a question about daily smartwatch data from 12 people. The app shows how it "
    "understood your question, so you can check it before trusting the answer."
)

with st.form("ask"):
    question = st.text_input("Your question", placeholder=EXAMPLES[0])
    submitted = st.form_submit_button("Ask")
if submitted and question.strip():
    ask(question.strip())

st.caption("Or try an example:")
columns = st.columns(len(EXAMPLES))
for i, example in enumerate(EXAMPLES):
    if columns[i].button(example):
        ask(example)

if "spec_text" not in st.session_state:
    st.stop()

st.subheader("1. How I understood your question")
st.text_area("Query spec (you can edit this and the result updates)", key="spec_text", height=260)
try:
    spec = QuerySpec.model_validate_json(st.session_state["spec_text"])
except ValidationError as e:
    st.error(f"This spec is not valid: {e.errors()[0]['msg']} ({e.errors()[0]['loc']})")
    st.stop()
if spec.explanation:
    st.info(spec.explanation)

st.subheader("2. Result")
try:
    result = run(df, spec)
except QueryError as e:
    st.warning(f"Cannot answer: {e}")
    st.stop()

assert spec.metric is not None
metric = METRICS_BY_NAME[spec.metric]

if spec.by == "none":
    st.metric(f"{metric.label} ({spec.agg})", f"{result['value'].iloc[0]:.2f} {metric.unit}")
    st.caption(f"Based on {result['n'].iloc[0]} recorded days.")
else:
    st.plotly_chart(make_chart(result, spec), width="stretch")
    st.caption("Hover over a point or bar to see how many recorded days it is based on.")
    with st.expander("Data table"):
        st.dataframe(result)
