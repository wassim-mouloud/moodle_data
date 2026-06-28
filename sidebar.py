import pandas as pd
import streamlit as st


def build_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    all_courses = sorted(df["cours"].dropna().unique())
    selected_courses = st.sidebar.multiselect(
        "Cours",
        options=all_courses,
        default=all_courses,
        placeholder="Tous les cours",
    )

    all_users = sorted(df["user_full"].dropna().unique())
    selected_users = st.sidebar.multiselect(
        "Utilisateur",
        options=all_users,
        default=all_users,
        placeholder="Tous les utilisateurs",
    )

    min_date  = df["date_session"].min().date()
    max_date  = df["date_session"].max().date()
    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    st.sidebar.divider()
    st.sidebar.markdown("**Filtres avancés**")

    gamif_choice = st.sidebar.radio(
        "Gamification",
        options=["Toutes les sessions", "Avec bonus 🎮", "Sans bonus"],
        index=0,
        horizontal=False,
    )

    msg_min = int(df["message_count"].min())
    msg_max = int(df["message_count"].max())
    if msg_min < msg_max:
        msg_range = st.sidebar.slider(
            "Nombre de messages",
            min_value=msg_min,
            max_value=msg_max,
            value=(msg_min, msg_max),
        )
    else:
        msg_range = (msg_min, msg_max)

    tok_min = int(df["tokens_used"].min())
    tok_max = int(df["tokens_used"].max())
    if tok_min < tok_max:
        tok_range = st.sidebar.slider(
            "Tokens consommés",
            min_value=tok_min,
            max_value=tok_max,
            value=(tok_min, tok_max),
        )
    else:
        tok_range = (tok_min, tok_max)

    dur_min = float(df["duration_min"].min())
    dur_max = float(df["duration_min"].max())
    if dur_min < dur_max:
        dur_range = st.sidebar.slider(
            "Durée (minutes)",
            min_value=round(dur_min, 1),
            max_value=round(dur_max, 1),
            value=(round(dur_min, 1), round(dur_max, 1)),
            step=0.5,
        )
    else:
        dur_range = (dur_min, dur_max)

    st.sidebar.divider()
    st.sidebar.caption(f"Dataset : {len(df)} sessions au total")

    mask = pd.Series(True, index=df.index)
    if selected_courses:
        mask &= df["cours"].isin(selected_courses)
    if selected_users:
        mask &= df["user_full"].isin(selected_users)
    if len(date_range) == 2:
        start, end = date_range
        mask &= df["date_session"].dt.date.between(start, end)
    if gamif_choice == "Avec bonus 🎮":
        mask &= df["has_bonus"]
    elif gamif_choice == "Sans bonus":
        mask &= ~df["has_bonus"]
    mask &= df["message_count"].between(*msg_range)
    mask &= df["tokens_used"].between(*tok_range)
    mask &= df["duration_min"].between(*dur_range)

    filtered = df[mask].copy()
    st.sidebar.caption(f"Après filtres : **{len(filtered)}** sessions")
    return filtered
