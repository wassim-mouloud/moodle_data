# Estud{IA}nt — IA Souveraine, Équité et Pédagogie Critique

**TER Master 1 Informatique, parcours SID — Aix-Marseille Université**
**Année universitaire 2025-2026**

**Encadrant :** Alain Casali (alain.casali@univ-amu.fr)

**Contribution documentée dans ce rapport :** Wassim Mouloud & Rami Chahine
— volet Data & Learning Analytics

---

## Sommaire

1. [Présentation du sujet](#1-présentation-du-sujet)
2. [État de l'art](#2-état-de-lart)
3. [Solution proposée](#3-solution-proposée)
4. [Expérimentations](#4-expérimentations)
5. [Conclusion](#5-conclusion)
6. [Annexes](#6-annexes)
7. [Bibliographie](#7-bibliographie)

---

## 1. Présentation du sujet

### 1.1 Objectifs généraux

Le projet Estud{IA}nt s'inscrit dans les ambitions DREAM-U de modernisation des pratiques pédagogiques à Aix-Marseille Université. L'idée directrice est simple à énoncer mais ambitieuse à réaliser : permettre à chaque étudiant d'accéder gratuitement et de façon équitable à un assistant pédagogique basé sur un grand modèle de langage (LLM), sans dépendre d'un abonnement privé (ChatGPT, Claude, etc.) ni d'un envoi de données vers des serveurs tiers échappant au contrôle de l'établissement.

Pour répondre à cette ambition, l'équipe a fait le choix d'une **IA souveraine** : un modèle de langage open-weight (Gemma 4B) déployé localement sur du matériel appartenant à l'IUT (un serveur NVIDIA DGX Spark), exposé via une API interne et intégré directement dans l'environnement pédagogique des étudiants, à savoir Moodle (instance Ametice). Cette intégration prend la forme d'un plugin, **Tutor IA**, qui répond aux questions des étudiants en se basant exclusivement sur le contenu du cours dans lequel il est activé — contrainte volontaire qui vise à limiter les usages hors-sujet et à ancrer l'outil dans la pédagogie du cours plutôt qu'à en faire un chatbot généraliste.

Concrètement, le plugin se présente sous la forme d'une interface de chat directement intégrée à la page du cours Moodle concerné. Lorsqu'un étudiant pose une question, celle-ci est transmise via `moodle-proxy` au LLM (Gemma 4B) servi par `hal-vllm-chat`, en passant par une couche d'abstraction d'API compatible OpenAI (`hal-litellm`) et un composant de routage (`hal-router`). La présence d'une base de données vectorielle dans l'infrastructure (`hal-qdrant`) indique que les réponses ne sont pas générées à partir des seules connaissances générales du modèle, mais s'appuient sur une recherche augmentée par récupération (RAG) dans le contenu du cours : le contenu pédagogique est préalablement indexé sous forme vectorielle, puis les passages les plus pertinents par rapport à la question posée sont injectés dans le contexte fourni au modèle avant génération de la réponse. C'est ce mécanisme qui permet au tuteur de rester ancré dans le contenu réel du cours plutôt que de répondre de façon générique.

Le plugin applique également un système de quota et de gamification : chaque étudiant dispose d'un nombre de messages limité par défaut sur un cours donné (`message_count`) ; une fois ce quota approché ou atteint, un quiz bonus est proposé, dont les bonnes réponses débloquent des messages supplémentaires, journalisés dans le champ `bonus_tokens`. Ce mécanisme répond directement à l'objectif de sensibilisation aux coûts énergétiques et financiers de l'usage d'un LLM affiché par le projet, tout en introduisant un point de passage pédagogique actif (le quiz) entre deux phases d'usage passif du tuteur.

Le projet poursuit plusieurs objectifs imbriqués :

- **Équité numérique** : tous les étudiants ont accès au même outil, sans barrière financière, indépendamment de leur capacité à payer un abonnement IA personnel.
- **Pédagogie critique** : au-delà du simple tuteur qui aide à comprendre un cours, certains usages explorent des rôles agentiques différenciés — par exemple une IA volontairement biaisée déployée en BUT1 Informatique, destinée à entraîner les étudiants à questionner et vérifier les réponses d'un système d'IA plutôt qu'à leur faire une confiance aveugle.
- **Sensibilisation aux coûts** : un système de quotas de tokens est mis en place, avec un mécanisme de gamification (quiz bonus) qui permet de débloquer des messages supplémentaires en cas de bonnes réponses. L'objectif pédagogique est double : limiter l'usage passif du tuteur (copier-coller de questions sans réflexion) et sensibiliser les étudiants au fait qu'une requête à un LLM a un coût réel, énergétique et financier.
- **Suivi et remédiation** : offrir aux enseignants des données exploitables sur l'usage du tuteur par leurs étudiants, dans une logique de suivi ORE (Observatoire de la Réussite Étudiante) et de détection de difficultés pour faciliter une remédiation personnalisée.
- **Learning Analytics** : structurer la mesure de l'impact de l'outil sur la persévérance et la réussite des étudiants, ce qui suppose de définir, calculer et visualiser des indicateurs pertinents à partir des traces d'usage du tuteur.

Ma contribution personnelle au sein de ce projet collectif porte exclusivement sur ce dernier point : je n'ai pas participé au développement du plugin Tutor IA ni à l'intégration du modèle de langage (travail réalisé par d'autres membres de l'équipe), mais j'ai pris en charge l'ensemble de la chaîne Data, de l'extraction des traces brutes jusqu'à la production d'un tableau de bord analytique.

### 1.2 Analyse du sujet

Le sujet Estud{IA}nt soulève, du point de vue spécifique de la partie Data dont j'ai eu la responsabilité, plusieurs problèmes techniques et méthodologiques qu'il convient de poser clairement avant de présenter la solution retenue.

**Accéder aux données sans perturber un système de production.** Les traces d'usage du tuteur IA sont stockées dans la base MariaDB d'une instance Moodle active (`moodle-lucas`), elle-même hébergée dans un conteneur Docker sur un serveur accessible uniquement via un réseau privé (Tailscale). Le premier problème est donc un problème d'accès : comment récupérer des données depuis une base de production, sans droits d'administration système préétablis, en respectant le périmètre de sécurité du réseau du projet, et sans risquer d'impacter le service ?

**Extraire une donnée structurée à partir d'un outil non outillé pour l'export.** Le CLI `mariadb` utilisé pour interroger la base ne supporte pas l'option `--fields-terminated-by`, qui permettrait normalement un export CSV propre. Le format de sortie par défaut (tabulations) doit donc être transformé, ce qui introduit un risque de corruption si certains champs contiennent eux-mêmes des tabulations ou des virgules — c'est précisément le cas du champ `topic_keywords`, qui contient une liste de mots-clés séparés par des virgules non échappées. Le problème devient alors un problème de **parsing robuste** : comment reconstruire une ligne structurée à 11 colonnes alors qu'une colonne au milieu de la ligne a un nombre de champs variable et utilise le même séparateur que le format d'export choisi ?

**Construire des indicateurs pédagogiquement pertinents à partir de traces brutes.** Une fois les données chargées, la question n'est plus seulement technique mais analytique : quelles métriques permettent réellement de répondre aux objectifs affichés par le projet (persévérance, réussite, équité, sensibilisation aux coûts) ? Un simple comptage de messages ou de tokens ne suffit pas à révéler un décrochage, une difficulté pédagogique récurrente sur un cours donné, ou un effet de la gamification sur l'engagement. Il a donc fallu définir des indicateurs dérivés (durée de session, taux de répétition des mots-clés, écarts entre sessions, cohortes hebdomadaires) capables de transformer une table de logs en informations actionnables pour un enseignant.

**Restituer l'information à un public non technique.** Les destinataires finaux des analyses — enseignants, encadrant, équipe DREAM-U — ne sont pas nécessairement familiers avec la manipulation de données brutes. Le sujet impose donc une contrainte de restitution : produire un outil interactif, visuel et explicite (avec des explications de lecture pour chaque graphique), plutôt qu'un simple notebook d'analyse statique.

**Travailler avec un volume de données extrêmement limité.** Enfin, un problème transversal à toute la partie expérimentation est la faiblesse du volume de données réellement disponible au moment de la rédaction de ce rapport : la phase de test n'a généré que 18 sessions pour 4 utilisateurs, ce qui limite mécaniquement la portée statistique de toute analyse de comportement étudiant à grande échelle, ce qui a orienté une partie du travail vers l'extension progressive de la collecte sur la durée du projet afin de disposer d'un historique suffisant pour valider les indicateurs les plus exigeants en données (rétention par cohorte, score de difficulté).

---

## 2. État de l'art

### 2.1 Learning Analytics et plateformes pédagogiques

Les Learning Analytics — la collecte, l'analyse et la restitution de données issues de l'usage d'environnements numériques d'apprentissage — constituent un champ de recherche et de pratique déjà mature dans l'enseignement supérieur. Les plateformes de LMS (Learning Management System) génériques telles que Moodle proposent nativement des modules de reporting (logs de connexion, complétion d'activités, temps passé sur une ressource), mais ces données restent en général peu exploitées au-delà d'un usage administratif basique, faute d'outils d'analyse adaptés aux besoins pédagogiques fins des enseignants.

Les approches existantes pour combler cet écart se répartissent globalement en deux familles : des **plugins d'analytics intégrés au LMS** (par exemple les rapports d'engagement natifs de Moodle, ou des extensions tierces de visualisation), qui ont l'avantage de la simplicité de déploiement mais l'inconvénient d'une faible flexibilité analytique ; et des **pipelines externes** qui extraient les données du LMS vers un environnement d'analyse dédié (souvent Python/pandas, R, ou des outils de BI comme Power BI/Tableau), offrant une liberté analytique bien plus grande au prix d'un travail d'intégration supplémentaire. La solution retenue dans Estud{IA}nt relève de cette seconde famille.

### 2.2 Tuteurs intelligents et agents conversationnels pédagogiques

L'idée d'un tuteur automatisé capable de répondre aux questions des étudiants n'est pas nouvelle : les systèmes de tutorat intelligent (Intelligent Tutoring Systems, ITS) existent depuis plusieurs décennies, historiquement construits sur des bases de règles ou des modèles de connaissances explicites du domaine enseigné. L'arrivée des grands modèles de langage a profondément renouvelé ce champ en permettant des interactions en langage naturel beaucoup plus flexibles, sans nécessiter de modélisation experte exhaustive du domaine.

Cette évolution s'accompagne cependant de deux tensions bien documentées dans la littérature et dans le débat public sur l'IA en éducation : le risque de **dépendance cognitive** (l'étudiant obtient une réponse sans construire son propre raisonnement) et le risque de **confiance excessive** envers des réponses qui peuvent être incorrectes ou biaisées (phénomène d'hallucination des LLM). C'est précisément ce second risque que le projet Estud{IA}nt tente d'adresser de façon originale, en envisageant le déploiement volontaire d'agents biaisés dans certains contextes pédagogiques (BUT1 Informatique), pour former les étudiants à l'esprit critique face à l'IA plutôt que de chercher à masquer ce risque.

### 2.3 IA souveraine et hébergement local de modèles de langage

La quasi-totalité des usages grand public de l'IA générative repose sur des modèles propriétaires hébergés par des acteurs privés (OpenAI, Anthropic, Google), accessibles via abonnement et impliquant un transfert de données vers des infrastructures externes à l'établissement. Face à ce constat, une tendance croissante dans l'enseignement supérieur et la recherche publique consiste à déployer des modèles open-weight (Llama, Mistral, Gemma) sur une infrastructure matérielle propre, via des frameworks d'inférence optimisés tels que vLLM. Cette approche, qualifiée de souveraine, répond à des enjeux de confidentialité des données étudiantes, de maîtrise des coûts à long terme, et d'indépendance vis-à-vis des fournisseurs commerciaux. Le choix de Gemma 4B servi par vLLM sur un serveur DGX Spark, fait par les membres du projet en charge de la partie IA, s'inscrit directement dans cette tendance.

### 2.4 Positionnement de la contribution Data

Le tableau de bord développé dans ce projet s'inspire des outils de Business Intelligence usuels (dashboards interactifs, filtres dynamiques, indicateurs clés) tout en les adaptant au contexte spécifique des Learning Analytics : les indicateurs ne visent pas seulement à décrire l'usage (combien de messages, combien de sessions) mais à révéler des signaux actionnables pour un enseignant (risque de décrochage, score de difficulté par cours, dynamique de rétention dans le temps). Cette orientation rapproche la démarche des travaux sur la détection précoce du décrochage étudiant (early dropout prediction), tout en restant, dans le cadre de ce TER et au vu du volume de données disponible, à un niveau descriptif et heuristique plutôt que prédictif au sens d'un modèle de machine learning entraîné.

---

## 3. Solution proposée

### 3.1 Vue d'ensemble de l'infrastructure du projet

Avant de décrire ma contribution propre, il est nécessaire de situer l'infrastructure globale du projet, déployée et administrée par l'ensemble de l'équipe.

L'ensemble des serveurs du projet communique via **Tailscale**, un réseau privé virtuel maillé (mesh VPN) construit sur le protocole WireGuard et le chiffrement ChaCha20. Ce choix permet d'exposer des services internes (bases de données, API d'inférence) entre serveurs géographiquement distincts sans les rendre accessibles publiquement sur Internet, tout en simplifiant la connexion SSH au sein de l'équipe.

Deux serveurs principaux composent l'infrastructure :

- **Le serveur Moodle** (`100.71.206.63`, Debian), qui héberge plusieurs instances Moodle conteneurisées via Docker : `moodle-lucas` (port 8084, avec sa base `moodle-db-lucas`) qui constitue l'instance cible du plugin Tutor IA et la source des données analysées dans ce rapport, ainsi que des instances additionnelles (`moodle-master`, `moodle-younes`, `moodle-test`) utilisées par les autres membres de l'équipe pour leurs propres développements.
- **Le serveur GPU DGX Spark** (`100.76.166.71`, Ubuntu aarch64), qui héberge la chaîne d'inférence du LLM : `hal-vllm-chat` (serveur Gemma 4B servi par vLLM), `hal-litellm` (couche d'abstraction d'API compatible OpenAI), `hal-router` (routage des requêtes), `hal-qdrant` (base vectorielle, probablement utilisée pour de la recherche augmentée par récupération sur le contenu des cours) et `moodle-proxy`.

Le plugin **Tutor IA**, intégré à `moodle-lucas`, expose aux étudiants une interface de chat dans leurs cours. Chaque échange est journalisé dans une table dédiée de la base MariaDB de l'instance, `mdl_local_tutor_ia_logs`, qui constitue le point d'entrée unique de l'ensemble du travail décrit dans ce rapport.

### 3.2 Pipeline d'extraction des données

La chaîne d'extraction que j'ai mise en place se décompose en trois étapes, exécutées manuellement à ce stade du projet (l'automatisation d'un export récurrent constitue une perspective évoquée en conclusion).

**Étape 1 — Récupération des identifiants de connexion à la base.** Les identifiants de connexion à la base MariaDB de l'instance `moodle-lucas` ne sont pas documentés séparément ; ils sont injectés comme variables d'environnement dans le conteneur Docker correspondant. Ils ont été récupérés par inspection de l'environnement du conteneur :

```bash
docker exec moodle-db-lucas env
```

Cette commande a permis d'identifier l'utilisateur (`bn_moodle`), le mot de passe et la base cible (`bitnami_moodle`), confirmant que l'image Docker utilisée est basée sur la distribution Bitnami de Moodle.

**Étape 2 — Extraction et export CSV.** La table `mdl_local_tutor_ia_logs` a été interrogée directement depuis le conteneur de base de données via le client `mariadb` :

```bash
docker exec moodle-db-lucas mariadb -u bn_moodle -pmoodle_lucas_2026 bitnami_moodle \
  --batch --silent \
  -e "SELECT * FROM mdl_local_tutor_ia_logs;" \
  | sed 's/\t/,/g' > tutor_logs.csv
```

Le mode `--batch --silent` désactive le formatage tabulaire habituel de la console MariaDB et produit une sortie brute séparée par tabulations, plus simple à rediriger vers un fichier. L'option d'export CSV native du client (`--fields-terminated-by`) n'étant pas disponible dans cette version du CLI, la conversion tabulation → virgule a été effectuée a posteriori par un appel à `sed`. Cette solution, bien que pragmatique, présente une limite identifiée dès cette étape et traitée lors du nettoyage des données : elle ne distingue pas les virgules de séparation des virgules présentes à l'intérieur d'un champ texte (cas du champ `topic_keywords`).

**Étape 3 — Rapatriement local.** Le fichier CSV obtenu côté serveur a été transféré vers la machine locale de développement par une copie sécurisée par SSH, via le réseau Tailscale :

```bash
scp wassim@100.71.206.63:~/tutor_logs.csv ./tutor_logs.csv
```

### 3.3 Structure de la donnée source

La table `mdl_local_tutor_ia_logs` comporte onze colonnes, qui constituent l'unique source de vérité de toute l'analyse :

| Colonne                 | Description                                                           |
| ----------------------- | --------------------------------------------------------------------- |
| `id`                    | Identifiant unique de la session de conversation                      |
| `firstname`, `lastname` | Identité de l'étudiant                                                |
| `email`                 | Adresse email (identifiant unique secondaire)                         |
| `cours`                 | Intitulé du cours Moodle dans lequel la session a eu lieu             |
| `message_count`         | Nombre de messages échangés au cours de la session                    |
| `topic_keywords`        | Liste de mots-clés extraits des questions posées (séparateur virgule) |
| `tokens_used`           | Nombre de tokens consommés par le LLM pour cette session              |
| `session_duration`      | Durée de la session, en secondes                                      |
| `bonus_tokens`          | Nombre de messages bonus débloqués via le mécanisme de gamification   |
| `date_session`          | Horodatage de la session                                              |

### 3.4 Nettoyage et transformation des données

Le chargement et le nettoyage des données sont centralisés dans le module [data.py](data.py), volontairement isolé du reste de l'application pour que toute évolution du format source n'impacte qu'un seul fichier.

La difficulté principale, déjà identifiée à l'étape d'export, concerne le champ `topic_keywords` : son contenu (une liste de mots-clés séparés par des virgules) utilise le même caractère que le séparateur de colonnes du CSV produit par le pipeline d'extraction. Une ligne brute du fichier ne peut donc pas être découpée naïvement sur la virgule sans fragmenter ce champ en un nombre de morceaux variable d'une ligne à l'autre. La solution retenue exploite une régularité structurelle de la table : les six premières colonnes (`id` à `message_count`) et les quatre dernières (`tokens_used` à `date_session`) ont toujours exactement un champ chacune, alors que `topic_keywords`, placé entre les deux, peut en occuper un nombre variable. La fonction `_parse_csv_row` découpe donc chaque ligne sur la virgule, prélève les six premiers et les quatre derniers champs, et reconstitue le champ `topic_keywords` en réassemblant tout ce qui reste au milieu :

```python
parts = line.rstrip("\n").split(",")
topic_keywords = ",".join(parts[6:-4]).strip()
```

Cette approche, bien que reposant sur une hypothèse de position fixe des colonnes plutôt que sur un parsing CSV générique, s'est révélée robuste sur l'ensemble des données traitées, y compris lorsque les mots-clés contiennent eux-mêmes des apostrophes ou des caractères accentués.

Une fois la table reconstruite, plusieurs transformations dérivées sont appliquées systématiquement :

- conversion du champ `date_session` en type datetime, avec extraction de la date seule, de l'heure, du jour de la semaine et de la semaine calendaire (utilisée pour l'analyse de cohortes) ;
- conversion numérique des colonnes `id`, `message_count`, `tokens_used`, `session_duration`, `bonus_tokens`, avec remplacement des valeurs non convertibles par zéro ;
- calcul d'une durée de session en minutes (`duration_min`), plus lisible que la durée brute en secondes ;
- calcul d'un indicateur booléen `has_bonus` signalant si la session a déclenché le mécanisme de gamification ;
- concatenation du prénom et du nom en un champ `user_full` utilisé comme identifiant d'affichage.

L'ensemble du chargement est mis en cache via le décorateur `@st.cache_data` de Streamlit, ce qui évite de recharger et reparser le CSV à chaque interaction de l'utilisateur avec le tableau de bord.

### 3.5 Architecture logicielle du tableau de bord

Le tableau de bord, développé avec le framework **Streamlit**, a été structuré en modules à responsabilité unique plutôt qu'en un unique script monolithique, afin de faciliter la maintenance et l'évolution de l'outil au fil du projet :

- [data.py](data.py) — chargement et nettoyage des données (décrit ci-dessus) ;
- [sidebar.py](sidebar.py) — gestion de l'ensemble des filtres interactifs (cours, utilisateur, période, statut de gamification, plages de messages/tokens/durée), appliqués au jeu de données avant tout affichage ;
- [charts.py](charts.py) — fonctions de construction des graphiques (Plotly), chacune isolée et réutilisable ;
- [components.py](components.py) — composants d'affichage de plus haut niveau (cartes de KPIs, tableaux, classements, profils individuels) ;
- [analytics.py](analytics.py) — calculs analytiques dérivés (détection de risque de décrochage, score de difficulté par cours, matrice de rétention par cohorte), séparés du reste pour isoler la logique métier des Learning Analytics de la simple restitution visuelle ;
- [app.py](app.py) — point d'entrée de l'application, orchestrant l'ensemble sous forme d'onglets thématiques.

Le tableau de bord s'organise autour de six onglets :

1. **KPIs** — indicateurs agrégés globaux (sessions, messages, tokens, utilisateurs uniques, durée moyenne, taux de gamification) et tableau de synthèse par cours.
2. **Visualisations** — sept graphiques croisant les dimensions cours/temps/comportement : messages et sessions par cours, évolution temporelle de l'activité, distribution des durées de session, nuage de mots-clés, relation tokens/messages avec mise en évidence de la gamification, et heatmap horaire d'activité.
3. **Suivi pédagogique** — un ensemble d'indicateurs orientés action enseignante, détaillés en section 3.6.
4. **Sessions** — table détaillée de l'ensemble des sessions filtrées, exportable visuellement.
5. **Classement** — classement des étudiants selon plusieurs critères (messages, sessions, tokens, durée), avec visualisation des étudiants les plus engagés.
6. **Profils** — vue individuelle par étudiant (cours utilisés, mots-clés récurrents, activité dans le temps).

Chaque graphique est accompagné d'un encart explicatif (« Comment lire ce graphe ? ») rédigé en langage non technique, choix de conception qui répond directement à la contrainte de restitution à un public d'enseignants identifiée en section 1.2.

### 3.6 Indicateurs de Learning Analytics avancés

Au-delà des indicateurs descriptifs de base, trois indicateurs dérivés ont été conçus spécifiquement pour répondre aux objectifs de suivi pédagogique et de détection de difficulté affichés par le projet Estud{IA}nt :

**Détection du risque de décrochage.** Un étudiant ayant déjà construit un usage régulier du tuteur (au moins deux sessions) est signalé comme « à risque » si la durée écoulée depuis sa dernière session dépasse un seuil paramétrable par l'enseignant (14 jours par défaut). Trois niveaux de sévérité (Modéré, Élevé, Critique) sont calculés en comparant la durée d'inactivité au seuil choisi, et l'écart moyen habituel entre les sessions de l'étudiant est affiché en complément pour permettre de juger si l'inactivité observée est anormale au regard de son propre rythme d'usage.

**Score de difficulté par cours.** Pour chaque cours, trois signaux de friction pédagogique sont combinés après normalisation min-max : la durée moyenne des sessions, le nombre moyen de messages échangés par session, et le taux de répétition des mots-clés extraits des questions (une forte proportion de mots-clés récurrents traduisant des questions reposées plusieurs fois sur une notion non assimilée). La moyenne de ces trois signaux normalisés produit un score relatif de 0 à 100, qui permet de classer les cours du jeu de données filtré selon le niveau d'aide qu'ils semblent requérir — un signal utile pour prioriser un accompagnement renforcé sur certains contenus.

**Rétention par cohorte hebdomadaire.** Les étudiants sont regroupés en cohortes selon la semaine de leur première utilisation du tuteur, puis le pourcentage de chaque cohorte encore actif S+1, S+2... semaines plus tard est calculé et restitué sous forme de matrice (heatmap), selon une construction usuelle en analyse de rétention produit. Cet indicateur permet de distinguer un usage ponctuel du tuteur (par exemple à l'approche d'un devoir précis, avec une chute rapide de la rétention) d'une adoption durable de l'outil dans les habitudes de travail des étudiants.

---

## 4. Expérimentations

### 4.1 Données collectées

Le pipeline d'extraction décrit en section 3.2 a été exécuté à plusieurs reprises sur l'instance `moodle-lucas` au fil de l'avancement du projet, à mesure que l'usage du plugin Tutor IA s'est étendu au-delà des seuls comptes de développement. Le jeu de données consolidé au moment de la rédaction de ce rapport comporte **621 sessions** réparties sur **16 utilisateurs**, couvrant une période d'environ neuf mois (septembre 2025 à juin 2026).

L'analyse de ce jeu de données via le tableau de bord fait apparaître les résultats suivants :

- **6 630 messages** échangés au total, pour environ **25,6 millions de tokens** consommés par le modèle de langage — soit une moyenne d'environ 3 860 tokens par message, cohérente avec un modèle qui reformule et contextualise ses réponses à partir du contenu du cours plutôt que de répondre de façon laconique.
- **9 cours** distincts sollicités, avec une activité assez homogène entre eux : _R2.08 – Outils numériques pour les statistiques descriptives_ arrive en tête (897 messages), suivi de _Développement Web – HTML/CSS/JS_ (857), _Réseaux Informatiques_ (823) et _Systèmes d'exploitation Linux_ (779), les cinq autres cours se situant entre 607 et 716 messages.
- Le mécanisme de gamification a été déclenché par l'ensemble des **16 utilisateurs**, pour un total de **2 610 tokens bonus** débloqués, ce qui indique une adoption large du système de quiz bonus sur la durée d'observation.
- La répartition de l'activité entre les 16 utilisateurs et les 9 cours est suffisamment équilibrée pour permettre une lecture différenciée par cours et par étudiant dans les onglets Classement et Profils du tableau de bord, contrairement à une phase de test initiale dominée par des comptes de développement.

Ce volume reste celui d'une **phase de déploiement pilote** plutôt que d'un déploiement à l'échelle de l'ensemble des promotions de l'IUT, ce qui est discuté en section 5.

### 4.2 Robustesse du pipeline et validation des indicateurs avancés

Disposer de neuf mois d'historique a permis de valider en conditions réelles la pertinence des indicateurs avancés présentés en section 3.6, en particulier la rétention par cohorte, qui nécessite plusieurs semaines de données pour produire un résultat interprétable. Les vérifications suivantes ont été effectuées :

- le parsing du champ `topic_keywords` reste robuste face à des mots-clés contenant des caractères accentués et des cas de bord (cellules vides) ;
- le score de difficulté par cours produit un classement différencié et stable entre les cours, avec des écarts de score significatifs (par exemple 90,0 pour le cours le plus en difficulté contre 57,2 pour un cours plus en retrait dans le classement) ;
- la matrice de rétention par cohorte se construit correctement sur l'historique complet et fait apparaître des taux de rétention décroissants au fil des semaines, conformes au comportement attendu d'un outil d'usage non obligatoire ;
- l'ensemble des graphiques et filtres du tableau de bord répond correctement à ce volume de données sans dégradation de performance perceptible côté interface, ce qui laisse présager une bonne tenue en charge si le déploiement s'étend à davantage de promotions.

### 4.3 Restitution et ergonomie

Le tableau de bord a été testé de façon itérative tout au long du développement, par exécution locale via `streamlit run app.py` et vérification visuelle de chaque nouvel onglet ou graphique ajouté. Une attention particulière a été portée à la cohérence visuelle (thème sombre, codes couleurs cohérents entre les graphiques d'un même onglet) et à l'autonomie de lecture (chaque graphique est accompagné d'un texte explicatif permettant à un enseignant non familier des outils de visualisation de données d'interpréter correctement ce qu'il observe).

---

## 5. Conclusion

Ce projet a constitué une mise en situation complète d'un cycle de traitement de données, de l'accès à une infrastructure distante jusqu'à la restitution d'un outil d'aide à la décision pour un public non technique, en passant par toutes les étapes intermédiaires de nettoyage, de modélisation d'indicateurs et de mise en forme.

**Bilan sur la conduite du projet.** La principale difficulté rencontrée n'a pas été d'ordre technique mais d'ordre temporel et organisationnel : le développement du plugin Tutor IA et de l'infrastructure d'inférence par les autres membres de l'équipe a naturellement précédé la possibilité de produire des données réelles exploitables, ce qui a mécaniquement retardé le moment où la partie Data a pu travailler sur des données représentatives d'un usage étudiant effectif. Cette dépendance séquentielle entre les sous-équipes du projet — l'analyse de données ne pouvant commencer sérieusement qu'une fois l'instrumentation en place et un usage minimal généré — est une leçon d'organisation de projet transversale qui aurait pu être anticipée plus tôt, par exemple en générant dès le démarrage du projet un jeu de données simulé réaliste pour développer et valider le pipeline d'analyse en parallèle du développement du plugin, plutôt qu'en attendant les premières données réelles pour commencer ce travail. C'est d'ailleurs la démarche qui a été adoptée a posteriori (section 4.2), mais qui aurait gagné à être mise en place plus tôt dans le calendrier du projet.

**Limites identifiées.**

- Le volume de données disponible (621 sessions, 16 utilisateurs sur neuf mois) correspond à une phase de déploiement pilote et reste en deçà de ce qu'un déploiement à l'échelle de plusieurs promotions de l'IUT produirait : les conclusions sur l'effet de la gamification sur l'engagement ou sur la pertinence opérationnelle des indicateurs de risque de décrochage et de rétention par cohorte restent donc à confirmer sur un historique plus long et une population étudiante plus large.
- Le pipeline d'extraction reste manuel (connexion SSH, commande d'export, transfert `scp`), ce qui est acceptable pour une phase de test mais ne serait pas soutenable pour un suivi continu en production.
- Le score de difficulté par cours, bien que reposant sur des signaux pertinents, demeure un indicateur heuristique fondé sur une normalisation relative entre les cours du jeu de données filtré : son interprétation absolue (qu'est-ce qu'un score de 60 signifie en soi ?) reste limitée, et une validation par confrontation avec l'avis des enseignants des cours concernés serait nécessaire avant un déploiement opérationnel.
- L'extraction par conversion tabulation/virgule via `sed`, bien que fonctionnelle sur les données observées, demeure fragile par construction face à des cas non rencontrés à ce jour (par exemple un mot-clé contenant lui-même une tabulation).

**Ce qu'avec l'expérience de ce projet j'aborderais différemment.** Je mettrais en place, dès le lancement du projet et indépendamment de l'avancement de la partie IA, un export automatisé et planifié des données (par exemple via une tâche cron exécutant le pipeline d'extraction à intervalle régulier, plutôt qu'une extraction manuelle ponctuelle), ce qui aurait permis de disposer d'un historique de données réelles plus long au moment de la rédaction de ce rapport. Je privilégierais également, dès la définition du schéma de la table de logs, une recommandation auprès des développeurs du plugin pour un format d'export structuré natif (JSON ou CSV correctement échappé) plutôt qu'un export texte brut nécessitant une étape de parsing artisanal — cette dernière ayant représenté une part disproportionnée du temps de développement au regard de sa complexité fonctionnelle réelle.

**Perspectives.** Une fois l'instance `moodle-lucas` utilisée par une cohorte réelle d'étudiants sur une période significative, le tableau de bord développé permettra une exploitation effective des indicateurs de suivi pédagogique conçus dans ce travail. Des perspectives d'enrichissement incluent l'automatisation complète du pipeline d'extraction, l'ajout d'une fonctionnalité d'export des vues filtrées (CSV/Excel) pour un partage direct avec les enseignants concernés, et — sous réserve d'un volume de données suffisant — l'exploration de modèles prédictifs de décrochage plus formels que l'heuristique actuelle basée sur des seuils.

---

## 6. Annexes

### Annexe A — Liste des colonnes de la table source

```
mdl_local_tutor_ia_logs
├── id                 : identifiant de session (entier)
├── firstname          : prénom de l'étudiant
├── lastname            : nom de l'étudiant
├── email                : adresse email
├── cours                 : intitulé du cours Moodle
├── message_count          : nombre de messages échangés
├── topic_keywords          : mots-clés extraits des questions (liste séparée par virgules)
├── tokens_used              : tokens consommés par le LLM
├── session_duration          : durée de la session (secondes)
├── bonus_tokens                : tokens bonus débloqués (gamification)
└── date_session                 : horodatage de la session
```

### Annexe B — Commandes du pipeline d'extraction

```bash
# 1. Récupération des identifiants de connexion à la base
docker exec moodle-db-lucas env

# 2. Extraction et conversion tabulation -> virgule
docker exec moodle-db-lucas mariadb -u bn_moodle -pmoodle_lucas_2026 bitnami_moodle \
  --batch --silent \
  -e "SELECT * FROM mdl_local_tutor_ia_logs;" \
  | sed 's/\t/,/g' > tutor_logs.csv

# 3. Rapatriement local via SSH/Tailscale
scp wassim@100.71.206.63:~/tutor_logs.csv ./tutor_logs.csv

# 4. Lancement du tableau de bord
streamlit run app.py
```

### Annexe C — Architecture des modules du tableau de bord

```
app.py            → point d'entrée, orchestration des onglets
├── data.py        → chargement et nettoyage du CSV
├── sidebar.py       → filtres interactifs
├── charts.py          → fonctions de génération des graphiques Plotly
├── components.py        → composants d'affichage (KPIs, tableaux, classements, profils)
└── analytics.py            → indicateurs avancés (décrochage, difficulté, rétention)
```

### Annexe D — Indicateurs clés calculés sur les données collectées (621 sessions, 16 utilisateurs)

| Indicateur                                   | Valeur                                                                      |
| -------------------------------------------- | --------------------------------------------------------------------------- |
| Sessions totales                             | 621                                                                         |
| Utilisateurs uniques                         | 16                                                                          |
| Messages totaux                              | 6 630                                                                       |
| Tokens consommés                             | ≈ 25 600 000                                                                |
| Tokens bonus débloqués                       | 2 610                                                                       |
| Utilisateurs ayant déclenché la gamification | 16 / 16                                                                     |
| Cours distincts sollicités                   | 9                                                                           |
| Cours le plus actif                          | R2.08 – Outils numériques pour les statistiques descriptives (897 messages) |
| Période couverte                             | 01/09/2025 – 02/06/2026                                                     |

---

## 7. Bibliographie

1. Siemens, G., & Long, P. (2011). _Penetrating the Fog: Analytics in Learning and Education_. EDUCAUSE Review.
2. VanLehn, K. (2011). _The Relative Effectiveness of Human Tutoring, Intelligent Tutoring Systems, and Other Tutoring Systems_. Educational Psychologist, 46(4).
3. Kasneci, E. et al. (2023). _ChatGPT for Good? On Opportunities and Challenges of Large Language Models for Education_. Learning and Individual Differences, 103.
4. Kwon, W. et al. (2023). _Efficient Memory Management for Large Language Model Serving with PagedAttention_. Proceedings of the 29th ACM SIGOPS Symposium on Operating Systems Principles (article de référence pour vLLM, framework d'inférence utilisé pour le déploiement du modèle Gemma 4B).
5. Documentation officielle Moodle — _Logging API & Report_, docs.moodle.org.
6. Documentation officielle Streamlit — _Streamlit Documentation_, docs.streamlit.io.
7. Documentation officielle Tailscale — _How Tailscale works_, tailscale.com/kb.
8. Documentation officielle pandas — _pandas documentation_, pandas.pydata.org.
