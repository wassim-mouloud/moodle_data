import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

PLOTLY_TEMPLATE = "plotly_dark"


def _apply_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b22",
        font_color="#c9d1d9",
    )
    return fig


def parse_keywords(series: pd.Series, min_len: int = 3, top_n: int = 20) -> pd.DataFrame:
    words: list[str] = []
    for cell in series.dropna():
        for kw in str(cell).split(","):
            kw = kw.strip().lower()
            if len(kw) >= min_len:
                words.append(kw)
    counts = Counter(words).most_common(top_n)
    return pd.DataFrame(counts, columns=["keyword", "count"])


def chart_messages_per_course(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby("cours")["message_count"].sum().reset_index().sort_values("message_count")
    fig = px.bar(
        agg, x="message_count", y="cours", orientation="h",
        title="Messages par cours",
        labels={"message_count": "Messages", "cours": ""},
        color="message_count", color_continuous_scale="Blues",
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(coloraxis_showscale=False, height=350)
    return _apply_theme(fig)


def chart_sessions_per_course(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby("cours").size().reset_index(name="sessions").sort_values("sessions")
    fig = px.bar(
        agg, x="sessions", y="cours", orientation="h",
        title="Sessions par cours",
        labels={"sessions": "Sessions", "cours": ""},
        color="sessions", color_continuous_scale="Teal",
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(coloraxis_showscale=False, height=350)
    return _apply_theme(fig)


def chart_activity_over_time(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby(["date_only", "cours"]).size().reset_index(name="sessions")
    agg["date_only"] = pd.to_datetime(agg["date_only"])
    fig = px.line(
        agg, x="date_only", y="sessions", color="cours",
        title="Activité dans le temps (sessions/jour par cours)",
        labels={"date_only": "Date", "sessions": "Sessions", "cours": "Cours"},
        markers=True,
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(height=350, legend=dict(orientation="h", y=-0.3))
    return _apply_theme(fig)


def chart_duration_distribution(df: pd.DataFrame) -> go.Figure:
    fig = px.histogram(
        df[df["duration_min"] > 0], x="duration_min",
        nbins=15,
        title="Distribution des durées de session",
        labels={"duration_min": "Durée (minutes)", "count": "Sessions"},
        color_discrete_sequence=["#58a6ff"],
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(height=350)
    return _apply_theme(fig)


def chart_tokens_vs_messages(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df, x="message_count", y="tokens_used",
        color="has_bonus",
        size="duration_min",
        hover_data=["user_full", "cours", "date_only"],
        title="Tokens consommés vs Messages (taille = durée, couleur = gamification)",
        labels={
            "message_count": "Messages",
            "tokens_used": "Tokens IA",
            "has_bonus": "Gamification",
            "duration_min": "Durée (min)",
        },
        color_discrete_map={True: "#f0883e", False: "#58a6ff"},
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(height=400)
    return _apply_theme(fig)


def chart_top_keywords(df: pd.DataFrame, cours: str | None = None) -> go.Figure:
    subset = df if cours is None else df[df["cours"] == cours]
    kw_df = parse_keywords(subset["topic_keywords"])
    title = "Top mots-clés des questions étudiantes" + (f" — {cours}" if cours else "")
    if kw_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Aucun mot-clé disponible")
        return _apply_theme(fig)
    fig = px.bar(
        kw_df.sort_values("count"), x="count", y="keyword", orientation="h",
        title=title,
        labels={"count": "Occurrences", "keyword": ""},
        color="count", color_continuous_scale="Viridis",
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(
        coloraxis_showscale=False,
        height=max(350, len(kw_df) * 22),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return _apply_theme(fig)


def chart_heatmap(df: pd.DataFrame) -> go.Figure:
    WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    WEEKDAY_FR    = {"Monday": "Lun", "Tuesday": "Mar", "Wednesday": "Mer",
                     "Thursday": "Jeu", "Friday": "Ven", "Saturday": "Sam", "Sunday": "Dim"}

    heat = (
        df.groupby(["weekday", "hour"])
        .size()
        .reindex(pd.MultiIndex.from_product([WEEKDAY_ORDER, range(24)], names=["weekday", "hour"]), fill_value=0)
        .reset_index(name="sessions")
    )
    heat["weekday_fr"] = heat["weekday"].map(WEEKDAY_FR)
    pivot = heat.pivot(index="weekday_fr", columns="hour", values="sessions")
    pivot = pivot.reindex([WEEKDAY_FR[d] for d in WEEKDAY_ORDER])

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}h" for h in range(24)],
        y=pivot.index.tolist(),
        colorscale="Blues",
        hoverongaps=False,
        hovertemplate="Heure: %{x}<br>Jour: %{y}<br>Sessions: %{z}<extra></extra>",
    ))
    fig.update_layout(title="Heatmap d'activité (heure × jour de semaine)", height=320)
    return _apply_theme(fig)


def chart_difficulty_score(difficulty_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        difficulty_df.sort_values("score_difficulte"),
        x="score_difficulte", y="cours", orientation="h",
        title="Score de difficulté par cours",
        labels={"score_difficulte": "Score de difficulté (0-100)", "cours": ""},
        color="score_difficulte", color_continuous_scale="OrRd",
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(coloraxis_showscale=False, height=max(350, len(difficulty_df) * 35))
    return _apply_theme(fig)


def chart_retention_heatmap(matrix: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=[f"S+{c}" for c in matrix.columns],
        y=matrix.index.tolist(),
        colorscale="Blues",
        zmin=0, zmax=100,
        hoverongaps=False,
        hovertemplate="Cohorte: %{y}<br>%{x}<br>Rétention: %{z}%<extra></extra>",
        texttemplate="%{z:.0f}%",
    ))
    fig.update_layout(
        title="Rétention par cohorte hebdomadaire",
        height=max(320, len(matrix) * 35),
        xaxis_title="Semaines après la 1ère session",
    )
    return _apply_theme(fig)
