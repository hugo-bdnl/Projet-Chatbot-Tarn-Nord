# Frontend — Chatbot territorial

Application React basée sur la [maquette Figma Make](https://www.figma.com/make/018jY1n0vwxrkcCOPVfguN/Chatbot-territorial).

## Stack

- React 18 + TypeScript
- Vite 6
- Tailwind CSS 4 + shadcn/ui (Radix)
- React Router 7
- Recharts (tableau de bord admin)

## Commandes

```bash
npm install
npm run dev      # développement
npm run build    # build production
```

## Configuration API

Copier `.env.example` vers `.env` et renseigner l'URL du backend :

```
VITE_API_URL=http://localhost:8000
```

Sans `.env`, le front appelle `http://localhost:8000` par défaut. Le backend autorise en CORS les origines
`http://localhost:5173` et `http://localhost:3000` (`CHATBOT_CORS_ORIGINS` pour en ajouter).

## Appels à l'API

Tous les appels passent par `src/app/lib/api.ts` (types, gestion d'erreur, en-tête `X-API-Key`) :

| Écran | Appels |
|---|---|
| `ChatInterface` | `GET /config` au chargement (nom, accueil, suggestions) · `POST /ask` à chaque question · `POST /feedback` sur le pouce haut/bas |
| `admin › Annuaire` | `GET /admin/organizations` (recherche `q` et filtre `domain` côté serveur), `POST`/`PUT`/`DELETE`, `GET /domains` |
| `admin › Analytiques` | `GET /admin/analytics?days=7\|30\|90` |
| `admin › Configuration` | `GET`/`PUT /admin/config`, `POST /admin/config/reset` |
| `admin` (bandeau) | `GET /health` pour l'état du service, et saisie de la clé d'administration |

Deux règles tenues côté interface :

- **aucune réponse de secours écrite en dur** : si l'API est injoignable ou renvoie une erreur, le chat affiche
  l'erreur. Le chatbot n'affiche que ce que le serveur a validé ;
- **l'identifiant de session** envoyé à `/ask` est tiré au hasard et garde la durée de l'onglet ; le serveur n'en
  stocke qu'une empreinte salée, pour compter les visiteurs distincts (REQ-FUNC.4).

## Prochaines étapes dev

1. Fidélité visuelle à la maquette Figma
2. Import / export JSON de l'annuaire depuis le back-office (`/admin/organizations/import|export`)
3. Rôles Admin / Opérateur / RH (aujourd'hui une seule clé d'administration)
4. Widget intégrable pour le site de l'agglomération
