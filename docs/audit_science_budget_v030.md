<!-- title: Science & Budget Separation Audit -->

# Audit scientifique et logiciel — v0.3.0

**Branche** : `audit/science-budget-v030` · **Base** : `main` @ `07d9925` · **Portée** : séparation énergie de lancement / delta-v embarqué / total cinématique connecté, sur l'ensemble de la chaîne Terre → Saturne (orbite à rayon de Titan).

Aucun fichier n'a été modifié pour produire cet audit. Toutes les valeurs recalculées ci-dessous ont été obtenues en important et en appelant directement les fonctions du dépôt (aucune reformulation manuelle des formules).

---

## 0. Contexte du dépôt

- Aucun `AGENTS.md` ni `README.md` à la racine (confirmé absent, comme lors des audits précédents de ce projet).
- Document faisant autorité sur le modèle physique connecté : `docs/connected_first_order_model.md`.
- Arbre Git propre avant audit ; 440 tests passent (`python -m pytest -q`, voir §11).
- Le modèle « connecté » actuel remplace un ancien enchaînement (capture à 62 330 km → orbite de stationnement à 600 000 km → départ vers Titan → capture titanocentrique à 1 500 km d'altitude). Ce remplacement est documenté comme volontaire dans `docs/connected_first_order_model.md` (« *replaces the former connected-budget sequence…* ») et dans `mission/dv_budget.py` (« *Propulsive mission terms with the obsolete Saturn capture removed* »).

---

## 1. Localisation de chaque valeur de la baseline

| Valeur baseline | Fichier : ligne | Fonction / constante | Formule |
|---|---|---|---|
| Périapse de capture 150 000 km | `mission/constants.py:44` | `NOMINAL_SATURN_PERIAPSIS_RADIUS_M = 150_000_000.0` | constante, mesurée depuis le centre de Saturne |
| Référence anneau F ≈ 140 180 km | `mission/constants.py:43` | `F_RING_REFERENCE_RADIUS_M = 140_180_000.0` | constante (référence Cassini) |
| Apoapse / rayon orbital moyen de Titan 1 221 870 km | `mission/constants.py:34` | `TITAN_MEAN_ORBIT_RADIUS_M = 1_221_870_000.0` | constante |
| Circularisation saturnocentrique à ce rayon | `mission/connected_physics.py:134-198` | `compute_saturn_capture_to_titan_orbit()` | `v_circ = sqrt(mu/r_apo)`, `Δv_circ = v_circ - v_apo,ellipse` |
| v∞ Terre Lambert ≈ 10 432,306 m/s | `mission/launch_search_ephemeris.py:69-136` | `solve_earth_saturn_lambert()` → `earth_v_infinity_m_s` | `‖v_transfer,depart − v_Terre‖` (Lambert PyKEP, éphémérides JPL low-precision) |
| v∞ Saturne Lambert ≈ 6 490,745 m/s | idem | `saturn_v_infinity_m_s` | `‖v_transfer,arr − v_Saturne‖` |
| Injection terrestre ≈ 7 381,480 m/s | `mission/physics.py:45-61` | `delta_v_injection(v_inf, mu, r)` | `sqrt(v_inf² + 2μ/r) − sqrt(μ/r)`, `r` = rayon Terre + 250 km LEO |
| Capture Saturne ≈ 2 182,991 m/s | `mission/connected_physics.py:171` | `capture_delta_v = v_p,hyperbole − v_p,ellipse` | vis-viva à la même radiale (150 000 km) |
| Circularisation ≈ 2 966,182 m/s | `mission/connected_physics.py:172` | `circularisation_delta_v = v_circ − v_apo,ellipse` | vis-viva à la même radiale (1 221 870 km) |
| Total connecté ≈ 12 530,653 m/s | `mission/dv_budget.py:24-26` | `MissionDeltaVBudget.total_m_s` | somme exacte des 4 postes (voir §4) |
| Vol interplanétaire 2 856 j | Lambert (`departure_mjd2000`/`arrival_mjd2000` de la jambe Terre→Saturne) | — | `arrival_mjd2000 − departure_mjd2000` |
| Scénario complet ≈ 2 859,354 j | `mission/connected_physics.py:196` (`time_of_flight_s`), agrégé dans `app_services.py` (`mission_duration_days`) | — | TOF interplanétaire + temps périapse→apoapse de l'ellipse de capture |

Toutes les valeurs de la baseline ont été **recalculées indépendamment** (script Python appelant directement ces fonctions) et correspondent exactement aux chiffres fournis par la baseline (voir §3 et §9 pour le détail des recalculs).

---

## 2. La baseline emploie-t-elle les véritables états Lambert ?

**Oui, confirmé par trois voies indépendantes :**

1. **Lecture du code d'assemblage.** `mission/full_mission.py:203-263`, `compute_earth_saturn_titan_mission()` :
   ```python
   arrival_v_infinity = earth_saturn_trajectory.v_inf_arrival   # ligne 228, jambe Lambert validée
   ...
   connected_first_order=compute_connected_first_order_chain(
       arrival_v_infinity_m_s=arrival_v_infinity,               # ligne 260 — jamais None ici
       ...
   )
   ```
   Le v∞ analytique de Hohmann (`compute_earth_saturn_hohmann()`, utilisé seulement quand `arrival_v_infinity_m_s is None`) n'est **jamais** invoqué par ce chemin d'appel — il ne sert que de référence déterministe autonome (voir `docs/connected_first_order_model.md`) et aux tests de non-régression.

2. **Recalcul indépendant.** En appelant `mission.launch_search_ephemeris.solve_earth_saturn_lambert(9681.181818181818, 12537.181818181829, 16)` (un second solveur Lambert du dépôt, indépendant de `trajectory.py`) :
   ```
   earth_v_infinity_m_s  = 10432.306468285753   (baseline : ≈10 432,306)
   saturn_v_infinity_m_s = 6490.744714263189    (baseline : ≈6 490,745)
   ```
   Les deux solveurs Lambert du dépôt (`trajectory.py` et `mission/launch_search_ephemeris.py`) convergent bit-pour-bit sur ces époques — aucune divergence.

3. **Test de régression existant.** `tests/test_connected_physics.py::test_lambert_and_baseline_paths_share_identical_saturn_burns` (ligne 106) prouve que le chemin « v∞ daté (Lambert) » et un appel direct à `compute_saturn_capture_to_titan_orbit()` avec le même v∞ produisent des objets **strictement identiques** (`assertEqual` sur les dataclasses complètes) — la même physique de capture est réutilisée, seule la source du v∞ change.

---

## 3. C3 recalculé à partir du v∞ actif

`C3 = v∞²`. Formule identique à celle déjà codée dans `mission/launch_search.py:120` (`c3_m2_s2=transfer.earth_v_infinity_m_s**2`), appliquée ici au v∞ Terre actif de la baseline :

```
v∞ = 10 432.306468285753 m/s
C3 = v∞²  = 108 833 018.248 m²/s²
   = 108.833 km²/s²
```

**Constat** : ce C3 (108,83 km²/s²) n'est **affiché nulle part sur la page Mission setup / le scorecard baseline** — la métrique C3 n'existe que sur la page *Launch windows*, pour les candidats de recherche (`pages/launch_windows.py:245`). C'est une lacune de complétude (pas une erreur physique) : la baseline calcule bien un v∞ actif exploitable, mais son énergie C3 n'est jamais restituée à l'utilisateur sur la page où le scénario actif est affiché. Voir recommandation R1.

---

## 4. Cartographie de tous les totaux delta-v et ratios de masse

### 4.1 Totaux delta-v (tous les points d'entrée trouvés)

| Site | Fichier : ligne | Composition du total |
|---|---|---|
| Budget connecté (baseline / Lambert daté) | `app_services.py:617-631` → `mission/dv_budget.py:50-94` | injection Terre + DSM/fly-by (0) + capture (150 000 km) + circularisation (1 221 870 km) |
| Historique Cassini | `app_services.py:543-551` | injection Terre (v∞ VVEJGA réel) + burn SOI réel ; DSM/fly-by, staging, transfert Titan, capture Titan explicitement à 0 |
| Planète seule (pas de lune) | `app_services.py:573-580` | injection Terre + DSM/fly-by ; tous les termes Saturne/Titan à 0 |
| Front de Pareto | `mission/pareto.py:124-205` | `earth_departure_v_infinity_m_s` + `saturn_arrival_v_infinity_m_s` par point Lambert, agrégés via le même budget connecté |
| Candidat *Launch windows* | `launch_window_engine_adapter.py` (`scenario_to_candidate`) | `delta_v_departure_m_s + delta_v_capture_m_s + delta_v_titan_circularization_m_s` — vérifié égal à `total_delta_v_m_s` par construction (`mission/launch_search_models.py` : *"total_delta_v_m_s must equal the exact manoeuvre sum"*) |

### 4.2 Ratios de masse (tous les points d'entrée trouvés)

| Site | Fichier : ligne | `dv_total` injecté |
|---|---|---|
| Scorecard connecté | `app_services.py:632` | total connecté complet (4 postes) |
| Scorecard Cassini | `app_services.py:552` | injection + SOI |
| Scorecard planète seule | `app_services.py:583` | injection + DSM/fly-by |
| Front de Pareto (`wet_mass_kg` par point) | `mission/pareto.py:193` | total connecté complet, par point |
| Scorecard candidat *Launch windows* actif | `pages/mission_setup.py:288` | `candidate.delta_v_total_m_s` (total complet du candidat) |
| Étude de faisabilité mono-étage | `app_services.py:644-648` → `mission/feasibility_check.py:33` | `dv_total` (même variable que le scorecard — total complet) |

**Constat des 6 sites** : **tous** utilisent un total complet (jamais un sous-total partiel) pour calculer `exp(dv/(Isp·g₀))`. Aucune contamination croisée trouvée. Voir cependant §9 pour un cas où un sous-total partiel *pourrait* produire un chiffre trompeur s'il était calculé hors de ces chemins.

---

## 5. L'injection est-elle traitée comme une dépense du véhicule ?

Oui, systématiquement, et c'est correct : `delta_v_injection()` (`mission/physics.py:45`) est appelée pour **chaque** branche (connectée, Cassini, planète seule) et son résultat est le **premier poste** additionné dans chaque `MissionDeltaVBudget`/budget équivalent avant le calcul du ratio de masse (`app_services.py:552`, `583`, `632`). Aucun site trouvé ne calcule un ratio de masse en excluant silencieusement ce poste — sauf le cas reconstitué en §9, qui n'existe dans aucun fichier du dépôt.

---

## 6-7. Recherche des valeurs legacy (62 330 / 600 000 / 1 500 km) et non-contamination du budget connecté

**Sites où ces valeurs apparaissent** (hors tests) :

| Constante | Fichier : ligne | Rôle |
|---|---|---|
| `62_330.0` | `app_services.py:327`, `pages/mission_setup.py:144` | Rayon de périapse **legacy**, alimente uniquement `MissionSetupInputs.saturn_periapsis_radius_km` |
| `600_000.0` | `app_services.py:328`, `pages/mission_setup.py:145` | Rayon de mise en orbite **legacy**, alimente uniquement `saturn_staging_radius_km` |
| `1_500.0` | `app_services.py:329`, `pages/mission_setup.py:146` | Altitude de capture Titan **legacy**, alimente uniquement `titan_capture_altitude_km` |

Ces trois champs ne sont plus éditables dans l'interface (commentaire en clair, `pages/mission_setup.py:125-129` : *« Legacy studies remain inspectable on Saturn & Titan studies, but are no longer editable mission inputs and never feed the connected budget »*) et ne servent qu'à produire `staging_result`/`titan_transfer` — les études isolées affichées sur la page *Saturn & Titan studies*.

**Preuve de non-contamination** — `mission/dv_budget.py:50-94`, `compose_complete_dv_budget()` :

```python
def compose_complete_dv_budget(
    earth_saturn_budget, saturn_arrival_staging=None, saturn_titan_transfer=None,
    *, connected_result=None,
) -> MissionDeltaVBudget:
    ...
    if saturn_arrival_staging is not None and not isinstance(saturn_arrival_staging, ...):
        raise TypeError(...)   # <- seule vérification de type, AUCUNE lecture de champ numérique
    ...
    return MissionDeltaVBudget(
        earth_departure_m_s=...,
        dsm_flyby_m_s=...,
        saturn_capture_to_ellipse_m_s=chain.saturn_capture.capture_delta_v_m_s,       # <- vient de `chain` (150 000/1 221 870 km), jamais de staging/titan
        saturn_staging_circularisation_m_s=chain.saturn_capture.circularisation_delta_v_m_s,
        saturn_titan_departure_m_s=0.0,   # <- codé en dur à zéro
        titan_capture_m_s=0.0,            # <- codé en dur à zéro
    )
```

`saturn_arrival_staging` et `saturn_titan_transfer` (calculés à partir des rayons legacy) sont acceptés **uniquement pour vérification de type** ; aucun de leurs champs numériques n'est lu. Confirmé par deux tests de régression qui passent :
- `tests/test_dv_budget.py::test_nominal_total_has_no_double_counted_legacy_capture`
- `tests/test_connected_physics.py::test_total_is_exact_sum_and_excludes_redundant_terms`

**Conclusion** : les valeurs legacy **ne contaminent pas** le budget connecté ni son ratio de masse, en l'état actuel du code.

---

## 8. Référentiels et unités

- **SI interne partout** : `mission/physics.py` documente explicitement m, s, m/s, μ en m³/s² (docstring du module). Conversion km uniquement en couche d'affichage.
- **Rayons Saturne cohérents** : `compute_saturn_capture_to_titan_orbit()` (`mission/connected_physics.py:150-153`) valide `periapsis > SATURN_EQUATORIAL_RADIUS_M` (60 268 km) **et** `periapsis > F_RING_REFERENCE_RADIUS_M` (140 180 km) avant d'accepter 150 000 km — les trois rayons sont mesurés depuis le **centre** de Saturne, ordre `60 268 < 140 180 < 150 000 < 1 221 870` cohérent.
- **Titan : deux constantes distinctes, jamais confondues** : `TITAN_MEAN_RADIUS_M = 2 574,76 km` (rayon physique du corps, `mission/constants.py:28`, utilisé pour l'échelle 3D) vs `TITAN_MEAN_ORBIT_RADIUS_M = 1 221 870 km` (rayon orbital autour de Saturne, ligne 34). Noms non ambigus, aucun site ne les confond.
- **Repère héliocentrique cohérent** entre les deux solveurs Lambert du dépôt (§2, point 2) : accord bit-pour-bit.

Aucune incohérence de référentiel ou d'unité trouvée.

---

## 9. L'affirmation « le ratio de masse passerait de 54,2 à 5,16 »

**Recherche de la source** : `git log --all -S "54.2"` et `-S "5.16"` sur l'ensemble de l'historique du dépôt, et recherche texte dans tous les fichiers `.py`/`.md` — **aucune occurrence**, dans aucune version, dans aucun fichier de ce dépôt. Le document source de cette affirmation n'est pas dans ce dépôt et n'a pas pu être localisé.

**Reconstitution indépendante** (`mission.sizing.compute_mass_budget`, Isp = 320 s, g₀ = 9,80665 m/s², par défaut de `pages/mission_setup.py`) :

```
mass_ratio(dv = 12 530,653 m/s)   = exp(12530.653 / (320·9.80665)) = 54.219...   ≈ 54,2
mass_ratio(dv =  5 149,173 m/s)   = exp( 5149.173 / (320·9.80665)) =  5.1595...  ≈ 5,16
```

où **5 149,173 m/s = capture (2 182,991) + circularisation (2 966,182)**, c'est-à-dire le total connecté **sans le poste d'injection terrestre (7 381,480 m/s)**.

**Ces deux chiffres correspondent exactement**, au centième près, à :
- `54,2` = ratio de masse pour le **total connecté complet** (injection + capture + circularisation) — la quantité correcte, physiquement complète.
- `5,16` = ratio de masse pour le **sous-total Saturne seul** (capture + circularisation), **excluant l'injection terrestre**, qui représente pourtant ~59 % du total connecté.

**Interprétation** : rien dans l'architecture du dépôt ne « change » entre ces deux nombres — ce ne sont pas un « avant » et un « après » d'une évolution architecturale. Ce sont deux calculs du même total delta-v de la même mission, sur deux périmètres différents et non équivalents. Présenter la chute de 54,2 à 5,16 comme un gain obtenu par une modification d'architecture serait **mathématiquement trompeur** : le vaisseau doit physiquement porter le propergol nécessaire à l'injection terrestre (le poste le plus coûteux du budget) pour quitter la Terre, quelle que soit l'architecture de capture à Saturne choisie ensuite. Un ratio de masse de 5,16 ne décrit **pas** une mission Terre→Saturne réalisable ; il décrit seulement la phase de capture saturnienne isolée de son départ.

**Vérification dans le code vivant** : aucun des 6 sites cartographiés en §4.2 ne reproduit ce calcul partiel — l'erreur potentielle n'est **pas présente** dans le code actuel de l'application (voir R2 pour une garde-fou proposée).

---

## 10. Ce qui est exact, ce qui dépend de l'architecture, ce qui reste non concluable

**Mathématiquement exact (étant donné les entrées)**
- Les formules hyperbole/ellipse de `compute_saturn_capture_to_titan_orbit()` (vis-viva à rayon commun, cohérentes avec la documentation `docs/connected_first_order_model.md`).
- `C3 = v∞²` — relation triviale, appliquée identiquement en §3 et dans `mission/launch_search.py:120`.
- `mass_ratio = exp(Δv / (Isp·g₀))` (Tsiolkovsky) — appliquée uniformément dans `mission/sizing.py`.
- La somme `total_m_s = Σ(4 postes)` de `MissionDeltaVBudget`, vérifiée exacte par test (`assertEqual(budget.total_m_s, sum(...))`).

**Dépend de l'architecture de lancement / des choix utilisateur**
- L'injection terrestre (≈7 381,480 m/s) dépend de l'altitude de parking LEO (250 km par défaut, modifiable dans Mission setup, `leo_altitude_km`) — un choix d'altitude différent change ce poste et donc le total connecté et le ratio de masse.
- Le ratio de masse (54,2) dépend entièrement de l'Isp choisi (320 s par défaut) — un moteur plus performant changerait ce chiffre sans qu'aucune trajectoire ne change.
- Le rayon de périapse connecté (150 000 km, ajustable dans une plage validée) est un choix de conception documenté (« *a design choice outside the reference F-ring radius, not an operational ring-clearance certification* », `docs/connected_first_order_model.md`), pas une contrainte physique unique.

**Non concluable en l'état (et volontairement non tranché ici)**
- Compatibilité avec un lanceur réel donné (aucune base de données de lanceur, aucune courbe C3-vs-masse-utile dans le dépôt — cf. interdiction explicite de trancher).
- Faisabilité d'une rencontre réellement phasée avec Titan (le modèle s'arrête à un rayon orbital saturnocentrique commun ; aucune éphéméride de Titan n'entre dans ce calcul — documenté comme exclusion explicite dans `connected_physics.py`, `assumptions`/`exclusions`).
- Toute économie de delta-v par assistance gravitationnelle (aucun calcul de ce type n'a été demandé ni produit dans cet audit).

---

## 11. Tests exécutés

```
python -m pytest -q
440 passed, 211 subtests passed
```

Tests directement pertinents pour cet audit, exécutés individuellement avec succès :
- `tests/test_connected_physics.py` (11 tests, incl. `test_lambert_and_baseline_paths_share_identical_saturn_burns`, `test_total_is_exact_sum_and_excludes_redundant_terms`)
- `tests/test_dv_budget.py` (`test_nominal_total_has_no_double_counted_legacy_capture`, `test_composes_only_the_two_authoritative_saturn_burns`)

Aucun échec. Aucune constante modifiée pour obtenir ces résultats.

---

## Incohérences relevées

| # | Sévérité | Constat | Fichier |
|---|---|---|---|
| I1 | Mineure (complétude) | C3 calculable pour la baseline mais jamais affiché sur Mission setup / le scorecard actif — seule la page *Launch windows* le montre. | `pages/mission_setup.py` |
| I2 | Mineure (garde-fou absent) | Rien dans le code n'empêche explicitement un futur appelant de `compute_mass_budget()` de lui passer un sous-total partiel (ex. Saturne seul) plutôt que le total connecté complet — le motif exact reconstitué en §9 n'est pas *présent* mais n'est pas non plus *techniquement empêché*. | `mission/sizing.py`, `app_services.py` |
| I3 | Informationnelle | L'affirmation « 54,2 → 5,16 » n'a pas de source dans ce dépôt ; si elle circule dans un document externe, elle risque d'être lue comme un gain d'architecture alors qu'elle compare deux périmètres de calcul non équivalents (§9). | — (hors dépôt) |

Aucune incohérence de niveau bloquant (donnée fausse, formule incorrecte, contamination réelle du budget connecté) n'a été trouvée.

---

## Recommandations

**R1 (mineure, UI seulement)** — Afficher le C3 (108,83 km²/s² pour la baseline actuelle) sur le scorecard Mission setup, à côté du v∞ actif, pour cohérence avec la page *Launch windows*. Aucune formule nouvelle : réutiliser `v_inf**2 / 1e6`, déjà présent dans `mission/launch_search.py:120`.

**R2 (correction scientifique minimale proposée, non implémentée)** — Ajouter une garde explicite (docstring renforcé + assertion de nommage, ou un test de non-régression dédié) documentant que `compute_mass_budget(dv_total, ...)` **doit toujours recevoir un total de mission complet** (jamais un sous-total de phase), avec un exemple explicite du contre-exemple Saturne-seul (§9) comme cas de test à interdire. Cette garde ne changerait aucune constante ni aucun résultat existant ; elle documenterait et testerait un invariant déjà respecté partout aujourd'hui, pour empêcher qu'il soit un jour rompu silencieusement. **Non implémentée dans cet audit**, conformément à la consigne de proposer séparément toute correction scientifique.

**R3 (documentation)** — Si un document externe édité hors de ce dépôt contient l'affirmation « 54,2 → 5,16 », le corriger pour clarifier qu'il s'agit de deux périmètres de calcul (mission complète vs phase Saturne seule) et non d'un gain d'architecture, en citant les mêmes deux totaux delta-v (12 530,653 m/s et 5 149,173 m/s) que ce rapport.

---

## Rappel des interdictions respectées

- Aucune capture Titan ajoutée.
- Aucune économie de 1,43 km/s annoncée (aucun calcul de gain gravity-assist effectué).
- Aucun jugement de compatibilité lanceur rendu (§10, explicitement classé « non concluable »).
- Lambert non remplacé par Hohmann — Hohmann n'a été utilisé que comme référence documentée déjà présente dans le dépôt (`docs/connected_first_order_model.md`), jamais substitué au chemin Lambert réel.
- Aucune constante modifiée dans `mission/` ou ailleurs.
