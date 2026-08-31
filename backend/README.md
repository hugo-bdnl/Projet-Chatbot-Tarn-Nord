# Chatbot territorial — back-end (annuaire + recherche sémantique, sans IA générative)

Back-end du chatbot du Grand Albigeois (projet **Master 1 TRIED, IPST-CNAM Albi**). Il répond au recueil des besoins
(*Projet chatbot CNAM, 09/02/2026*) : **recueillir le besoin d'un industriel et l'orienter automatiquement vers les
acteurs de l'innovation du territoire** (laboratoires, plateformes, écoles, centres techniques, financeurs, acteurs
emploi-formation), à partir d'un **annuaire centralisé** (organisations, sites, contacts, domaines d'activité).

Il applique la recommandation de la note *« Benchmark des solutions de chatbot institutionnel »* : recherche
sémantique **sans IA générative**. Le système ne rédige rien : chaque réponse est assemblée à partir de fiches de
l'annuaire, d'extraits exacts de documents et de messages configurés par l'administrateur. Quand rien n'est assez
proche, il le dit et propose de préciser le besoin.

```
Alimentation (au démarrage, puis à chaque modification de l'annuaire)
  annuaire SQLite (organisations, sites, contacts, domaines) ──► fiche texte par acteur ─┐
  fiches Markdown (corpus/)  ──► découpage par sections ─────────────────────────────────┴─► embeddings ─► index ChromaDB
                                                                                                          (+ index BM25 en mémoire)
À chaque besoin exprimé
  question ──► embedding ──► passages les plus proches (acteurs + fiches) ──► seuil de fiabilité
           ──► jusqu'à 3 acteurs (fiche annuaire complète) + 1 extrait documentaire + relances
           ──► journal anonymisé (analytiques du back-office)
```

## Stack

| Brique | Choix | Pourquoi |
|---|---|---|
| API | Python 3.12+ / FastAPI | Swagger automatique (`/docs`), validation Pydantic, asynchrone |
| Annuaire, configuration, journal | SQLite (bibliothèque standard, mode WAL) | zéro service à exploiter, schéma = MCD du recueil des besoins, sauvegarde = un fichier |
| Embeddings | `intfloat/multilingual-e5-small` (sentence-transformers, **CPU**) | bon en français, 118 M de paramètres, ~470 Mo, quelques ms par question |
| Index vectoriel | ChromaDB embarqué (persistant) | suffisant pour des milliers de passages, mise à jour incrémentale |
| Mots-clés | rank-bm25 | baseline du benchmark + complément du mode hybride (sigles, noms propres) |
| Conteneur | Docker (python:3.12-slim, torch CPU, modèle embarqué) | fonctionne hors ligne sur un serveur standard |

## Structure

```
backend/
├── app/
│   ├── main.py              # création de l'app FastAPI, CORS, routers
│   ├── api/public.py        # /health /config /ask /feedback /organizations /domains /documents
│   ├── api/admin.py         # /admin/* (annuaire CRUD + import/export, analytiques, config, reindex) — X-API-Key
│   ├── assistant.py         # couche conversationnelle : orientation, fiche d'acteur, refus, relances, catégorie
│   ├── directory/           # annuaire : repository SQLite (MCD) + projection texte (indexée / affichée)
│   ├── analytics.py         # journal anonymisé des questions, feedback, statistiques
│   ├── chatbot_config.py    # configuration métier modifiable à chaud (nom, accueil, catégories…)
│   ├── indexer.py           # alimente l'index : fiches du corpus + organisations
│   ├── search/              # embeddings E5, ChromaStore, BM25, moteur (3 modes, RRF, seuil)
│   ├── ingestion/           # loaders md/txt/html/pdf, découpage en passages
│   ├── db.py, config.py, schemas.py, bootstrap.py, cli.py
├── seed/organizations.json  # annuaire de DÉMARRAGE : 24 acteurs réels de l'écosystème (coordonnées à valider)
├── corpus/                  # 8 fiches Markdown de démonstration (aides, énergie, foncier, RH, recherche, sous-traitance…)
├── eval/questions.jsonl     # 38 besoins annotés + 8 questions hors périmètre
├── tests/                   # pytest : 43 tests (unitaires + intégration API avec le vrai modèle)
├── Dockerfile, docker-compose.yml, .env.example, requirements*.txt
```

