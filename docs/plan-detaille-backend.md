---
title: "Plan détaillé — Partie IV : conception et développement du chatbot côté backend"
subtitle: "Chatbot territorial du Grand Albigeois"
author: "Master 1 TRIED — IPST-CNAM Albi — groupe Backend"
date: "2 septembre 2026"
lang: fr-FR
---

# Cadrage

## Contraintes de l'oral

| Contrainte | Règle retenue |
|---|---|
| Durée totale | 35 minutes |
| Par groupe | 15 minutes maximum sur un seul groupe |
| Slides | 1 slide par minute de parole au maximum |
| Contenu imposé | une partie « pourquoi est-il encore pertinent de faire notre travail à la main, sans IA » |
| Échéance | plan détaillé envoyé le jour même |

## Budget de temps proposé

À valider avec les groupes Besoin et Front. Le backend est le lot le plus technique et demande une minute de plus que le front, tout en restant très en deçà du plafond de 15 minutes.

| Partie du rapport | Groupe | Durée | Slides |
|---|---|---|---|
| I — Introduction | commun | 2 min | 2 |
| II — Analyse des besoins | Besoin | 9 min | 9 |
| III — Interface frontend | Front | 10 min | 10 |
| **IV — Chatbot backend** | **Back** | **11 min** | **11** |
| V — Conclusion | commun | 3 min | 3 |
| **Total** | — | **35 min** | **35** |

Si le groupe préfère ramener chaque lot à 9 minutes, les slides 2 et 10 du storyboard sont conçues pour être fondues dans leurs voisines sans casser le fil du propos.

# Partie IV — Plan détaillé

Structure calquée sur la partie III du front (recueil des besoins, choix techniques, développement, résultats, travail manuel), adaptée à ce que le backend a réellement à démontrer. Volume visé : environ 9 à 10 pages.

## IV.1 — Des besoins du client aux exigences du backend

*Environ 1 page — slides 1 et 2.*

**Ce qu'on démontre :** ce que le serveur doit garantir n'a pas été décidé par nous, c'est la traduction technique du recueil des besoins.

- Rappel du besoin côté serveur, en une phrase : **recueillir en langage libre le besoin d'un industriel et l'orienter vers les acteurs de l'innovation du territoire**, à partir d'un annuaire centralisé.
- Traduction en exigences vérifiables : REQ-FUNC.1 recueil du besoin, .2 orientation automatique, .3 garantie de qualité, .4 confidentialité, .5 connexion à l'annuaire, .6 gestion des accès ; REQ-NF.2 performance, .4 évolutivité, .5 compatibilité.
- Les quatre personas du recueil se lisent comme quatre usages de l'API : l'industriel interroge, le chargé de mission consulte les statistiques, l'administrateur tient l'annuaire, le partenaire fournit ses données.
- Périmètre du lot backend, et ce qui en est explicitement exclu : le widget d'intégration, l'hébergement définitif, le connecteur vers l'annuaire régional réel (dont le format n'est pas encore connu).

**Support :** tableau de traçabilité exigence → réponse du backend (9 lignes, déjà rédigé dans `backend/README.md`).

**Chiffres à citer :** 6 exigences fonctionnelles, 3 non-fonctionnelles, 4 personas.

## IV.2 — Le choix structurant : retrouver plutôt que générer

*Environ 1,5 page — slide 3.*

**Ce qu'on démontre :** le chatbot ne rédige rien. C'est une décision de conception, prise avant la première ligne de code, et tout le reste en découle.

- Point de départ : la note *Benchmark des solutions de chatbot institutionnel* recommande une recherche sémantique **sans IA générative**.
- Les trois familles comparées : arbre de décision à règles, recherche d'information (mots-clés puis sémantique), génération augmentée par un LLM. Critères : fiabilité de la réponse, auditabilité, coût par question, dépendance à un fournisseur, traitement des données, effort de maintien.
- L'argument décisif : orienter vers un acteur public engage la collectivité. Un modèle qui invente un dispositif d'aide, un interlocuteur ou un numéro de téléphone produit un préjudice concret, et une phrase générée ne s'audite pas.
- La décision et sa conséquence directe : toute réponse est **assemblée** à partir de trois matières validées — une fiche de l'annuaire, un extrait exact d'un document, un message configuré par l'administrateur. Chaque élément affiché est donc traçable jusqu'à sa source.
- Ce que ce choix n'interdit pas : la réponse de `/ask` renvoie déjà les passages et leurs sources ; une couche de rédaction pourrait s'y brancher plus tard sans toucher à l'index. L'évolutivité est préservée, elle n'est simplement pas activée.

