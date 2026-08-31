"""Configuration technique centralisée. Toutes les variables sont surchargeables par l'environnement
avec le préfixe CHATBOT_ (ex. CHATBOT_MIN_SCORE=0.85) ou via un fichier .env.

La configuration MÉTIER du chatbot (nom, message d'accueil, catégories de besoins…) n'est pas ici :
elle est modifiable à chaud par l'administrateur via l'API (/admin/config) et stockée en base.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHATBOT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Données ---------------------------------------------------------
    corpus_dir: Path = Field(default=Path("corpus"), description="Fiches documentaires (md/txt/html/pdf)")
    data_dir: Path = Field(default=Path("data"), description="Persistance : index ChromaDB + base SQLite")
    db_path: Path | None = Field(default=None, description="Base SQLite (défaut : <data_dir>/chatbot.sqlite3)")
    seed_file: Path = Field(default=Path("seed/organizations.json"),
                            description="Annuaire de démarrage, chargé si la base est vide")
    collection_name: str = "passages"

    # --- Modèle d'embedding (français / multilingue, tourne sur CPU) ----
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_batch_size: int = 32

    # --- Découpage en passages -----------------------------------------
    chunk_size: int = Field(default=700, ge=100, description="Taille cible d'un passage (caractères)")
    chunk_overlap: int = Field(default=100, ge=0, description="Chevauchement entre passages (caractères)")
    org_chunk_size: int = Field(default=300, ge=80,
                                description="Passages plus courts pour les fiches d'organisation : chaque phrase "
                                            "de la description devient un vecteur, ce qui évite qu'un acteur "
                                            "polyvalent soit noyé dans une description longue")

    # --- Recherche -------------------------------------------------------
    default_mode: str = Field(default="hybrid", pattern="^(semantic|keyword|hybrid)$",
                              description="Mode utilisé par /ask quand la requête n'en précise pas. `hybrid` = "
                                          "classement sémantique + BM25 (RRF) avec barrière de fiabilité "
                                          "sémantique ; mesuré légèrement meilleur que `semantic` seul "
                                          "(acronymes, noms propres)")
    default_top_k: int = Field(default=3, ge=1, le=20, description="Passages renvoyés en mode debug / CLI")
    candidate_pool: int = Field(default=20, ge=5, le=100,
                                description="Candidats examinés par question (et par moteur avant fusion hybride)")
    min_score: float = Field(
        default=0.825, ge=0.0, le=1.0,
        description="Similarité cosinus minimale pour considérer un acteur / un extrait comme pertinent. "
                    "En dessous, le chatbot répond qu'il n'a pas trouvé plutôt que d'inventer. "
                    "À recalibrer avec `python -m app.cli eval -v` après toute évolution de l'annuaire.",
    )
    rrf_k: int = Field(default=60, description="Constante k de la Reciprocal Rank Fusion (mode hybride)")
    hybrid_tolerance: float = Field(
        default=0.01, ge=0.0, le=0.05,
        description="Mode hybride : un passage classé dans les `hybrid_keyword_top` premiers par mots-clés est "
                    "accepté jusqu'à cette distance sous min_score (accord lexical + sémantique quasi au seuil). "
                    "0 = barrière sémantique stricte.")
    hybrid_keyword_top: int = Field(default=3, ge=1, le=10)

    # --- Démarrage -------------------------------------------------------
    auto_seed: bool = Field(default=True, description="Charger seed_file si l'annuaire est vide")
    auto_ingest: bool = Field(default=True, description="Construire l'index au démarrage s'il est vide")

    # --- API -------------------------------------------------------------
    api_key: str = Field(default="", description="Clé attendue dans le header X-API-Key sur /admin/* "
                                                 "(vide = administration ouverte, réservé au développement)")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Origines CORS autorisées, séparées par des virgules ('*' pour tout autoriser)",
    )
    analytics_retention_days: int = Field(default=365, ge=1,
                                          description="Durée de conservation du journal des questions")
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def db_file(self) -> Path:
        return self.db_path or (self.data_dir / "chatbot.sqlite3")


def get_settings() -> Settings:
    return Settings()