## Démarrage rapide

### Docker (recommandé)

```bash
cd backend
cp .env.example .env            # renseigner CHATBOT_API_KEY (protège /admin/*)
docker compose up -d --build    # ~5 min la 1re fois (torch CPU + modèle embarqués dans l'image)
curl http://localhost:8000/health
```

Au premier démarrage : l'annuaire est vide → chargement de `seed/organizations.json` ; l'index est vide → indexation
des fiches et des organisations (quelques secondes). Données persistantes dans le volume `chatbot-data`
(`/data` : `chatbot.sqlite3` + index Chroma). `./corpus` est monté en lecture seule ; après modification d'une
fiche : `POST /admin/reindex`.

### Local (venv)

```bash
cd backend
uv venv .venv --python 3.12                      # ou python -m venv .venv
# Windows : .venv/Scripts/activate  |  Linux/macOS : source .venv/bin/activate
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -r requirements-dev.txt

python -m app.cli seed                           # charge l'annuaire de démarrage + construit l'index
python -m app.cli ask "J'ai besoin d'une pièce métallique spécifique"
uvicorn app.main:app --reload                    # http://127.0.0.1:8000/docs
```

CLI : `python -m app.cli {seed|ingest|ask|eval|stats|export}` (`seed --file mon-annuaire.json [--replace]`,
`export --out sauvegarde.json`).

## API

### Public (widget de chat, annuaire en consultation)

| Méthode | Route | Rôle |
|---|---|---|
| `GET` | `/health` | état, modèle, nb de fiches / organisations / passages |
| `GET` | `/config` | nom du chatbot, message d'accueil, suggestions initiales |
| `POST` | `/ask` | besoin exprimé → acteurs + extrait + relances (voir ci-dessous) |
| `POST` | `/feedback` | `{query_id, helpful, comment?}` — évaluation d'une réponse par l'usager |
| `GET` | `/organizations?q=&domain=&limit=&offset=` | annuaire (acteurs actifs), recherche plein texte simple |
| `GET` | `/organizations/{id}` | fiche complète (sites, contacts, domaines) |
| `GET` | `/domains` | domaines d'activité avec description et nombre d'acteurs |
| `GET` | `/documents` | contenu de l'index (fiches + organisations, nb de passages) |

### Administration (`X-API-Key: <CHATBOT_API_KEY>`)