> **Ne pas confondre avec IV.6.** Ici, c'est *le produit* qui ne génère pas. En IV.6, c'est *notre méthode de travail*. Deux questions différentes — mais les annoncer comme telles permet de les faire se répondre en conclusion.

**Support :** tableau comparatif 3 approches × 6 critères, avec la ligne retenue mise en évidence.

## IV.3 — Architecture et modélisation des données

*Environ 2 pages — slides 4 et 5.*

**Ce qu'on démontre :** le modèle conceptuel du recueil des besoins est devenu, sans intermédiaire, le schéma de la base.

- L'architecture se lit en deux temps. **Alimentation** : annuaire SQLite et fiches Markdown → projection en texte → découpage en passages → embeddings → index vectoriel (et index mots-clés). **Interrogation** : question → embedding → passages les plus proches → seuil de fiabilité → réponse composée et journal anonymisé.
- Justifier chaque brique par une contrainte, jamais par la mode : FastAPI (validation Pydantic, Swagger automatique), SQLite en mode WAL (aucun service à exploiter, sauvegarde = un fichier, schéma = le MCD), ChromaDB embarqué (mise à jour incrémentale), rank-bm25 (la baseline du benchmark, conservée comme complément), `multilingual-e5-small` sur CPU (bon en français, 118 M de paramètres, environ 470 Mo, quelques millisecondes par question).
- Le MCD devient le schéma : `organizations`, `sites` (association *Situer*), `contacts` (*Contact*), `domains` et `organization_domains` (*Exerce*). Une organisation se manipule comme un document complet.
- **La décision à défendre : on n'indexe pas tout.** Seuls la description, les domaines et les mots-clés d'un acteur sont vectorisés. Les villes, adresses et téléphones sont affichés depuis la base mais volontairement exclus de l'index — sinon « un restaurant à Albi » ferait remonter n'importe quel acteur albigeois. C'est une décision de terrain, pas une optimisation.
- Conséquence pour l'administrateur : la description est le texte qui sert à la recherche ; la rédiger avec les mots des industriels (« agrandir mon atelier », « trouver un terrain ») améliore directement l'orientation.
- Deux granularités de découpage, pour deux natures de contenu : fiches documentaires en fenêtres de 700 caractères avec 100 de chevauchement, organisations en passages de 300 sans chevauchement (une phrase ≈ un vecteur).

**Support :** schéma du pipeline en deux bandes (alimentation / interrogation) et extrait du MCD annoté avec les noms de tables.

**Chiffres à citer :** 24 acteurs réels de démarrage, 17 domaines, 8 fiches, 118 passages indexés, environ 2 690 lignes de Python applicatif.

## IV.4 — Le moteur de recherche et la règle de fiabilité

*Environ 2 pages — slides 6 à 8.*

**Ce qu'on démontre :** le cœur du travail n'est pas de trouver une réponse, c'est de savoir quand il ne faut pas en donner.

