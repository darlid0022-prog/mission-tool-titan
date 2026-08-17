# Titan Mission Tool — Roadmap "aller au maximum"

Ce document est le plan détaillé pour pousser l'outil le plus loin possible :
destination multi-planète (comme l'Excel d'origine), meilleure interface,
meilleure visualisation 3D, puis profondeur d'ingénierie. Chaque phase indique
ce qui existe déjà, ce qu'il faut construire, le risque, et quel outil
(Claude Code / Codex / IA VS Code) utilise le mieux le budget de tokens.

État de référence au moment de l'écriture : `main`, dernier commit
"mission-control dark theme, persistent scorecard, tab-based navigation",
180 tests, remote GitHub à jour (`main` + `demo-ready`).

Mise à jour du 17 août 2026 : le catalogue d'instruments structuré, la CI
GitHub Actions et les phases 1.1/1.3 (planètes majeures et lunes résolubles)
sont implémentés. La compatibilité numérique Terre → Saturne → Titan est
préservée et la suite locale compte désormais 199 tests. La prochaine étape
active est la phase 1.4, généralisation de l'arrivée vers l'orbite d'attente.

---

## Principe directeur : comment prioriser

L'ordre ci-dessous est pensé pour que chaque phase soit **utilisable seule**
(rien de cassé si on s'arrête après une phase) et pour que les phases qui
rapportent le plus par rapport à leur coût passent en premier :

1. Multi-destination (le plus demandé, et le solveur Lambert le supporte déjà à 90%)
2. Interface (rendre le multi-destination réellement utilisable)
3. Visualisation 3D (le rendre impressionnant)
4. Profondeur d'ingénierie (sous-systèmes, catalogue d'instruments rempli)
5. Qualité / déploiement public

Répartition d'outils par type de tâche (cf. notre discussion sur les
crédits) :

| Type de tâche | Outil recommandé | Pourquoi |
|---|---|---|
| Ajouter un corps céleste à `bodies.py` (mécanique, répétitif, pattern déjà présent 3x) | **IA VS Code (Copilot inline)** | Pattern-matching pur sur du code existant, quasi gratuit |
| Généraliser `saturn_staging.py` → `arrival_staging.py` (refactor paramétrique avec risque de régression) | **Codex** en petites étapes bien cadrées, un module à la fois | Tâche isolée, spec claire, diff contenu |
| Recomposer `full_mission.py` / `app.py` pour brancher plusieurs types de destination (orchestration multi-fichiers) | **Claude Code**, session ciblée par sous-tâche | Demande de comprendre l'architecture existante en entier |
| Design de l'interface / choix de palette / specs de visualisation | **Claude Code** (ce plan + validation avec le skill dataviz) | Nécessite la cohérence globale du design system |
| Rédaction de tests | **Codex** ou IA VS Code selon la complexité du cas testé | Souvent mécanique une fois le comportement attendu connu |

Règle simple : si tu peux décrire la tâche en une phrase avec un fichier
cible précis → Codex ou VS Code AI. Si la tâche demande de comprendre
comment 4 fichiers interagissent avant de toucher au premier → Claude Code.

---

## Phase 1 — Destinations multi-planètes (la demande explicite)

### Ce qui existe déjà (bonne nouvelle : la base est réutilisable à ~90%)

- `mission/leg_solver.py::compute_lambert_leg` est **déjà générique** : il
  prend n'importe quels `origin`/`destination` résolus via `resolve_body()`
  et ne code en dur ni Terre ni Saturne. Rien à changer ici.
- `mission/bodies.py` n'enregistre que 3 corps (`earth`, `saturn`, `titan`)
  dans `SUPPORTED_BODIES`. C'est le vrai goulot d'étranglement.
- `mission/saturn_staging.py` et `mission/moon_transfer.py`
  (Saturn → Titan) codent en dur Saturne/Titan alors que la physique
  (capture hyperbolique → orbite d'attente, transfert de Hohmann
  planète → lune) est générique par nature.
- Le fichier Excel d'origine contient déjà toutes les constantes physiques
  nécessaires (masse, rayon, périhélie/aphélie, vitesse orbitale pour
  chaque planète ; masse, rayon, périapse/apoapse, vitesse orbitale pour
  chaque lune : Phobos, Deimos, Io, Europa, Ganymède, Callisto, Titan). Ce
  sont des données publiques déjà présentes dans le projet — pas besoin de
  les re-chercher, juste de les porter en Python.

### Ce qu'il faut construire

