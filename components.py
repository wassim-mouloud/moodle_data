import pandas as pd
import plotly.express as px
import streamlit as st

from charts import PLOTLY_TEMPLATE, _apply_theme, parse_keywords, chart_difficulty_score, chart_retention_heatmap
from analytics import compute_dropout_risk, compute_course_difficulty, compute_weekly_retention


def render_kpis(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">Indicateurs clés</div>', unsafe_allow_html=True)

    total_sessions = len(df)
    total_messages = int(df["message_count"].sum())
    total_tokens   = int(df["tokens_used"].sum())
    unique_users   = df["email"].nunique()
    avg_duration   = df["duration_min"].mean() if len(df) else 0
    gamif_rate     = (df["has_bonus"].sum() / len(df) * 100) if len(df) else 0
    avg_msg        = df["message_count"].mean() if len(df) else 0

    kpis = [
        ("Sessions",     total_sessions,          ""),
        ("Messages",     total_messages,          ""),
        ("Tokens IA",    f"{total_tokens:,}",     ""),
        ("Utilisateurs", unique_users,            ""),
        ("Durée moy.",   f"{avg_duration:.1f} min", ""),
        ("Msg / session",f"{avg_msg:.1f}",        ""),
        ("Taux gamif.",  f"{gamif_rate:.0f}%",    "🎮"),
    ]
    for col, (label, value, icon) in zip(st.columns(7), kpis):
        col.markdown(
            f'<div class="metric-card">'
            f'<p class="metric-value">{icon}{value}</p>'
            f'<p class="metric-label">{label}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_course_summary(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">Aperçu des cours</div>', unsafe_allow_html=True)

    summary = (
        df.groupby("cours")
        .agg(
            sessions=("id", "count"),
            messages=("message_count", "sum"),
            tokens=("tokens_used", "sum"),
            utilisateurs=("email", "nunique"),
            durée_moy=("duration_min", "mean"),
            taux_gamif=("has_bonus", "mean"),
        )
        .reset_index()
        .sort_values("messages", ascending=False)
    )
    summary["durée_moy"]  = summary["durée_moy"].round(1)
    summary["taux_gamif"] = (summary["taux_gamif"] * 100).round(0).astype(int).astype(str) + "%"
    summary.columns = ["Cours", "Sessions", "Messages", "Tokens", "Utilisateurs", "Durée moy. (min)", "Taux gamif."]
    st.dataframe(summary, use_container_width=True, hide_index=True)


def render_table(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">Sessions détaillées</div>', unsafe_allow_html=True)

    display_df = (
        df[["id", "user_full", "email", "cours", "date_session",
            "message_count", "tokens_used", "duration_min",
            "bonus_tokens", "has_bonus", "topic_keywords"]]
        .rename(columns={
            "user_full": "Utilisateur", "cours": "Cours", "date_session": "Date",
            "message_count": "Messages", "tokens_used": "Tokens",
            "duration_min": "Durée (min)", "bonus_tokens": "Bonus",
            "has_bonus": "Gamif.", "topic_keywords": "Mots-clés",
        })
        .sort_values("Date", ascending=False)
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            "id":          st.column_config.NumberColumn("ID", width="small"),
            "Date":        st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY HH:mm"),
            "Messages":    st.column_config.NumberColumn("Messages", format="%d 💬"),
            "Tokens":      st.column_config.NumberColumn("Tokens", format="%d"),
            "Durée (min)": st.column_config.NumberColumn("Durée (min)", format="%.1f"),
            "Gamif.":      st.column_config.CheckboxColumn("Gamif. 🎮"),
        },
    )


def render_student_ranking(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">Classement des étudiants</div>', unsafe_allow_html=True)

    ranking = (
        df.groupby(["user_full", "email"])
        .agg(
            sessions=("id", "count"),
            messages=("message_count", "sum"),
            tokens=("tokens_used", "sum"),
            durée_totale=("duration_min", "sum"),
            durée_moy=("duration_min", "mean"),
            taux_gamif=("has_bonus", "mean"),
            cours_distincts=("cours", "nunique"),
        )
        .reset_index()
    )
    ranking["durée_totale"] = ranking["durée_totale"].round(1)
    ranking["durée_moy"]    = ranking["durée_moy"].round(1)
    ranking["taux_gamif"]   = (ranking["taux_gamif"] * 100).round(0).astype(int).astype(str) + "%"

    sort_options = {
        "Messages totaux": "messages",
        "Sessions": "sessions",
        "Tokens consommés": "tokens",
        "Durée totale (min)": "durée_totale",
        "Cours distincts": "cours_distincts",
    }
    col_sort, col_order = st.columns([2, 1])
    with col_sort:
        sort_by_label = st.selectbox("Trier par", list(sort_options.keys()))
    with col_order:
        ascending = st.radio("Ordre", ["Décroissant", "Croissant"], horizontal=True) == "Croissant"

    sort_col = sort_options[sort_by_label]
    ranking  = ranking.sort_values(sort_col, ascending=ascending).reset_index(drop=True)
    ranking.index += 1

    ranking.columns = [
        "Étudiant", "Email", "Sessions", "Messages", "Tokens",
        "Durée totale (min)", "Durée moy. (min)", "Taux gamif.", "Cours distincts",
    ]

    st.dataframe(
        ranking,
        use_container_width=True,
        height=450,
        column_config={
            "Étudiant":          st.column_config.TextColumn("Étudiant", width="medium"),
            "Email":             st.column_config.TextColumn("Email", width="medium"),
            "Sessions":          st.column_config.NumberColumn("Sessions", format="%d"),
            "Messages":          st.column_config.NumberColumn("Messages", format="%d 💬"),
            "Tokens":            st.column_config.NumberColumn("Tokens", format="%d"),
            "Durée totale (min)":st.column_config.NumberColumn("Durée totale (min)", format="%.1f"),
            "Durée moy. (min)":  st.column_config.NumberColumn("Durée moy. (min)", format="%.1f"),
            "Taux gamif.":       st.column_config.TextColumn("Taux gamif. 🎮"),
            "Cours distincts":   st.column_config.NumberColumn("Cours distincts", format="%d"),
        },
    )

    st.divider()
    st.markdown('<div class="section-header">Visualisation de l\'engagement</div>', unsafe_allow_html=True)

    top_n = st.slider("Nombre d'étudiants à afficher", min_value=5, max_value=min(30, len(ranking)), value=min(10, len(ranking)))
    top_df = ranking.head(top_n)

    fig = px.bar(
        top_df.iloc[::-1],
        x="Messages",
        y="Étudiant",
        orientation="h",
        color="Sessions",
        color_continuous_scale="Blues",
        title=f"Top {top_n} étudiants — Messages envoyés",
        labels={"Messages": "Messages", "Étudiant": ""},
        template=PLOTLY_TEMPLATE,
        height=max(300, top_n * 30),
    )
    fig.update_layout(coloraxis_showscale=True, margin=dict(l=10, r=10, t=40, b=10))
    _apply_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("ℹ️ Comment lire ce graphe ?"):
        st.markdown(
            "Chaque barre représente un étudiant, trié selon le critère sélectionné ci-dessus. "
            "La **longueur** indique le nombre de messages envoyés, la **couleur** le nombre de sessions. "
            "Un étudiant avec beaucoup de messages mais peu de sessions pose des questions longues et approfondies ; "
            "l'inverse indique des interactions courtes et fréquentes."
        )


def render_user_profiles(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">Profils utilisateurs</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    selected = st.selectbox("Sélectionner un utilisateur", sorted(df["user_full"].unique()))
    udf = df[df["user_full"] == selected]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sessions",         len(udf))
    col2.metric("Messages totaux",  int(udf["message_count"].sum()))
    col3.metric("Tokens consommés", f"{int(udf['tokens_used'].sum()):,}")
    col4.metric("Temps total",      f"{udf['duration_min'].sum():.1f} min")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Cours utilisés**")
        cours_agg = (
            udf.groupby("cours")
            .agg(sessions=("id", "count"), messages=("message_count", "sum"))
            .reset_index()
            .sort_values("messages", ascending=False)
        )
        st.dataframe(cours_agg, use_container_width=True, hide_index=True)

    with col_b:
        st.markdown("**Sujets abordés (top mots-clés)**")
        kw_df = parse_keywords(udf["topic_keywords"], top_n=15)
        if not kw_df.empty:
            fig = px.bar(
                kw_df.sort_values("count"), x="count", y="keyword",
                orientation="h", height=max(280, len(kw_df) * 22),
                color="count", color_continuous_scale="Blues",
                labels={"count": "", "keyword": ""},
                template=PLOTLY_TEMPLATE,
            )
            fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
            _apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("ℹ️ Comment lire ce graphe ?"):
                st.markdown(
                    "Liste les **mots-clés les plus fréquents** dans les questions posées par cet étudiant. "
                    "Plus une barre est longue, plus le thème est revenu souvent dans ses sessions. "
                    "Permet d'identifier les notions sur lesquelles il revient régulièrement ou qui lui posent le plus de difficultés."
                )
        else:
            st.info("Pas de mots-clés disponibles.")

    st.markdown("**Activité dans le temps**")
    timeline = (
        udf.groupby("date_only")
        .agg(sessions=("id", "count"), messages=("message_count", "sum"))
        .reset_index()
    )
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
    with st.expander("ℹ️ Comment lire ce graphe ?"):
        st.markdown(
            "Montre le **nombre de messages envoyés par jour** par cet étudiant. "
            "Chaque barre correspond à une journée où il a utilisé le Tutor IA. "
            "Les pics révèlent les périodes d'activité intense — souvent avant un examen ou un rendu."
        )


def render_pedagogical_insights(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-header">⚠️ Étudiants à risque de décrochage</div>', unsafe_allow_html=True)

    inactivity_days = st.slider(
        "Seuil d'inactivité (jours)", min_value=7, max_value=60, value=14, step=1,
        help="Un étudiant ayant déjà utilisé le tuteur plusieurs fois est signalé s'il n'est pas revenu depuis ce nombre de jours.",
    )
    at_risk = compute_dropout_risk(df, inactivity_days=inactivity_days)

    if at_risk.empty:
        st.success("Aucun étudiant à risque détecté avec ce seuil.")
    else:
        display = at_risk[[
            "user_full", "email", "sessions", "messages", "days_inactive", "avg_gap_days", "severity",
        ]].rename(columns={
            "user_full": "Étudiant", "email": "Email", "sessions": "Sessions", "messages": "Messages",
            "days_inactive": "Jours d'inactivité", "avg_gap_days": "Écart moy. entre sessions (j)",
            "severity": "Sévérité",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)
        with st.expander("ℹ️ Comment interpréter ce tableau ?"):
            st.markdown(
                "Liste les étudiants ayant déjà eu **au moins 2 sessions** mais silencieux depuis plus que le seuil choisi. "
                "La **sévérité** compare l'inactivité actuelle au seuil (Modéré : 1-2×, Élevé : 2-4×, Critique : >4×). "
                "L'**écart moyen entre sessions** donne le rythme habituel de l'étudiant — utile pour juger si l'inactivité "
                "actuelle est anormale ou cohérente avec ses habitudes."
            )

    st.divider()
    st.markdown('<div class="section-header">📐 Score de difficulté par cours</div>', unsafe_allow_html=True)

    difficulty = compute_course_difficulty(df)
    if difficulty.empty:
        st.info("Pas assez de données pour calculer un score de difficulté.")
    else:
        st.plotly_chart(chart_difficulty_score(difficulty), use_container_width=True)
        with st.expander("ℹ️ Comment lire ce score ?"):
            st.markdown(
                "Score relatif (0-100) combinant trois signaux de friction, normalisés entre les cours du jeu de données filtré : "
                "**durée moyenne de session**, **messages échangés par session**, et **taux de répétition des mots-clés** "
                "(les étudiants reposent les mêmes questions = notion non comprise). "
                "Un score élevé signale un cours où les étudiants ont besoin de plus d'aide — utile pour prioriser un accompagnement renforcé."
            )
        with st.expander("📋 Détail du calcul"):
            st.dataframe(
                difficulty.rename(columns={
                    "cours": "Cours", "sessions": "Sessions", "duree_moy": "Durée moy. (min)",
                    "msg_par_session": "Messages/session", "taux_repetition": "Taux répétition mots-clés",
                    "score_difficulte": "Score difficulté",
                }),
                use_container_width=True, hide_index=True,
            )

    st.divider()
    st.markdown('<div class="section-header">📈 Rétention par cohorte hebdomadaire</div>', unsafe_allow_html=True)

    retention = compute_weekly_retention(df)
    if retention.empty or retention.shape[1] < 2:
        st.info("Pas assez de semaines de données pour calculer une rétention significative.")
    else:
        st.plotly_chart(chart_retention_heatmap(retention), use_container_width=True)
        with st.expander("ℹ️ Comment lire cette heatmap ?"):
            st.markdown(
                "Chaque ligne est une **cohorte** : les étudiants ayant utilisé le tuteur pour la première fois cette semaine-là "
                "(n = taille de la cohorte). Chaque colonne **S+N** indique le pourcentage de cette cohorte encore actif N semaines plus tard. "
                "Une chute rapide après S+0 indique un usage ponctuel (ex : devoir précis) plutôt qu'une adoption durable du tuteur."
            )