- Trois modes implémentés et comparables : `keyword` (BM25, la baseline du benchmark, volontairement naïve), `semantic` (E5), `hybrid` (mode par défaut).
- La fusion : RRF, score = somme de 1/(k + rang) avec k = 60. Expliquer **pourquoi une fusion par rang et non par score** : un score BM25 et une similarité cosinus ne vivent pas sur la même échelle et ne s'additionnent pas.
- La règle de fiabilité : un acteur ou un extrait n'est proposé que si son meilleur passage atteint une similarité cosinus supérieure ou égale à **0,825**. En mode hybride, BM25 ne sert qu'au classement ; un passage classé dans les trois premiers par mots-clés bénéficie d'une tolérance de 0,01 sous le seuil, ce qui rattrape les sigles et les noms propres.
- Sous le seuil, le chatbot dit qu'il n'a pas trouvé et propose des catégories de besoins pour reformuler : le refus n'est pas un échec, c'est la réponse à REQ-FUNC.1 (guider la formulation du besoin).
- La couche conversationnelle et ses quatre intentions : *orientation* (jusqu'à 3 acteurs et 1 extrait), *organization* (l'usager nomme un acteur, la fiche complète est renvoyée sans passer par l'index, avec reconnaissance des sigles et des alias), *document*, *no_answer*.
- Le contrat d'API : `/ask`, `/feedback`, `/config`, `/organizations` côté public ; `/admin/*` protégés par l'en-tête `X-API-Key` (comparaison en temps constant). C'est le point de contact avec la partie III : s'accorder avec le front sur la slide qui montre le contrat.
- Confidentialité (REQ-FUNC.4) : aucune adresse IP ni donnée nominative, identifiant de session haché en SHA-256 avec un sel propre à l'installation, purge automatique à 365 jours, collecte désactivable depuis le back-office.

**Support :** une réponse `/ask` annotée (answer, organizations, documents, suggestions, score, query_id, latency_ms).

**Démonstration :** deux questions en direct, une dans le périmètre et une hors périmètre pour montrer le refus. C'est le moment le plus convaincant de la partie ; le préparer et le répéter.

## IV.5 — Évaluation, résultats et exploitation par le client

*Environ 1,5 page — slides 9 et 10.*

**Ce qu'on démontre :** le seuil de 0,825 n'est pas un réglage d'intuition, c'est le résultat d'une mesure que l'on peut rejouer devant le jury.

- La méthode : un jeu de **46 questions** — 38 besoins formulés comme les personas les poseraient (souvent sans les mots des fiches) et 8 questions hors périmètre auxquelles le chatbot *doit* refuser de répondre. Rejouable en une commande : `python -m app.cli eval -v`.
- Ce qu'on mesure : la **réponse effectivement produite**, et pas seulement le premier résultat brut — hit@1, présence dans la réponse, MRR, taux de faux rejets, taux de rejet des hors-sujet.

| Mode | hit@1 | Trouvé dans la réponse | MRR | Faux rejets | Rejet des hors-sujet |
|---|---|---|---|---|---|
| `keyword` (BM25) | 89 % | 100 % | 0,936 | 0 % | 25 % |
| `semantic` (E5-small) | 87 % | 95 % | 0,901 | 0 % | 75 % |
| **`hybrid`** (retenu) | **92 %** | **100 %** | **0,950** | **0 %** | **75 %** |

- **Le résultat le plus intéressant à raconter :** BM25 seul retrouve la bonne réponse dans 100 % des cas… et répond aussi aux questions hors sujet dès qu'un mot est partagé (« restaurant à *Albi* », « billet de train *Albi*–*Toulouse* »). Il ne sait pas dire « je ne sais pas ». Le mode hybride garde la barrière sémantique et gagne sur les sigles.
- Les limites, assumées : deux hors-sujet sur huit passent encore, c'est la limite du modèle *small*. Le levier n'est pas un seuil plus haut — il créerait des faux rejets — mais un modèle plus discriminant (`e5-base`) ou un réordonnancement par cross-encoder sur les 20 candidats.
- Qualité logicielle : 43 tests pytest (unitaires et intégration API avec le vrai modèle, environ 620 lignes), conteneur Docker fonctionnant **hors ligne** (modèle embarqué), sans privilèges, avec *healthcheck* ; 20 à 80 ms par question sur CPU.
- La boucle d'exploitation par le client : les questions restées sans réponse remontent dans `/admin/analytics`, l'administrateur enrichit l'annuaire, la qualité s'améliore sans réentraînement ni intervention de développeur. C'est ce qui rend le produit livrable.

**Support :** ce tableau et une capture du tableau de bord analytiques (questions fréquentes, questions sans réponse).

**À refaire :** rejouer l'évaluation avant l'impression du rapport et figer les chiffres cités partout.

## IV.6 — Pourquoi ce backend a été écrit à la main

*Environ 1,5 page — slide 11. Partie imposée par la consigne.*

**Ce qu'on démontre :** ce qui fait la qualité de ce serveur n'est presque jamais du code, ce sont des arbitrages mesurés sur nos données et sur nos personas.

- **Poser la distinction d'entrée.** En IV.2, le produit choisit de ne pas générer. Ici, c'est nous qui choisissons de ne pas faire générer le produit. Les deux décisions se justifient par la même exigence — répondre de ce qu'on livre — et c'est ce parallèle qui donne sa force à la partie.
- **Les décisions qui comptent ne sont pas des lignes de code.** Le seuil à 0,825, la tolérance de 0,01, la non-indexation des villes, le découpage des organisations à 300 caractères : aucune de ces valeurs ne se devine. Chacune vient d'une mesure sur un jeu de questions que nous avons dû écrire nous-mêmes. Un générateur produit un code plausible ; il ne produit pas la mesure qui dit quel seuil ne crée pas de faux rejets sur *cet* annuaire.
- **L'ancrage dans le recueil des besoins.** Le schéma de la base est le MCD du client, pas un schéma générique. La chaîne besoin → modèle → code est ce qui rend le livrable défendable ; elle se rompt dès que la conception est déléguée.
- **Responsabilité et traçabilité.** Le destinataire est une collectivité. Chaque comportement doit être justifiable, d'où le tableau de traçabilité des exigences, les tests et l'évaluation rejouable. On ne défend pas devant un client, ni devant un jury, un code qu'on n'a pas compris.
- **Le coût ne disparaît pas, il se déplace.** Du code généré doit être lu, corrigé, testé et calibré. Sur un sujet de recherche d'information, l'essentiel du temps est dans l'évaluation et le calibrage : c'est précisément la part qui ne se délègue pas.
- **Les contraintes de déploiement.** Fonctionnement hors ligne, sur CPU, coût nul par question, données qui ne quittent pas le serveur : c'est le résultat d'un choix d'ingénierie assumé, pas d'un assemblage rapide.
- **C'est la compétence visée par le diplôme.** Modéliser, indexer, évaluer quantitativement : le M1 valide ce que nous savons faire, pas ce que nous savons commander.
- **La nuance à garder, pour ne pas caricaturer.** Nous ne disons pas que l'IA est inutile — le backend en utilise une, un modèle d'embeddings, à l'endroit où elle est fiable et mesurable. Nous disons qu'elle ne remplace ni la mesure, ni la responsabilité, ni la compréhension du besoin.

> **Deux points à trancher en groupe.**
> **1.** Dire honnêtement quel usage de l'assistance IA a réellement eu lieu dans le projet et où la décision est restée humaine : un périmètre assumé est bien plus solide devant un jury qu'un « zéro IA » invérifiable.
> **2.** Se répartir les arguments avec le front (III.5) pour ne pas tenir deux fois le même discours : au front la maîtrise de l'interface, l'accessibilité et la dette technique ; au backend la mesure, la responsabilité et les données. La conclusion (V) réunit les deux.

# Storyboard des 11 slides

Une slide par minute, jamais plus. Les slides 2 et 10 sont les variables d'ajustement si le temps du groupe est réduit à 9 minutes.

| # | Slide | Sous-partie | Ce qu'on montre |
|---|---|---|---|
| 1 | Le lot backend en une phrase | IV.1 | périmètre, et ce qui en est exclu |
| 2 | Des exigences aux garanties | IV.1 | tableau de traçabilité *(fusionnable)* |
| 3 | Retrouver plutôt que générer | IV.2 | comparatif des 3 approches |
| 4 | Architecture en deux temps | IV.3 | schéma alimentation / interrogation |
| 5 | Le MCD devient le schéma | IV.3 | tables, et ce qu'on n'indexe pas |
| 6 | Trois modes, une fusion | IV.4 | BM25, E5, RRF |
| 7 | Le droit de dire « je ne sais pas » | IV.4 | le seuil et le refus |
| 8 | Démonstration | IV.4 | une question dans le périmètre, une hors périmètre |
| 9 | Évaluation sur 46 questions | IV.5 | tableau des 3 modes |
| 10 | Limites et exploitation | IV.5 | tableau de bord, boucle d'enrichissement *(fusionnable)* |
| 11 | Pourquoi à la main | IV.6 | les arbitrages qui ne se génèrent pas |

# À faire d'ici l'oral

1. **Valider le budget de temps** avec les groupes Besoin et Front. *(aujourd'hui)*
2. **Envoyer ce plan détaillé** et confirmer la répartition des arguments IV.6 / III.5 avec le front. *(aujourd'hui)*
3. **Produire les deux schémas** de la partie IV.3 : pipeline en deux bandes, et MCD annoté avec les noms de tables.
4. **Rejouer l'évaluation** (`python -m app.cli eval -v`) et figer les chiffres cités dans le rapport et les slides.
5. **Capturer** le tableau de bord analytiques et une réponse `/ask` complète pour l'annotation.
6. **Répéter la démonstration hors ligne** (`docker compose up`) et préparer des captures de secours en cas de problème de machine ou de réseau.
7. **Annoncer clairement en démonstration** que les coordonnées de l'annuaire de démarrage restent à valider avec chaque partenaire : c'est une exigence du recueil, pas un détail.
8. **Chronométrer** la partie IV à blanc : 11 minutes est un plafond, viser 10.

# Sources

Ce plan s'appuie sur `backend/README.md` (architecture, contrat d'API, résultats d'évaluation, traçabilité des exigences), le code de `backend/app/`, le jeu d'évaluation `backend/eval/questions.jsonl` et le recueil des besoins du 09/02/2026.
