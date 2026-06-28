import io
import pandas as pd
import streamlit as st


def _parse_csv_row(line: str) -> dict:
    """
    Parse one raw CSV line whose topic_keywords field contains unquoted commas.
    Structure: id, firstname, lastname, email, cours, message_count,
               [keyword, keyword, ...],   <- variable length
               tokens_used, session_duration, bonus_tokens, date_session
    Strategy: take first 6 fields from the left, last 4 from the right;
    everything in between is the keywords field.
    """
    parts = line.rstrip("\n").split(",")
    return {
        "id":             parts[0].strip(),
        "firstname":      parts[1].strip(),
        "lastname":       parts[2].strip(),
        "email":          parts[3].strip(),
        "cours":          parts[4].strip(),
        "message_count":  parts[5].strip(),
        "topic_keywords": ",".join(parts[6:-4]).strip(),
        "tokens_used":    parts[-4].strip(),
        "session_duration": parts[-3].strip(),
        "bonus_tokens":   parts[-2].strip(),
        "date_session":   parts[-1].strip(),
    }


@st.cache_data
def load_data(source) -> pd.DataFrame:
    """Accept a file path (str) or a Streamlit UploadedFile."""
    if isinstance(source, str):
        with open(source, encoding="utf-8") as fh:
            lines = fh.readlines()
    else:
        lines = io.TextIOWrapper(source, encoding="utf-8").readlines()

    df = pd.DataFrame([_parse_csv_row(l) for l in lines if l.strip()])

    df["date_session"] = pd.to_datetime(df["date_session"], errors="coerce")
    df["date_only"]    = df["date_session"].dt.date
    df["hour"]         = df["date_session"].dt.hour
    df["weekday"]      = df["date_session"].dt.day_name()
    df["week"]         = df["date_session"].dt.to_period("W").astype(str)

    for col in ("id", "message_count", "tokens_used", "session_duration", "bonus_tokens"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["duration_min"] = (df["session_duration"] / 60).round(2)
    df["has_bonus"]    = df["bonus_tokens"] > 0
    df["user_full"]    = df["firstname"] + " " + df["lastname"]

    return df
