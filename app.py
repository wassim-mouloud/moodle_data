import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DreamU – Tutor IA Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark theme overrides ──────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .metric-card {
        background: linear-gradient(135deg, #1e2736 0%, #243044 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #58a6ff; margin: 0; }
    .metric-label { font-size: 0.85rem; color: #8b949e; margin: 0; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-delta { font-size: 0.8rem; color: #3fb950; margin-top: 0.2rem; }
    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #c9d1d9;
        border-left: 3px solid #58a6ff; padding-left: 0.75rem;
        margin: 1.5rem 0 1rem 0;
    }
    .test-badge {
        background-color: #da3633; color: white;
        border-radius: 4px; padding: 2px 6px; font-size: 0.7rem; font-weight: 600;
    }
    .gamif-badge {
        background-color: #1f6feb; color: white;
        border-radius: 4px; padding: 2px 6px; font-size: 0.7rem; font-weight: 600;
    }
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #58a6ff; border-bottom-color: #58a6ff; }
</style>
""", unsafe_allow_html=True)

PLOTLY_TEMPLATE = "plotly_dark"

def _apply_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b22",
        font_color="#c9d1d9",
    )
    return fig

# ── Test-session heuristics ───────────────────────────────────────────────────
TEST_EMAILS = {"admin@master.local"}
NOISE_KEYWORDS = {
    "zizi", "sallut", "tes", "oee", "slaut", "salu", "salut", "bonjour",
    "vas", "merci", "lendpoint",
}

def _is_test_session(row: pd.Series) -> bool:
    """Flag sessions that look like dev/admin tests."""
    if row["email"] in TEST_EMAILS:
        return True
    kws = {k.strip().lower() for k in str(row["topic_keywords"]).split(",") if k.strip()}
    if kws and kws.issubset(NOISE_KEYWORDS):
        return True
    return False

# ── Data loading ──────────────────────────────────────────────────────────────
def _parse_csv_row(line: str) -> dict:
    """
    Parse one raw CSV line whose topic_keywords field contains unquoted commas.
    Structure: id, firstname, lastname, email, cours, message_count,
               [keyword, keyword, ...],   <- variable length
               tokens_used, session_duration, bonus_tokens, date_session
    Strategy: split on comma, take first 6 fixed fields from the left and
    last 4 fixed fields from the right; everything in between is keywords.
    """
    parts = line.rstrip("\n").split(",")
    # last 4: date_session (may contain a space but no comma), bonus_tokens,
    # session_duration, tokens_used  →  indices -1 … -4
    date_session  = parts[-1].strip()
    bonus_tokens  = parts[-2].strip()
    session_dur   = parts[-3].strip()
    tokens_used   = parts[-4].strip()
    # first 6 fixed fields
    id_           = parts[0].strip()
    firstname     = parts[1].strip()
    lastname      = parts[2].strip()
    email         = parts[3].strip()
    cours         = parts[4].strip()
    message_count = parts[5].strip()
    # everything between index 6 and -4 is keywords
    keywords = ",".join(parts[6:-4]).strip()
    return {
        "id": id_, "firstname": firstname, "lastname": lastname,
        "email": email, "cours": cours, "message_count": message_count,
        "topic_keywords": keywords, "tokens_used": tokens_used,
        "session_duration": session_dur, "bonus_tokens": bonus_tokens,
        "date_session": date_session,
    }


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    with open(path, encoding="utf-8") as fh:
        rows = [_parse_csv_row(line) for line in fh if line.strip()]
    df = pd.DataFrame(rows)

    # Parse dates
    df["date_session"] = pd.to_datetime(df["date_session"], errors="coerce")
    df["date_only"] = df["date_session"].dt.date
    df["hour"] = df["date_session"].dt.hour
    df["weekday"] = df["date_session"].dt.day_name()
    df["week"] = df["date_session"].dt.to_period("W").astype(str)

    # Cast all numeric columns (all come in as strings from the custom parser)
    for col in ("id", "message_count", "tokens_used", "session_duration", "bonus_tokens"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Derived columns
    df["duration_min"] = (df["session_duration"] / 60).round(2)
    df["has_bonus"] = df["bonus_tokens"] > 0
    df["user_full"] = df["firstname"] + " " + df["lastname"]
    df["is_test"] = df.apply(_is_test_session, axis=1)

    return df

# ── Keyword parser ────────────────────────────────────────────────────────────
def parse_keywords(series: pd.Series, min_len: int = 3, top_n: int = 20) -> pd.DataFrame:
    """Return a DataFrame of (keyword, count) sorted descending."""
    words: list[str] = []
    for cell in series.dropna():
        for kw in str(cell).split(","):
            kw = kw.strip().lower()
            # Keep only keywords with enough characters and no pure noise
            if len(kw) >= min_len and kw not in NOISE_KEYWORDS:
                words.append(kw)
    counts = Counter(words).most_common(top_n)
    return pd.DataFrame(counts, columns=["keyword", "count"])

# ── Sidebar ───────────────────────────────────────────────────────────────────
def build_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Moodle-logo.svg/240px-Moodle-logo.svg.png",
        width=120,
    )
    st.sidebar.title("DreamU – Tutor IA")
    st.sidebar.caption("Dashboard analytique · IUT Aix-Marseille")
    st.sidebar.divider()

    # Test-session filter
    exclude_tests = st.sidebar.toggle(
        "Exclure les sessions de test",
        value=True,
        help="Masque les sessions identifiées comme admin/dev (email admin@master.local ou keywords aberrants)",
    )

    # Course filter
    all_courses = sorted(df["cours"].dropna().unique())
    selected_courses = st.sidebar.multiselect(
        "Cours",
        options=all_courses,
        default=all_courses,
        placeholder="Tous les cours",
    )

    # User filter
    all_users = sorted(df["user_full"].dropna().unique())
    selected_users = st.sidebar.multiselect(
        "Utilisateur",
        options=all_users,
        default=all_users,
        placeholder="Tous les utilisateurs",
    )

    # Date range filter
    min_date = df["date_session"].min().date()
    max_date = df["date_session"].max().date()
    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    st.sidebar.divider()
    st.sidebar.caption(f"Dataset : {len(df)} sessions au total")

    # Apply filters
    mask = pd.Series(True, index=df.index)
    if exclude_tests:
        mask &= ~df["is_test"]
    if selected_courses:
        mask &= df["cours"].isin(selected_courses)
    if selected_users:
        mask &= df["user_full"].isin(selected_users)
    if len(date_range) == 2:
        start, end = date_range
        mask &= df["date_session"].dt.date.between(start, end)

    filtered = df[mask].copy()
    st.sidebar.caption(f"Après filtres : **{len(filtered)}** sessions")
    return filtered

# ── KPI cards ─────────────────────────────────────────────────────────────────
def render_kpis(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">Indicateurs clés</div>', unsafe_allow_html=True)

    total_sessions = len(df)
    total_messages = int(df["message_count"].sum())
    total_tokens = int(df["tokens_used"].sum())
    unique_users = df["email"].nunique()
    avg_duration = df["duration_min"].mean() if len(df) else 0
    gamif_rate = (df["has_bonus"].sum() / len(df) * 100) if len(df) else 0
    avg_msg = df["message_count"].mean() if len(df) else 0

    cols = st.columns(7)
    kpis = [
        ("Sessions", total_sessions, ""),
        ("Messages", total_messages, ""),
        ("Tokens IA", f"{total_tokens:,}", ""),
        ("Utilisateurs", unique_users, ""),
        ("Durée moy.", f"{avg_duration:.1f} min", ""),
        ("Msg / session", f"{avg_msg:.1f}", ""),
        ("Taux gamif.", f"{gamif_rate:.0f}%", "🎮"),
    ]
    for col, (label, value, icon) in zip(cols, kpis):
        col.markdown(
            f'<div class="metric-card">'
            f'<p class="metric-value">{icon}{value}</p>'
            f'<p class="metric-label">{label}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Charts ────────────────────────────────────────────────────────────────────
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


def chart_top_keywords(df: pd.DataFrame) -> go.Figure:
    kw_df = parse_keywords(df["topic_keywords"])
    if kw_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Aucun mot-clé disponible")
        return _apply_theme(fig)
    fig = px.bar(
        kw_df.sort_values("count"), x="count", y="keyword", orientation="h",
        title="Top mots-clés des questions étudiantes",
        labels={"count": "Occurrences", "keyword": ""},
        color="count", color_continuous_scale="Viridis",
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(coloraxis_showscale=False, height=max(350, len(kw_df) * 22))
    return _apply_theme(fig)


def chart_heatmap(df: pd.DataFrame) -> go.Figure:
    WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    WEEKDAY_FR = {"Monday": "Lun", "Tuesday": "Mar", "Wednesday": "Mer",
                  "Thursday": "Jeu", "Friday": "Ven", "Saturday": "Sam", "Sunday": "Dim"}

    heat = (
        df.groupby(["weekday", "hour"])
        .size()
        .reindex(pd.MultiIndex.from_product([WEEKDAY_ORDER, range(24)], names=["weekday", "hour"]), fill_value=0)
        .reset_index(name="sessions")
    )
    heat["weekday_fr"] = heat["weekday"].map(WEEKDAY_FR)
    pivot = heat.pivot(index="weekday_fr", columns="hour", values="sessions")
    ordered_fr = [WEEKDAY_FR[d] for d in WEEKDAY_ORDER]
    pivot = pivot.reindex(ordered_fr)

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

# ── Detailed table ────────────────────────────────────────────────────────────
def render_table(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">Sessions détaillées</div>', unsafe_allow_html=True)

    display_cols = [
        "id", "user_full", "email", "cours", "date_session",
        "message_count", "tokens_used", "duration_min",
        "bonus_tokens", "has_bonus", "is_test", "topic_keywords",
    ]
    display_df = df[display_cols].rename(columns={
        "user_full": "Utilisateur",
        "cours": "Cours",
        "date_session": "Date",
        "message_count": "Messages",
        "tokens_used": "Tokens",
        "duration_min": "Durée (min)",
        "bonus_tokens": "Bonus",
        "has_bonus": "Gamif.",
        "is_test": "Test",
        "topic_keywords": "Mots-clés",
    })

    # Sort newest first
    display_df = display_df.sort_values("Date", ascending=False)

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "Date": st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY HH:mm"),
            "Messages": st.column_config.NumberColumn("Messages", format="%d 💬"),
            "Tokens": st.column_config.NumberColumn("Tokens", format="%d"),
            "Durée (min)": st.column_config.NumberColumn("Durée (min)", format="%.1f"),
            "Gamif.": st.column_config.CheckboxColumn("Gamif. 🎮"),
            "Test": st.column_config.CheckboxColumn("Test 🧪"),
        },
    )

# ── User profiles ─────────────────────────────────────────────────────────────
def render_user_profiles(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">Profils utilisateurs</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    users = sorted(df["user_full"].unique())
    selected = st.selectbox("Sélectionner un utilisateur", users)
    udf = df[df["user_full"] == selected]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sessions", len(udf))
    col2.metric("Messages totaux", int(udf["message_count"].sum()))
    col3.metric("Tokens consommés", f"{int(udf['tokens_used'].sum()):,}")
    col4.metric("Temps total", f"{udf['duration_min'].sum():.1f} min")

    col_a, col_b = st.columns(2)

    # Cours utilisés
    with col_a:
        st.markdown("**Cours utilisés**")
        cours_agg = udf.groupby("cours").agg(
            sessions=("id", "count"),
            messages=("message_count", "sum"),
        ).reset_index().sort_values("messages", ascending=False)
        st.dataframe(cours_agg, use_container_width=True, hide_index=True)

    # Top keywords for this user
    with col_b:
        st.markdown("**Sujets abordés (top mots-clés)**")
        kw_df = parse_keywords(udf["topic_keywords"], top_n=15)
        if not kw_df.empty:
            fig = px.bar(
                kw_df.sort_values("count"), x="count", y="keyword",
                orientation="h", height=280,
                color="count", color_continuous_scale="Blues",
                labels={"count": "", "keyword": ""},
                template=PLOTLY_TEMPLATE,
            )
            fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
            _apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas de mots-clés disponibles.")

    # Timeline
    st.markdown("**Activité dans le temps**")
    timeline = udf.groupby("date_only").agg(
        sessions=("id", "count"),
        messages=("message_count", "sum"),
    ).reset_index()
    timeline["date_only"] = pd.to_datetime(timeline["date_only"])
    fig_tl = px.bar(
        timeline, x="date_only", y="messages",
        labels={"date_only": "Date", "messages": "Messages"},
        color_discrete_sequence=["#58a6ff"],
        height=220,
        template=PLOTLY_TEMPLATE,
    )
    fig_tl.update_layout(margin=dict(t=10))
    _apply_theme(fig_tl)
    st.plotly_chart(fig_tl, use_container_width=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    df = load_data("tutor_ia_logs.csv")
    filtered = build_sidebar(df)

    st.title("🎓 DreamU – Tutor IA Analytics")
    st.caption("Tableau de bord des interactions étudiantes · IUT Aix-Marseille Université")

    if filtered.empty:
        st.warning("Aucune session ne correspond aux filtres sélectionnés.")
        return

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_kpi, tab_charts, tab_table, tab_users = st.tabs([
        "📊 KPIs", "📈 Visualisations", "📋 Sessions", "👤 Profils",
    ])

    with tab_kpi:
        render_kpis(filtered)

        st.divider()
        st.markdown('<div class="section-header">Aperçu des cours</div>', unsafe_allow_html=True)

        course_summary = filtered.groupby("cours").agg(
            sessions=("id", "count"),
            messages=("message_count", "sum"),
            tokens=("tokens_used", "sum"),
            utilisateurs=("email", "nunique"),
            durée_moy=("duration_min", "mean"),
            taux_gamif=("has_bonus", "mean"),
        ).reset_index().sort_values("messages", ascending=False)
        course_summary["durée_moy"] = course_summary["durée_moy"].round(1)
        course_summary["taux_gamif"] = (course_summary["taux_gamif"] * 100).round(0).astype(int).astype(str) + "%"
        course_summary.columns = ["Cours", "Sessions", "Messages", "Tokens", "Utilisateurs", "Durée moy. (min)", "Taux gamif."]
        st.dataframe(course_summary, use_container_width=True, hide_index=True)

    with tab_charts:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(chart_messages_per_course(filtered), use_container_width=True)
        with col2:
            st.plotly_chart(chart_sessions_per_course(filtered), use_container_width=True)

        st.plotly_chart(chart_activity_over_time(filtered), use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(chart_duration_distribution(filtered), use_container_width=True)
        with col4:
            st.plotly_chart(chart_top_keywords(filtered), use_container_width=True)

        st.plotly_chart(chart_tokens_vs_messages(filtered), use_container_width=True)
        st.plotly_chart(chart_heatmap(filtered), use_container_width=True)

    with tab_table:
        render_table(filtered)

    with tab_users:
        render_user_profiles(filtered)


if __name__ == "__main__":
    main()
