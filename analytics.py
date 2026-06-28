import pandas as pd

from charts import parse_keywords


def compute_dropout_risk(df: pd.DataFrame, inactivity_days: int = 14) -> pd.DataFrame:
    """
    Flag students who were active but have gone quiet relative to their own
    usage history and the dataset's most recent date.

    A student is "at risk" when the gap since their last session exceeds
    inactivity_days AND they had built up a usage history (>= 2 sessions) —
    one-off users are not flagged as they never had a sustained habit to drop.
    """
    if df.empty:
        return pd.DataFrame()

    last_seen_global = df["date_session"].max()

    per_user = (
        df.groupby(["user_full", "email"])
        .agg(
            sessions=("id", "count"),
            messages=("message_count", "sum"),
            last_session=("date_session", "max"),
            first_session=("date_session", "min"),
            avg_gap_days=("date_session", lambda s: s.sort_values().diff().dt.days.mean()),
        )
        .reset_index()
    )
    per_user["days_inactive"] = (last_seen_global - per_user["last_session"]).dt.days
    per_user["avg_gap_days"] = per_user["avg_gap_days"].fillna(0).round(1)

    at_risk = per_user[
        (per_user["days_inactive"] >= inactivity_days) & (per_user["sessions"] >= 2)
    ].copy()
    at_risk["severity"] = pd.cut(
        at_risk["days_inactive"],
        bins=[inactivity_days - 1, inactivity_days * 2, inactivity_days * 4, float("inf")],
        labels=["Modéré", "Élevé", "Critique"],
    )
    return at_risk.sort_values("days_inactive", ascending=False).reset_index(drop=True)


def compute_course_difficulty(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score 0-100 estimating how much friction a course generates, combining:
      - average session duration (longer = more struggle)
      - messages per session (more back-and-forth = more struggle)
      - keyword repetition rate (same topics resurfacing = unresolved confusion)
    Each component is min-max normalized across courses before averaging,
    so the score is only meaningful as a relative ranking within this dataset.
    """
    if df.empty:
        return pd.DataFrame()

    def repetition_rate(keywords_series: pd.Series) -> float:
        kw_df = parse_keywords(keywords_series)
        if kw_df.empty or kw_df["count"].sum() == 0:
            return 0.0
        total = kw_df["count"].sum()
        unique = len(kw_df)
        return 1 - (unique / total) if total else 0.0

    rows = []
    for cours, g in df.groupby("cours"):
        rows.append({
            "cours": cours,
            "sessions": len(g),
            "duree_moy": g["duration_min"].mean(),
            "msg_par_session": g["message_count"].mean(),
            "taux_repetition": repetition_rate(g["topic_keywords"]),
        })
    out = pd.DataFrame(rows)

    def norm(col: pd.Series) -> pd.Series:
        rng = col.max() - col.min()
        return (col - col.min()) / rng if rng > 0 else pd.Series(0.0, index=col.index)

    out["score_difficulte"] = (
        norm(out["duree_moy"]) + norm(out["msg_par_session"]) + norm(out["taux_repetition"])
    ) / 3 * 100
    out["score_difficulte"] = out["score_difficulte"].round(1)

    return out.sort_values("score_difficulte", ascending=False).reset_index(drop=True)


def compute_weekly_retention(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cohort retention matrix: for each weekly cohort (first week a student is
    seen), what fraction of that cohort is still active N weeks later.
    Standard cohort-retention construction, read row-by-row as % retained.
    """
    if df.empty:
        return pd.DataFrame()

    weeks = sorted(df["week"].unique())
    week_index = {w: i for i, w in enumerate(weeks)}

    first_week = df.groupby("user_full")["week"].apply(lambda s: min(s, key=lambda w: week_index[w]))
    active_weeks = df.groupby(["user_full", "week"]).size().reset_index()[["user_full", "week"]]
    active_weeks["cohort"] = active_weeks["user_full"].map(first_week)
    active_weeks["cohort_idx"] = active_weeks["cohort"].map(week_index)
    active_weeks["week_idx"] = active_weeks["week"].map(week_index)
    active_weeks["offset"] = active_weeks["week_idx"] - active_weeks["cohort_idx"]
    active_weeks = active_weeks[active_weeks["offset"] >= 0]

    cohort_sizes = first_week.value_counts()

    pivot = (
        active_weeks.groupby(["cohort", "offset"])["user_full"]
        .nunique()
        .reset_index(name="active")
    )
    pivot["cohort_size"] = pivot["cohort"].map(cohort_sizes)
    pivot["retention_pct"] = (pivot["active"] / pivot["cohort_size"] * 100).round(0)

    matrix = pivot.pivot(index="cohort", columns="offset", values="retention_pct")
    matrix = matrix.reindex(sorted(matrix.index, key=lambda w: week_index[w]))
    matrix.index = [f"{c} (n={cohort_sizes[c]})" for c in matrix.index]
    return matrix