| Méthode | Route | Rôle |
|---|---|---|
| `GET/POST` | `/admin/organizations` | lister (actives et inactives, `?active=`) / créer |
| `PUT/DELETE` | `/admin/organizations/{id}` | modifier (remplace sites, contacts, domaines) / supprimer — l'index est mis à jour immédiatement |
| `POST` | `/admin/organizations/import` | `{domains?, organizations, replace?}` — import en masse, « upsert » par nom (synchronisation annuaire régional) |
| `GET` | `/admin/organizations/export` | export complet réimportable |
| `PUT` | `/admin/domains/{id}` | renommer / décrire un domaine |
| `POST` | `/admin/reindex` | reconstruire l'index (après modification des fiches Markdown) |
| `GET` | `/admin/analytics?days=7` | conversations/jour, sessions distinctes, taux de réponse, satisfaction, latence, sujets, questions fréquentes **et sans réponse**, acteurs les plus proposés |
| `GET` | `/admin/analytics/questions?answered=false` | journal détaillé (pour enrichir l'annuaire) |
| `GET/PUT` | `/admin/config`, `POST /admin/config/reset` | configuration métier : nom, accueil, suggestions, orientation, collecte des statistiques, nb d'acteurs proposés, messages, catégories de besoins (mots-clés + question exemple) |

### `POST /ask`

```json
{"question": "Je cherche des aides pour innover", "session_id": "uuid-anonyme-du-navigateur"}
```

Champs optionnels : `mode` (`hybrid` par défaut, `semantic`, `keyword`), `max_organizations` (1-10), `debug`
(ajoute les passages candidats bruts dans `hits`). Réponse (abrégée) :

```json
{
  "question": "Je cherche des aides pour innover",
  "mode": "hybrid",
  "intent": "orientation",
  "answered": true,
  "answer": "Voici les acteurs du territoire qui peuvent répondre à votre besoin :\n\n• AD'OCC — Agence de développement économique de la Région Occitanie. (Toulouse)\n• Albi InnoProd – Technopole — Technopole de l'Albigeois : pépinière et hôtel d'entreprises… (Albi)\n• AREC Occitanie — Agence régionale énergie climat de la Région Occitanie… (Toulouse)\n\nÀ lire aussi — Financer un projet d'innovation : panorama des aides › Préparer son dossier :\nQuel que soit le financeur, un dossier comprend : …\n\nSouhaitez-vous plus d'informations sur l'un de ces acteurs ?",
  "category": "Innovation & Financement",
  "score": 0.8571,
  "organizations": [
    {"id": 6, "name": "AD'OCC", "description": "Agence de développement économique de la Région Occitanie. …",
     "website": "https://www.agence-adocc.com", "domains": ["Financement", "Accompagnement", "Innovation", "Export", "Foncier & Implantation"],
     "sites": [{"id": 59, "label": "Siège", "address": "", "postal_code": "31000", "city": "Toulouse"}, {"id": 60, "label": "Antenne Tarn", "postal_code": "81000", "city": "Albi"}],
     "contacts": [{"id": 54, "last_name": "", "first_name": "", "role": "Chargé d'affaires Tarn", "email": "", "phone": ""}],
     "keywords": ["aides régionales", "subvention", "…"], "active": true, "score": 0.8663}
  ],
  "documents": [
    {"title": "Financer un projet d'innovation : panorama des aides", "source": "aides-innovation.md",
     "section": "Préparer son dossier", "text": "Quel que soit le financeur, un dossier comprend : …", "score": 0.8571}
  ],
  "suggestions": ["En savoir plus sur AD'OCC", "En savoir plus sur Albi InnoProd – Technopole", "En savoir plus sur AREC Occitanie"],
  "query_id": 1,
  "latency_ms": 70.1
}
```

- `answer` est un texte prêt à afficher (le front peut aussi construire ses propres cartes à partir de
  `organizations` / `documents`) ; `suggestions` sont les puces de relance ; `query_id` est à renvoyer sur
  `/feedback`.
- Quatre `intent` : `orientation` (acteurs proposés), `organization` (l'usager a nommé un acteur : « En savoir plus
  sur France Travail » → fiche complète, sans passer par l'index), `document` (seul un extrait de fiche est assez
  proche), `no_answer` (`answered: false`, message configurable + catégories de besoins en relances).

> Sous Windows, `curl -d '…é…'` envoie les accents en cp1252 et l'API répond `422` : utiliser Swagger (`/docs`),
> `python -m app.cli ask "…"`, ou `--data-binary @fichier-utf8.json`.

## Données

### Annuaire (MCD du recueil des besoins, § 6)

| Entité du MCD | Table | Champs |
|---|---|---|
| Organisations | `organizations` | `name` (unique, insensible à la casse), `description`, `website`, + `keywords` (termes de recherche), `active` |
| Site (*Situer*) | `sites` | `label`, `address`, `postal_code`, `city` |
| Contact (*Contact*) | `contacts` | `last_name`, `first_name`, `role`, `email`, `phone` |
| Domaine d'activité (*Exerce*) | `domains` + `organization_domains` | `name` (unique), `description` |

Une organisation est manipulée comme un document complet (`sites`, `contacts`, `domains` inclus) ; `PUT` remplace ces
collections. **La `description` est le texte qui sert à la recherche** : la rédiger avec les mots des industriels
(« pour agrandir votre atelier, trouver un terrain… ») améliore directement l'orientation ; `keywords` complète
(sigles, synonymes). Villes, adresses et coordonnées ne sont pas indexées (elles sont affichées depuis la base).

`seed/organizations.json` fournit 24 acteurs réels de l'écosystème albigeois et occitan (IMT Mines Albi et ses
centres RAPSODEE / ICA / CGI, INU Champollion, AD'OCC, Région, Bpifrance, CCI du Tarn, agglomération de l'Albigeois,
Albi InnoProd, Mecanic Vallée, Aerospace Valley, UIMM, France Travail, Mission Locale, ADEME, AREC, Cnam, CMA, CRITT,
OPCO 2i, Action Logement, SATT) avec des descriptions générales : **adresses, téléphones et e-mails sont à valider
avec chaque partenaire** avant mise en service (REQ-FUNC.3 « validation partenaires »).

