# Mission Tool — objectif du week-end

## Objectif principal

Construire une première mission calculable :

Terre → Saturne → Titan

## Fonctionnalités incluses

- transfert Lambert Terre → Saturne ;
- départ direct ou injection depuis LEO ;
- capture propulsive à Saturne ;
- transfert simplifié Saturne → Titan ;
- capture propulsive autour de Titan ;
- budget de Delta-V par étape ;
- budget de masse préliminaire ;
- hypothèses physiques visibles ;
- tests automatiques de non-régression.

## Fonctionnalités exclues

- assistances gravitationnelles ;
- manoeuvres DSM ;
- descente atmosphérique ;
- atterrissage sur Titan ;
- optimisation multi-corps ;
- autres destinations ;
- dimensionnement détaillé des sous-systèmes ;
- déploiement public.

## Hypothèses initiales Saturne → Titan

- référentiel centré sur Saturne ;
- orbites circulaires et coplanaires ;
- orbite moyenne de Titan ;
- transfert de Hohmann préliminaire ;
- capture impulsive autour de Titan ;
- unités internes en mètres, secondes et kilogrammes.

## Critères de réussite

Le week-end est terminé lorsque :

- `make check` passe intégralement ;
- l’environnement est reproductible ;
- la CI exécute automatiquement les contrôles ;
- l’interface ne présente plus de fonctionnalités fictives ;
- les calculs Lambert ne sont pas relancés inutilement ;
- Terre → Saturne → Titan produit deux jambes cohérentes ;
- chaque valeur distingue clairement v-infinity et Delta-V ;
- les unités et hypothèses sont documentées ;
- les scénarios de non-régression passent.

## Règles de travail

- une tâche logique par commit ;
- tests obligatoires avant chaque commit ;
- aucune modification des valeurs de référence sans justification ;
- aucune fonctionnalité non implémentée présentée comme fonctionnelle ;
- les choix physiques doivent être documentés avant leur implémentation.
