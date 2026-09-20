# Projet Chatbot Tarn Nord

Chatbot territorial pour orienter les industriels vers l'écosystème d'innovation du territoire (Grand Albigeois).

## Structure du dépôt

```
Projet-Chatbot-Tarn-Nord/
├── frontend/          # Interface React (maquette Figma Make → app de prod)
└── backend/           # API FastAPI : annuaire + recherche sémantique (sans IA générative)
```

Les documents projet (recueil des besoins, présentation client) sont **hors dépôt**, dans le dossier voisin `../besoins/`.

## Maquette de référence

https://www.figma.com/make/018jY1n0vwxrkcCOPVfguN/Chatbot-territorial

## Démarrage rapide

### Backend (API, port 8000)

```bash
cd backend
docker compose up -d --build        # ~5 min la 1re fois (modèle d'embedding embarqué dans l'image)
curl http://localhost:8000/health   # Swagger : http://localhost:8000/docs
```

Sans Docker : voir [`backend/README.md`](backend/README.md) (venv Python 3.12+, `uvicorn app.main:app --reload`).
Au premier démarrage, l'annuaire de démarrage (`backend/seed/organizations.json`) et les fiches (`backend/corpus/`)
sont chargés et indexés automatiquement.

### Frontend (Vite, port 5173)

```bash
cd frontend
cp .env.example .env                # VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

| Route    | Description                          |
|----------|--------------------------------------|
| `/`      | Chat public                          |
| `/admin` | Back-office (annuaire, stats, config)|

## Contrat front ↔ back (implémenté)

Le front appelle réellement l'API : tout passe par le client [`frontend/src/app/lib/api.ts`], qui lit l'URL du
backend dans `VITE_API_URL`. Il n'y a plus aucune réponse écrite en dur côté interface : si le service est
injoignable, le chat l'affiche au lieu d'inventer une réponse.

| Écran front | Endpoints backend |
|---|---|
| Chat (`/`) | `GET /config` (nom, message d'accueil, suggestions initiales) · `POST /ask` → `answer`, `organizations[]`, `documents[]`, `suggestions[]`, `query_id` · `POST /feedback` (pouce haut/bas) |
| Admin › Annuaire | `GET/POST /admin/organizations`, `PUT/DELETE /admin/organizations/{id}`, import/export JSON, `GET /domains` |
| Admin › Analytiques | `GET /admin/analytics?days=7` (conversations/jour, sujets, questions fréquentes et sans réponse, satisfaction, latence) |
| Admin › Configuration | `GET/PUT /admin/config`, `POST /admin/config/reset` |

Les endpoints `/admin/*` exigent le header `X-API-Key` (variable `CHATBOT_API_KEY` du backend). La clé se saisit
dans le bandeau en haut de `/admin` : elle reste dans le navigateur de l'administrateur et n'est jamais écrite dans
le code ni dans un fichier du dépôt. Tant que `CHATBOT_API_KEY` n'est pas définie côté serveur, le back-office
fonctionne sans clé (mode développement). Détails, exemples et règles de fiabilité dans
[`backend/README.md`](backend/README.md).

## Équipe

- **Frontend** : dossier `frontend/`
- **Backend** : dossier `backend/` — annuaire (MCD du recueil des besoins) + recherche sémantique sur l'annuaire et les fiches documentaires (voir benchmark projet)