### Fiches documentaires (`corpus/`)

Formats : `.md` (conseillé), `.txt`, `.html`, `.pdf`. Le titre `#` devient le titre de la fiche, les `##` le
« chemin de section » affiché avec l'extrait ; les commentaires HTML `<!-- … -->` ne sont ni indexés ni affichés
(notes internes). Les 8 fiches fournies sont des **fiches de démonstration** à valider par le service développement
économique.

## Règle de fiabilité (ne jamais inventer)

Un acteur ou un extrait n'est proposé que si son meilleur passage a une **similarité cosinus ≥ `CHATBOT_MIN_SCORE`**
(0,825). En mode `hybrid` (défaut), BM25 ne sert qu'au classement (fusion RRF) ; un passage classé dans les 3 premiers
par mots-clés est toléré jusqu'à `CHATBOT_HYBRID_TOLERANCE` (0,01) sous le seuil. En mode `keyword`, il suffit d'un
mot significatif commun (c'est la baseline du benchmark, volontairement naïve). Sous le seuil : `answered: false`.

Le seuil se calibre avec `python -m app.cli eval -v`, qui affiche le score minimal des questions légitimes et le
score maximal des questions hors périmètre. Avec E5-small, les similarités sont concentrées entre ~0,77 et ~0,87 :
0,01 d'écart compte. **Après tout enrichissement notable de l'annuaire, rejouer l'évaluation.**

### Résultats (24 acteurs + 8 fiches = 118 passages, `min_score = 0,825`)

L'évaluation mesure la **réponse produite** (jusqu'à 3 acteurs puis 1 extrait), sur 38 besoins formulés comme les
personas du recueil (souvent sans les mots des fiches) et 8 questions hors périmètre.

| Mode | hit@1 | trouvé dans la réponse | MRR | faux rejets | rejet des hors-sujet |
|---|---|---|---|---|---|
| `keyword` (BM25) | 89 % | 100 % | 0,936 | 0 % | **25 %** |
| `semantic` (E5-small) | 87 % | 95 % | 0,901 | 0 % | 75 % |
| **`hybrid`** (défaut) | **92 %** | **100 %** | **0,950** | 0 % | 75 % |

