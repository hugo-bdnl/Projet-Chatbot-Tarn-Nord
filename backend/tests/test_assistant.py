"""Tests de la couche conversationnelle qui ne nécessitent pas le modèle d'embedding."""

import pytest

from app.assistant import Assistant, _aliases, detect_category, normalize
from app.chatbot_config import default_config
from app.db import Database
from app.directory import DirectoryRepository
from app.schemas import OrganizationIn


@pytest.fixture
def repo(tmp_path):
    r = DirectoryRepository(Database(tmp_path / "t.sqlite3"))
    r.create(OrganizationIn(name="IMT Mines Albi", description="École d'ingénieurs.", domains=["Recherche"]))
    r.create(OrganizationIn(name="Institut Clément Ader (ICA) – site d'Albi", description="Laboratoire."))
    r.create(OrganizationIn(name="AD'OCC", description="Agence régionale."))
    r.create(OrganizationIn(name="Région Occitanie – Direction du développement économique", description="Région."))
    r.create(OrganizationIn(name="Centre RAPSODEE (IMT Mines Albi – CNRS)", description="Centre de recherche."))
    r.create(OrganizationIn(name="France Travail – Agence d'Albi", description="Emploi."))
    return r


@pytest.fixture
def assistant(repo):
    # ni moteur ni journal : seules les fonctions indépendantes de l'index sont exercées
    return Assistant(engine=None, repo=repo, config_store=None, analytics=None, settings=None)


def test_normalize_and_aliases():
    assert normalize("  L’École  d'Ingénieurs ") == "l'ecole d'ingenieurs"
    ica = _aliases("Institut Clément Ader (ICA) – site d'Albi")
    assert {"institut clement ader (ica) – site d'albi", "institut clement ader", "ica"} <= set(ica)
    assert _aliases("Institut Clément Ader (ICA)") == ["institut clement ader (ica)", "institut clement ader", "ica"]
    assert "france travail" in _aliases("France Travail – Agence d'Albi")
    # le contenu « IMT Mines Albi – CNRS » n'est pas un sigle : il ne devient pas un alias de RAPSODEE
    rapsodee = _aliases("Centre RAPSODEE (IMT Mines Albi – CNRS)")
    assert "imt mines albi" not in rapsodee and "centre rapsodee" in rapsodee


def test_named_organization_detects_short_requests(assistant):
    assert assistant.named_organization("En savoir plus sur IMT Mines Albi").name == "IMT Mines Albi"
    assert assistant.named_organization("contact AD'OCC").name == "AD'OCC"
    assert assistant.named_organization("Coordonnées de l’AD’OCC ?").name == "AD'OCC"
    assert assistant.named_organization("institut clement ader").name.startswith("Institut Clément Ader")
    assert assistant.named_organization("Contact de l'ICA ?").name.startswith("Institut Clément Ader")
    assert assistant.named_organization("Comment joindre France Travail ?").name == "France Travail – Agence d'Albi"
    assert assistant.named_organization("Le centre RAPSODEE").name.startswith("Centre RAPSODEE")


def test_named_organization_ignores_real_questions(assistant):
    # l'acteur est cité mais la question porte sur autre chose : on passe par la recherche
    q = "Quelles aides de la Région Occitanie pour financer un gros programme d'investissement productif ?"
    assert assistant.named_organization(q) is None
    assert assistant.named_organization("Je cherche un fournisseur de pièces") is None
    assert assistant.named_organization("IMT") is None   # trop court / pas un alias complet


def test_detect_category_from_question_then_from_organizations(repo):
    cfg = default_config()
    assert detect_category("Je cherche des aides pour innover", cfg, []) == "Innovation & Financement"
    assert detect_category("J'ai besoin d'une pièce métallique spécifique", cfg, []) == "Recherche technique"
    assert detect_category("Un nouvel embauché cherche un logement", cfg, []) == "Formation & RH"
    assert detect_category("Je veux agrandir mon atelier", cfg, []) == "Foncier & Implantation"
    assert detect_category("Bonjour", cfg, []) is None
    org = repo.get_by_name("IMT Mines Albi")
    org.keywords = ["thèse CIFRE", "laboratoire"]
    assert detect_category("Bonjour", cfg, [org]) == "Recherche technique"
    cfg.categories = []
    assert detect_category("aides", cfg, []) is None
