"""Back-end du chatbot territorial (Grand Albigeois) — orientation des industriels vers les acteurs
de l'innovation par recherche sémantique, SANS IA générative.

    annuaire (SQLite : organisations, sites, contacts, domaines)  ─┐
    fiches Markdown (corpus/)                                      ─┴─► passages ─► embeddings ─► index ChromaDB
    besoin exprimé ─► embedding ─► acteurs / fiches les plus proches ─► seuil de fiabilité ─► réponse templatée

Toute réponse est assemblée à partir de données existantes (fiche d'organisation, extrait de document) :
le système ne rédige rien et n'invente jamais de contenu.
"""

__version__ = "0.2.0"
