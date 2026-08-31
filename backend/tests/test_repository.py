import pytest

from app.db import Database
from app.directory import DirectoryRepository, DuplicateOrganization
from app.directory.render import organization_card, organization_to_document, short_description
from app.schemas import ContactIn, DomainIn, DomainUpdate, OrganizationIn, SiteIn


@pytest.fixture
def repo(tmp_path):
    return DirectoryRepository(Database(tmp_path / "test.sqlite3"))


def _org(name="IMT Mines Albi", **extra) -> OrganizationIn:
    data = dict(
        name=name, description="École d'ingénieurs et centre de recherche. Travaille avec les entreprises.",
        website="https://example.org", keywords=["R&D", "stage"], domains=["Recherche", "Formation"],
        sites=[SiteIn(label="Campus", address="Allée des Sciences", postal_code="81013", city="Albi")],
        contacts=[ContactIn(first_name="Jean", last_name="Dupont", role="Relations entreprises",
                            email="contact@example.org", phone="05 00 00 00 00")],
    )
    data.update(extra)
    return OrganizationIn(**data)


def test_create_get_and_children(repo):
    org = repo.create(_org())
    assert org.id == 1 and org.active
    fetched = repo.get(org.id)
    assert fetched.name == "IMT Mines Albi"
    assert fetched.domains == ["Recherche", "Formation"]
    assert fetched.sites[0].city == "Albi" and fetched.sites[0].id > 0
    assert fetched.contacts[0].display_name == "Jean Dupont"
    assert repo.get_by_name("imt mines albi").id == org.id   # insensible à la casse
    assert repo.get(999) is None


def test_duplicate_name_is_rejected(repo):
    repo.create(_org())
    with pytest.raises(DuplicateOrganization):
        repo.create(_org(name="imt MINES albi"))


def test_update_replaces_children_and_domains(repo):
    org = repo.create(_org())
    updated = repo.update(org.id, _org(domains=["Innovation"], sites=[], contacts=[ContactIn(role="Accueil")]))
    assert updated.domains == ["Innovation"]
    assert updated.sites == []
    assert [c.role for c in updated.contacts] == ["Accueil"]
    assert updated.updated_at >= org.created_at
    assert repo.update(999, _org(name="Autre")) is None
    # le domaine « Recherche » n'est plus rattaché mais existe toujours (il garde sa description)
    assert {d.name: d.organizations for d in repo.list_domains()} == {"Formation": 0, "Innovation": 1, "Recherche": 0}


def test_list_filters(repo):
    repo.create(_org())
    repo.create(_org(name="AD'OCC", description="Agence de développement économique : aides et financement.",
                     domains=["Financement"], sites=[SiteIn(city="Toulouse")], active=True))
    repo.create(_org(name="Ancien acteur", active=False))
    assert repo.count() == 2 and repo.count(active_only=False) == 3
    total, items = repo.list(q="toulouse")
    assert total == 1 and items[0].name == "AD'OCC"
    assert repo.list(q="financement")[0] == 1
    assert repo.list(domain="Recherche")[0] == 1
    assert repo.list(active=None)[0] == 3
    assert [o.name for o in repo.list(limit=1, offset=1)[1]] == ["IMT Mines Albi"]   # tri par nom
    assert repo.names() == [(2, "AD'OCC"), (1, "IMT Mines Albi")] or set(repo.names()) == {(1, "IMT Mines Albi"), (2, "AD'OCC")}


def test_delete_cascades(repo):
    org = repo.create(_org())
    assert repo.delete(org.id) is True
    assert repo.delete(org.id) is False
    with repo.db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM organization_domains").fetchone()[0] == 0


def test_import_many_upserts_and_replaces(repo):
    repo.create(_org())
    result = repo.import_many([_org(description="Nouvelle description"), _org(name="CCI du Tarn")])
    assert (result.created, result.updated, result.deleted) == (1, 1, 0)
    assert repo.get_by_name("IMT Mines Albi").description == "Nouvelle description"
    result = repo.import_many([_org(name="CCI du Tarn")], replace=True)
    assert (result.created, result.updated, result.deleted) == (0, 1, 1)
    assert [o.name for o in repo.all_active()] == ["CCI du Tarn"]


def test_domains_descriptions(repo):
    repo.upsert_domains([DomainIn(name="Recherche", description="Laboratoires et centres de recherche.")])
    repo.create(_org())
    domains = {d.name: d for d in repo.list_domains()}
    assert domains["Recherche"].description.startswith("Laboratoires")
    assert domains["Recherche"].organizations == 1
    updated = repo.update_domain(domains["Formation"].id, DomainUpdate(description="Formation continue."))
    assert updated.description == "Formation continue."
    with pytest.raises(DuplicateOrganization):
        repo.update_domain(domains["Formation"].id, DomainUpdate(name="recherche"))


def test_render_document_and_card(repo):
    org = repo.create(_org())
    doc = organization_to_document(org)
    assert doc.doc_id == f"org:{org.id}" and doc.kind == "organization" and doc.title == org.name
    assert "Domaines d'activité : Recherche, Formation." in doc.text
    assert "Albi" not in doc.text                 # villes non indexées (voir render.py)
    assert "05 00 00 00 00" not in doc.text          # coordonnées non indexées
    card = organization_card(org)
    assert card.startswith("IMT Mines Albi")
    assert "Adresse (Campus) : Allée des Sciences, 81013 Albi" in card
    assert "Contact : Jean Dupont (Relations entreprises) — contact@example.org — 05 00 00 00 00" in card
    assert "Site web : https://example.org" in card


def test_short_description():
    assert short_description("Première phrase. Deuxième phrase.") == "Première phrase."
    long = "Mot " * 100
    assert short_description(long, max_len=40).endswith("…") and len(short_description(long, max_len=40)) <= 41
    assert short_description("   ") == ""