Lecture : la recherche par mots-clés répond à presque tout… y compris aux questions hors sujet dès qu'un mot est
partagé (« restaurant d'**Albi** », « billet de train **Albi**-**Toulouse** ») : elle ne sait pas dire « je ne sais
pas ». Le mode hybride garde la barrière sémantique et gagne sur les sigles et noms propres ; la tolérance de 0,01
pour les passages en tête du classement mots-clés fait passer « trouvé » de 95 % à 100 % sans laisser passer un
hors-sujet de plus (mesuré). Deux hors-sujet sur huit
passent encore (« un poème sur la mécanique » → CRITT Mécanique à 0,834 ; « le meilleur restaurant d'Albi » → Cnam
d'Albi à 0,828) alors que la question légitime la plus faible est à 0,832 : c'est la limite du modèle small. Le levier
n'est pas un seuil plus haut (il créerait des faux rejets) mais un modèle plus discriminant (`multilingual-e5-base`)
ou un réordonnancement par cross-encoder sur les 20 candidats.

## Configuration (variables d'environnement, préfixe `CHATBOT_`)

| Variable | Défaut | Rôle |
|---|---|---|
| `CORPUS_DIR` / `DATA_DIR` / `SEED_FILE` | `corpus` / `data` / `seed/organizations.json` | fiches / persistance (SQLite + Chroma) / annuaire de démarrage |
| `DB_PATH` | `<DATA_DIR>/chatbot.sqlite3` | base SQLite |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` | changer de modèle impose une réindexation et un recalibrage |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `ORG_CHUNK_SIZE` | `700` / `100` / `300` | découpage des fiches / des organisations (passages courts : une phrase = un vecteur) |
| `DEFAULT_MODE` | `hybrid` | mode de `/ask` sans `mode` explicite |
| `MIN_SCORE` | `0.825` | seuil de fiabilité (cosinus) |
| `HYBRID_TOLERANCE` / `HYBRID_KEYWORD_TOP` | `0.01` / `3` | tolérance sous le seuil pour les passages bien classés par mots-clés (0 = strict) |
| `CANDIDATE_POOL` | `20` | candidats examinés par question |
| `AUTO_SEED` / `AUTO_INGEST` | `true` / `true` | chargement de l'annuaire / construction de l'index au démarrage si vides |
| `API_KEY` | *(vide)* | **obligatoire hors développement** : protège `/admin/*` |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | origines du front |
| `ANALYTICS_RETENTION_DAYS` | `365` | purge du journal des questions |
| `LOG_LEVEL` | `INFO` | |

La configuration **métier** (nom, message d'accueil, suggestions initiales, activation des relances / de
l'orientation / des statistiques, nombre d'acteurs proposés, messages, catégories de besoins) est en base et se
modifie via `/admin/config` sans redémarrage.

## Confidentialité et sécurité

- Aucune donnée personnelle n'est demandée à l'usager. Le journal des questions ne contient ni IP ni identifiant
  nominatif ; le `session_id` éventuel (généré par le navigateur) est **haché avec un sel propre à l'installation** ;
  purge automatique après `ANALYTICS_RETENTION_DAYS` ; collecte désactivable dans la configuration.
- Les coordonnées de l'annuaire sont des contacts professionnels publiés par les partenaires ; leur validation et
  leur mise à jour relèvent de l'administrateur (persona RH / technicien).
- `/admin/*` exige `X-API-Key` (comparaison en temps constant) ; en production, placer l'API derrière un reverse
  proxy TLS et limiter le débit de `/ask`.
- Le conteneur tourne sans privilèges, hors ligne (modèle embarqué, `HF_HUB_OFFLINE=1`), avec un `HEALTHCHECK`.

## Traçabilité des exigences (recueil des besoins, § 5)

| Exigence | Réponse du back-end |
|---|---|
| REQ-FUNC.1 Recueil des besoins | `/ask` en langage libre ; détection de la catégorie de besoin ; relances et catégories proposées quand la demande est trop vague |
| REQ-FUNC.2 Orientation auto | jusqu'à 3 acteurs (labos, plateformes, écoles, centres techniques, financeurs…) + extrait documentaire, avec coordonnées |
| REQ-FUNC.3 Garantie qualité | seuil de fiabilité (jamais d'invention), `/feedback` (évaluation des réponses), questions sans réponse remontées dans `/admin/analytics`, `active` par acteur, `eval` rejouable |
| REQ-FUNC.4 Confidentialité | journal anonymisé et purgé, pas de données sensibles collectées, clé d'administration |
| REQ-FUNC.5 Connexion annuaire | annuaire structuré selon le MCD, import/export JSON en masse (upsert) pour la synchronisation avec l'annuaire régional |
| REQ-FUNC.6 Gestion accès | endpoints publics / endpoints d'administration protégés (une clé ; rôles Admin/Opérateur/RH = évolution) |
| REQ-NF.2 Performance | ~20-80 ms par question sur CPU (hors chargement initial du modèle ~10 s) |
| REQ-NF.4 Évolutivité | ajout d'un acteur = 1 requête, indexé immédiatement ; passage à `e5-base` ou à un reranker sans changer l'API |
| REQ-NF.5 Compatibilité | format d'échange JSON documenté (`/admin/organizations/export`), Swagger `/docs` |

## Tests

```bash
python -m pytest -q                                 # 43 tests (l'intégration API charge le vrai modèle, ~15 s)
CHATBOT_SKIP_MODEL_TESTS=1 python -m pytest -q      # unitaires seulement (annuaire, analytiques, config, assistant, découpage, BM25, RRF)
```

## Évolutions possibles

- Rôles d'administration distincts (Admin / Opérateurs / RH) et journal des modifications de l'annuaire.
- Modèle `multilingual-e5-base` ou réordonnancement cross-encoder si la marge du seuil doit s'élargir.
- Connecteur d'import depuis le format réel de l'annuaire régional (dès qu'il est connu) et synchronisation planifiée.
- Couche RAG optionnelle : le contrat `/ask` renvoie déjà passages + sources, une étape de rédaction (LLM local ou API)
  pourrait s'y brancher sans toucher à l'index, comme le prévoit la note de synthèse (« évolutivité »).