**1.1 — Étendre `bodies.py` aux planètes majeures**
PyKEP expose `pk.udpla.jpl_lp(name)` pour Mercure, Vénus, Mars, Jupiter,
Uranus, Neptune (et Pluton) — même mécanisme que Terre/Saturne actuels.
Ajouter une entrée `SUPPORTED_BODIES` par planète (~6 lignes de pattern
répété par planète). Risque : très faible, code déjà 3x dupliqué comme
modèle.

**1.2 — Ajouter Cérès et Pluton comme corps "orbite keplérienne artificielle"**
`jpl_lp` ne couvre pas forcément les planètes naines avec la précision
voulue (à vérifier à l'implémentation) — si absent, les traiter comme
Titan aujourd'hui : orbite héliocentrique keplérienne construite à partir
des périhélie/aphélie déjà présents dans l'Excel, sans éphéméride PyKEP
native, `supports_lambert=False` documenté comme tel.

**1.3 — Ajouter les lunes comme corps "orbite artificielle autour de leur planète"**
Exactement le pattern déjà utilisé pour Titan : Phobos, Deimos (autour de
Mars), Io, Europa, Ganymède, Callisto (autour de Jupiter). Chaque lune a
son `mu_self` (GM, constante publique) et son rayon orbital moyen autour
de sa planète — déjà dans l'Excel.

**1.4 — Généraliser le module de capture/mise en orbite d'attente**
Transformer `saturn_staging.py::compute_saturn_arrival_to_staging` en une
version paramétrique `arrival_staging.py::compute_arrival_to_staging(mu_parent, ...)`
qui accepte n'importe quel corps parent. Les contraintes d'anneaux
(D-ring, F-ring, E-ring) restent une option activée uniquement pour Saturne
(et éventuellement Jupiter/Uranus/Neptune si on veut, sinon ignorée) —
pas de simplification malhonnête, juste une fonctionnalité optionnelle.
Garder `saturn_staging.py` comme fine façade legacy autour du nouveau
module générique (même pattern que le refactor `bodies.py`/`leg_solver.py`
déjà fait dans le projet — "l'app n'a jamais eu besoin d'être modifiée").

**1.5 — Généraliser le transfert planète → lune**
Transformer `moon_transfer.py`/`compute_saturn_titan_transfer` en
`parent_moon_transfer.py::compute_parent_to_moon_transfer(mu_parent, moon_orbit_radius_m, mu_moon, moon_radius_m, ...)`.
Même logique (Hohmann circulaire coplanaire), juste paramétrée.

**1.6 — Brancher dans `full_mission.py` et `app.py`**
- `capabilities.py` : distinguer `PLANET_DESTINATIONS` (arrivée directe,
  un seul leg) de `MOON_DESTINATIONS` (deux legs : interplanétaire +
  transfert vers la lune, comme Titan aujourd'hui).
- Le sélecteur de destination dans l'UI devient un vrai choix parmi toutes
  les planètes/lunes de l'Excel, avec une liste déroulante à deux niveaux
  (planète, puis lune optionnelle) plutôt qu'un unique "Saturn" figé.
- Les sections qui ne sont physiquement valables que pour Titan (EDL
  atmosphérique, contraintes d'anneaux) s'affichent **seulement** quand la
  destination le permet — jamais une fonctionnalité fictive présentée
  comme active pour une destination où elle ne s'applique pas.

**1.7 — Ce qui reste explicitement hors scope de cette phase (à documenter, pas à cacher)**
- Atterrissage/EDL réel pour les corps sans atmosphère (Phobos, Deimos, Io,
  Europa, Ganymède, Callisto) : ce serait une descente propulsive pure, pas
  un EDL atmosphérique — modèle différent, à faire en Phase 4.
  Atmosphères réelles (Mars, Vénus) mériteraient chacune leur propre étude
  physique avant d'être branchées — ne pas réutiliser le modèle Titan tel
  quel par facilité.
- Assistances gravitationnelles multi-corps sur la route (le démonstrateur
  actuel Venus/Terre/Jupiter reste un module isolé, pas encore chaîné dans
  le budget dv connecté).

### Tests à écrire (avant tout commit, comme les 180 existants)

- Résolution de chaque nouveau corps (`test_celestial_body_resolution.py`
  étendu).
- Un test Lambert par nouvelle planète directe (Terre → Mercure, Terre →
  Mars, etc.), validé contre une référence connue (comme le fut Terre →
  Mars puis Terre → Saturne).
- Un test de transfert planète → lune par nouvelle lune.
- Régression : Terre → Saturne → Titan doit rester bit-à-bit identique
  après le refactor paramétrique (c'est le test le plus important — il
  prouve que la généralisation n'a rien changé au cas déjà validé).

---

## Phase 2 — Meilleure interface

### Diagnostic de l'existant

`app.py` est un unique fichier Streamlit d'environ 850 lignes avec 7 onglets.
Ça fonctionne, mais ça va devenir difficile à faire évoluer une fois le
multi-destination branché (chaque destination ajoute des sections
conditionnelles).

### Actions

**2.1 — Passer en application multi-page Streamlit** (`st.navigation` /
`st.Page`, disponible depuis Streamlit 1.36+, déjà en 1.61 ici) :
- `pages/mission_setup.py` (destination, fenêtre de lancement, propulsion,
  instruments)
- `pages/trajectory_3d.py`
- `pages/saturn_system_studies.py` → généralisé en
  `pages/moon_system_studies.py` quand la destination est une lune
- `pages/feasibility.py`
- `pages/optimization.py` (Pareto)
- `pages/gravity_assists.py`
Chaque page importe la logique métier de `mission/` sans dupliquer de
calcul — seul `app.py` explose en pages, pas la logique.

**2.2 — Système de design cohérent**
Appliquer les principes du skill `dataviz` (déjà utilisé pour ce plan) :
- Couleurs catégorielles (une par phase de mission : croisière Terre→Saturne,
  arrivée/mise en orbite, transfert vers la lune, EDL) assignées dans un
  **ordre fixe**, jamais recalculées dynamiquement — validées avec
  `scripts/validate_palette.js` pour être sûres/dur d'œil et lisibles en
  mode sombre (le thème actuel est déjà sombre "mission-control" : à
  revalider spécifiquement contre le fond sombre, pas juste réutiliser la
  palette claire).
- Le statut de faisabilité (single-stage feasible / infeasible) doit
  utiliser une **palette de statut réservée** (vert/orange/rouge), jamais
  une des couleurs catégorielles de phase — actuellement c'est un simple
  texte d'avertissement, à faire évoluer en indicateur visuel clair avec
  icône + libellé (jamais couleur seule).
- Légende toujours présente dès qu'il y a ≥ 2 séries dans un graphique,
  labels directs sélectifs plutôt qu'une valeur sur chaque point.

**2.3 — Page d'accueil / résumé de mission**
Remplacer l'expander "Planned capabilities" par une vraie page d'accueil :
carte de la destination choisie, résumé des hypothèses actives, statut de
chaque phase (modélisée / isolée / non modélisée) en un coup d'œil.

**2.4 — Export et partage**
- Export du rapport de mission (résumé dv/masse/durée) en PDF ou image.
- État de la mission encodé dans l'URL (query params Streamlit) pour
  partager une configuration précise par lien.

**2.5 — Accessibilité**
- Contraste vérifié en mode sombre (validator du skill dataviz, mode
  `--mode dark` avec la vraie couleur de fond du thème actuel).
- Table de données toujours disponible en alternative à chaque graphique
  (pour lecteurs d'écran / vérification manuelle).

---

## Phase 3 — Meilleure visualisation 3D

### Diagnostic de l'existant

Scène 3D Plotly avec vues héliocentrique et saturnienne séparées, timeline
animée par phase, corps non à l'échelle (assumé et documenté).

### Actions, du plus rentable au plus ambitieux

**3.1 — Porkchop plot (diagramme de fenêtre de lancement)**
C'est l'outil de référence en conception de mission (date de départ ×
date/durée d'arrivée, coloré par dv ou C3) — absent aujourd'hui alors que
le Pareto front actuel s'en approche déjà conceptuellement. Un vrai
porkchop plot par couple origine/destination donnerait une vraie valeur
d'aide à la décision, en plus d'être visuellement le graphique le plus
identifiable du domaine. Respecter la règle "un seul axe" du skill
dataviz : dv en couleur (séquentiel, un seul hue clair→foncé), pas un
double axe dv/C3.

**3.2 — Préréglages de caméra**
Vue "vue de dessus du plan écliptique", vue "approche finale", vue
"système de la lune cible" — au lieu de laisser l'utilisateur chercher le
bon angle à chaque fois.

**3.3 — Bascule échelle réelle / échelle lisible**
Actuellement les corps ne sont pas à l'échelle (nécessaire pour que les
lunes soient visibles). Ajouter une bascule explicite "échelle réelle"
(avec avertissement que les lunes deviennent invisibles) pour ceux qui
veulent voir la vraie proportion — transparence plutôt que choix imposé.

**3.4 — Vue synchronisée multi-corps**
Pour une destination-lune, afficher planète + orbite de la lune + trajet
du vaisseau dans un même repère au lieu de deux panneaux séparés, avec un
zoom progressif animé au moment de l'arrivée (transition douce plutôt que
changement brutal de panneau).

**3.5 — Info-bulles enrichies**
Au survol du curseur sur la trajectoire : temps écoulé, dv dépensé à ce
point, distance au Soleil et à la destination, phase actuelle — cohérent
avec la règle "hover layer par défaut" du skill dataviz.

**3.6 — (Optionnel, gros chantier) Sortir de Plotly si besoin**
Si les performances deviennent un problème avec des scènes plus riches
(multi-corps, multi-lunes), envisager un composant Streamlit personnalisé
en three.js/deck.gl. À ne considérer **qu'après** avoir buté sur une vraie
limite de Plotly — ne pas migrer par anticipation, c'est le chantier le
plus cher en tokens et en risque de régression de tout ce plan.

---

## Phase 4 — Profondeur d'ingénierie (rejoint l'Excel original)

Une fois le multi-destination et l'interface solides, revenir aux sujets
laissés de côté depuis le début :

**4.1 — Catalogue d'instruments : remplir les vraies valeurs**
Le catalogue construit aujourd'hui (`mission/payload_catalog.py`) n'a que
des emplacements nommés à 0 kg/0 W. Compléter avec des masses/puissances
réelles sourcées nécessite soit que tu fournisses des références
traçables, soit une recherche ciblée mission par mission (Cassini, JUICE,
Dragonfly...) — budget de recherche à prévoir séparément, comme discuté.

**4.2 — Dimensionnement détaillé des sous-systèmes**
Actuellement le modèle de masse est paramétrique (ratios Hesperos par
rapport au payload). Ajouter un mode "dimensionnement détaillé" optionnel
qui reprend la logique des feuilles Excel jamais remplies (Data Handling,
Communication, Thermal, Pointing Control, Propulsion, Structure, Power
Budget) — avec un vrai catalogue de composants (transpondeurs, roues de
réaction, etc.), au choix de l'utilisateur entre "rapide/paramétrique" et
"détaillé/composant par composant".

**4.3 — Atterrissage réel (au-delà de l'EDL Titan isolé)**
Descente propulsive pour les corps sans atmosphère, atterrissage complet
(pas seulement l'interface atmosphérique) pour Titan.

---

## Phase 5 — Qualité et déploiement

**5.1 — CI GitHub Actions**
Le critère de réussite original ("la CI exécute automatiquement les
contrôles") n'est pas encore atteint à ma connaissance (pas de dossier
`.github/workflows` détecté). Ajouter un workflow qui lance `make check`
sur chaque push/PR — filet de sécurité peu coûteux, à faire tôt plutôt
que tard.

**5.2 — Déploiement public**
Explicitement exclu jusqu'ici. Une fois les phases 1-3 stables :
Streamlit Community Cloud (gratuit, le plus simple) ou conteneur
déployé ailleurs si des dépendances (PyKEP) posent problème sur la
plateforme gratuite — à valider en premier avant de choisir.

**5.3 — Couverture de tests et audit de dépendances**
`quality.sh` fait déjà tourner `pip-audit` et `detect-secrets` — à
intégrer dans la CI plutôt que manuel uniquement.

---

## Résumé exécutif : par où commencer concrètement

1. **Phase 1.1-1.3** (ajout des corps) : petites tâches mécaniques,
   IA VS Code ou Codex, quasi gratuit, haute valeur immédiate.
2. **Phase 1.4-1.6** (généralisation staging + transfert + branchement) :
   Claude Code, en sessions ciblées module par module, avec test de
   non-régression Terre→Saturne→Titan à chaque étape.
3. **Phase 5.1** (CI) : à glisser dès que possible, coût minimal,
   protège tout le reste du travail.
4. **Phase 2** (interface) une fois 1 stable, sinon on redesigne une
   interface pour une seule destination et on la refait pour rien.
5. **Phase 3** (3D) en parallèle ou juste après 2.
6. **Phase 4** quand tu as le temps/les sources pour les vraies données
   d'instruments et de sous-systèmes — c'est la phase la plus dépendante
   de recherche externe, donc la plus coûteuse en tokens si on la fait
   trop tôt sans données solides.
7. **Phase 5.2** (déploiement public) en dernier, une fois que tu es
   content du résultat.
