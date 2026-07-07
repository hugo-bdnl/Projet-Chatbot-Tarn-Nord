# Projet Chatbot Tarn Nord

Chatbot territorial pour orienter les industriels vers l'écosystème d'innovation du territoire.

## Structure du dépôt

```
Projet-Chatbot-Tarn-Nord/
├── frontend/          # Interface React (maquette Figma Make → app de prod)
└── backend/           # À venir — API recherche sémantique (équipe backend)
```

Les documents projet (recueil des besoins, présentation client) sont **hors dépôt**, dans le dossier voisin `../besoins/`.

## Maquette de référence

https://www.figma.com/make/018jY1n0vwxrkcCOPVfguN/Chatbot-territorial

## Démarrage rapide (frontend)

```bash
cd frontend
npm install
npm run dev
```

| Route    | Description                          |
|----------|--------------------------------------|
| `/`      | Chat public                          |
| `/admin` | Back-office (annuaire, stats, config)|

## Équipe

- **Frontend** : dossier `frontend/`
- **Backend** : recherche sémantique sur documents territoriaux (voir benchmark projet)
