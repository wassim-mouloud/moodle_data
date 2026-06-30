import streamlit as st

from data import load_data
from sidebar import build_sidebar
from components import (
    render_kpis,
    render_course_summary,
    render_table,
    render_user_profiles,
    render_student_ranking,
    render_pedagogical_insights,
)
from charts import (
    chart_messages_per_course,
    chart_sessions_per_course,
    chart_activity_over_time,
    chart_duration_distribution,
    chart_tokens_vs_messages,
    chart_top_keywords,
    chart_heatmap,
)

st.set_page_config(
    page_title="DreamU – Tutor IA Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #c9d1d9;
        border-left: 3px solid #58a6ff; padding-left: 0.75rem;
        margin: 1.5rem 0 1rem 0;
    }
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #58a6ff; border-bottom-color: #58a6ff; }
</style>
""", unsafe_allow_html=True)


def main() -> None:
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Moodle-logo.svg/240px-Moodle-logo.svg.png",
        width=120,
    )
    st.sidebar.title("DreamU – Tutor IA")
    st.sidebar.caption("Dashboard analytique · IUT Aix-Marseille")
    st.sidebar.divider()

    uploaded = st.sidebar.file_uploader(
        "Fichier CSV de logs",
        type="csv",
        help="Exporte la table mdl_local_tutor_ia_logs depuis MariaDB puis charge-la ici.",
    )
    st.sidebar.divider()

    st.title("🎓 DreamU – Tutor IA Analytics")
    st.caption("Tableau de bord des interactions étudiantes · IUT Aix-Marseille Université")

    if uploaded is None:
        st.info("Charge un fichier CSV dans la sidebar pour commencer.")
        return

    df       = load_data(uploaded)
    filtered = build_sidebar(df)

    if filtered.empty:
        st.warning("Aucune session ne correspond aux filtres sélectionnés.")
        return

    tab_kpi, tab_charts, tab_insights, tab_table, tab_ranking, tab_users = st.tabs([
        "📊 KPIs", "📈 Visualisations", "⚠️ Suivi pédagogique", "📋 Sessions", "🏆 Classement", "👤 Profils",
    ])

    with tab_kpi:
        render_kpis(filtered)
        st.divider()
        render_course_summary(filtered)

    with tab_charts:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(chart_messages_per_course(filtered), use_container_width=True)
            with st.expander("ℹ️ Comment lire ce graphe ?"):
                st.markdown(
                    "Affiche le **nombre total de messages** échangés avec le Tutor IA pour chaque cours. "
                    "Un cours avec beaucoup de messages indique une forte sollicitation du tuteur — "
                    "cela peut refléter la difficulté du cours ou l'engagement des étudiants."
                )
        with col2:
            st.plotly_chart(chart_sessions_per_course(filtered), use_container_width=True)
            with st.expander("ℹ️ Comment lire ce graphe ?"):
                st.markdown(
                    "Affiche le **nombre de sessions** (conversations distinctes) ouvertes par cours. "
                    "À la différence des messages, une session peut contenir plusieurs échanges — "
                    "comparer les deux graphes permet de voir si les étudiants posent peu de questions longues ou beaucoup de questions courtes."
                )

        st.plotly_chart(chart_activity_over_time(filtered), use_container_width=True)
        with st.expander("ℹ️ Comment lire ce graphe ?"):
            st.markdown(
                "Montre l'**évolution du nombre de sessions par jour**, une courbe par cours. "
                "Les pics peuvent correspondre à des périodes d'examens, de devoirs ou de cours intensifs. "
                "Utilisez les filtres de la sidebar pour zoomer sur une période ou un cours spécifique."
            )

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(chart_duration_distribution(filtered), use_container_width=True)
            with st.expander("ℹ️ Comment lire ce graphe ?"):
                st.markdown(
                    "Répartit les sessions selon leur **durée en minutes**. "
                    "Une majorité de sessions très courtes (< 5 min) peut indiquer des questions rapides ou ponctuelles ; "
                    "des sessions longues suggèrent des étudiants qui travaillent en profondeur avec le tuteur."
                )
        with col4:
            kw_courses = ["Tous les cours"] + sorted(filtered["cours"].dropna().unique())
            kw_course_choice = st.selectbox("Filtrer les mots-clés par cours", kw_courses, key="kw_course_filter")
            kw_cours = None if kw_course_choice == "Tous les cours" else kw_course_choice
            st.plotly_chart(chart_top_keywords(filtered, cours=kw_cours), use_container_width=True)
            with st.expander("ℹ️ Comment lire ce graphe ?"):
                st.markdown(
                    "Recense les **mots-clés les plus fréquents** extraits des questions posées par les étudiants. "
                    "Permet d'identifier rapidement les **thèmes et notions** qui posent le plus de difficultés. "
                    "Plus une barre est longue, plus le mot-clé est apparu souvent dans les sessions filtrées. "
                    "Utilisez le sélecteur ci-dessus pour isoler les mots-clés d'un cours spécifique."
                )

        st.plotly_chart(chart_tokens_vs_messages(filtered), use_container_width=True)
        with st.expander("ℹ️ Comment lire ce graphe ?"):
            st.markdown(
                "Chaque point représente **une session**. "
                "L'axe horizontal indique le nombre de messages échangés, l'axe vertical le nombre de tokens IA consommés. "
                "La **taille** du point reflète la durée de la session, et la **couleur** distingue les sessions avec gamification (orange) de celles sans (bleu). "
                "Un point en haut à droite = session longue, très interactive et coûteuse en tokens."
            )

        st.plotly_chart(chart_heatmap(filtered), use_container_width=True)
        with st.expander("ℹ️ Comment lire ce graphe ?"):
            st.markdown(
                "Visualise les **plages horaires les plus actives** sur la semaine. "
                "Chaque case représente une combinaison jour/heure ; plus la couleur est foncée, plus il y a eu de sessions à ce moment. "
                "Utile pour identifier les créneaux d'utilisation intense (révisions nocturnes, pauses déjeuner, etc.)."
            )

    with tab_insights:
        render_pedagogical_insights(filtered)

    with tab_table:
        render_table(filtered)

    with tab_ranking:
        render_student_ranking(filtered)

    with tab_users:
        render_user_profiles(filtered)


if __name__ == "__main__":
    main()
