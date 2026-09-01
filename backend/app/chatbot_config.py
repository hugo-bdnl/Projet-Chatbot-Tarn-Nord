"""Configuration MÉTIER du chatbot, modifiable à chaud par l'administrateur (persona « RH »).

Stockée en JSON dans la table `settings` ; les valeurs par défaut reproduisent la maquette du front.
"""

from __future__ import annotations

import json
import logging
import secrets

from .db import Database, utc_now
from .schemas import Category, ChatbotConfig

logger = logging.getLogger(__name__)

CONFIG_KEY = "chatbot"
SALT_KEY = "analytics_salt"

DEFAULT_CATEGORIES = [
    Category(name="Innovation & Financement",
             keywords=["aide", "aides", "innovation", "innover", "innovant", "financement", "financer",
                       "subvention", "prêt", "investissement", "investir", "accompagnement", "levée de fonds",
                       "crédit d'impôt", "brevet"],
             example_question="Je cherche des aides pour innover"),
    Category(name="Formation & RH",
             keywords=["rh", "ressources humaines", "recrutement", "recruter", "embauche", "embaucher",
                       "formation", "former", "compétences", "alternance", "apprentissage", "apprenti",
                       "mobilité", "logement", "salarié", "salariés", "talents"],
             example_question="Je recherche des solutions RH"),
    Category(name="Recherche technique",
             keywords=["pièce", "métallique", "fournisseur", "sous-traitant", "sous-traitance", "fabrication",
                       "usinage", "prototype", "prototypage", "matériau", "matériaux", "procédé", "laboratoire",
                       "essai", "essais", "impression 3d", "composite", "recherche", "r&d"],
             example_question="J'ai besoin d'une pièce métallique spécifique"),
    Category(name="Transition énergétique",
             keywords=["énergie", "énergétique", "environnement", "transition", "écologique", "décarbonation",
                       "carbone", "déchets", "solaire", "photovoltaïque", "chaleur", "consommation", "climat",
                       "rse"],
             example_question="J'ai un projet de transition énergétique"),
    Category(name="Foncier & Implantation",
             keywords=["foncier", "terrain", "implantation", "implanter", "extension", "agrandir",
                       "agrandissement", "locaux", "bâtiment", "zone d'activité", "permis de construire",
                       "déménager", "s'installer"],
             example_question="Je veux agrandir mon site de production"),
]


def default_config() -> ChatbotConfig:
    return ChatbotConfig(categories=[c.model_copy(deep=True) for c in DEFAULT_CATEGORIES])


class ConfigStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self) -> ChatbotConfig:
        with self.db.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (CONFIG_KEY,)).fetchone()
        if not row:
            return default_config()
        try:
            return ChatbotConfig.model_validate(json.loads(row["value"]))
        except Exception as exc:  # configuration corrompue : on repart des défauts sans bloquer le service
            logger.warning("Configuration chatbot illisible (%s) : valeurs par défaut utilisées", exc)
            return default_config()

    def save(self, config: ChatbotConfig) -> ChatbotConfig:
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (CONFIG_KEY, config.model_dump_json(), utc_now()),
            )
        return config

    def reset(self) -> ChatbotConfig:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM settings WHERE key = ?", (CONFIG_KEY,))
        return default_config()

    def analytics_salt(self) -> str:
        """Sel aléatoire, généré une fois par installation, pour hacher les identifiants de session."""
        with self.db.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (SALT_KEY,)).fetchone()
            if row:
                return str(row["value"])
            salt = secrets.token_hex(16)
            conn.execute("INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)", (SALT_KEY, salt, utc_now()))
            return salt
