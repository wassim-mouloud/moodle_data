# DreamU – Tutor IA Analytics

Dashboard Streamlit d'analyse des interactions étudiantes avec le Tutor IA de DreamU (IUT Aix-Marseille).

## Ce que ça fait

L'application charge un export CSV de la table `mdl_local_tutor_ia_logs` (MariaDB/Moodle) et produit un tableau de bord interactif organisé en 6 onglets :

| Onglet                | Contenu                                                                                                               |
| --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **KPIs**              | Sessions, messages, tokens IA, utilisateurs actifs, durée moyenne, taux de gamification                               |
| **Visualisations**    | Messages/sessions par cours, activité dans le temps, distribution des durées, mots-clés fréquents, heatmap jour/heure |
| **Suivi pédagogique** | Étudiants à risque de décrochage, score de difficulté par cours, matrice de rétention hebdomadaire                    |
| **Sessions**          | Table brute filtrée et exportable                                                                                     |
| **Classement**        | Ranking des étudiants les plus actifs                                                                                 |
| **Profils**           | Fiche individuelle par étudiant                                                                                       |

La sidebar permet de filtrer par cours, plage de dates et présence de gamification.

## Structure des fichiers

```
app.py          # point d'entrée Streamlit
data.py         # chargement et nettoyage du CSV
sidebar.py      # filtres sidebar
components.py   # blocs UI (KPIs, tableaux, profils…)
charts.py       # graphiques Plotly
analytics.py    # calculs : décrochage, difficulté, rétention
```

## Format du CSV attendu

Chaque ligne correspond à une session. Les colonnes (dans l'ordre) :

```
id, firstname, lastname, email, cours, message_count,
[keyword, keyword, ...],   ← longueur variable
tokens_used, session_duration, bonus_tokens, date_session
```

## Installation et lancement

```bash
pip install streamlit pandas plotly

streamlit run app.py
```

Puis charge ton CSV via le bouton **"Fichier CSV de logs"** dans la sidebar.
