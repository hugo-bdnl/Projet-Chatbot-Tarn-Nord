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

## Prochaines étapes dev

1. Fidélité visuelle à la maquette Figma
2. Remplacer les réponses simulées (`getBotResponse`) par des appels API
3. Afficher les **sources documentaires** renvoyées par le backend (recherche sémantique)
4. Brancher le CRUD annuaire admin sur l'API
