"""Test d'intégration de l'API avec le vrai modèle d'embedding (lent : ~15 s + téléchargement du modèle la
première fois). Désactivable avec CHATBOT_SKIP_MODEL_TESTS=1."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.skipif(os.getenv("CHATBOT_SKIP_MODEL_TESTS") == "1",
                                reason="tests nécessitant le modèle désactivés")

MIN_SCORE = 0.825
KEY = {"X-API-Key": "secret-test"}

DOCS = {
    "aides.md": "# Financer un projet d'innovation\n\n## Par où commencer\n\nPour financer un projet innovant, "
                "contactez d'abord l'agence régionale : elle identifie les subventions et avances remboursables "
                "mobilisables et oriente vers les financeurs.",
    "energie.md": "# Réduire la consommation d'énergie de son usine\n\n## Diagnostic\n\nCommencez par un diagnostic "
                  "énergétique du site : consommations d'électricité et de gaz, récupération de chaleur, "
                  "isolation, éclairage.",
}

SEED = {
    "domains": [{"name": "Financement", "description": "Aides et prêts."}],
    "organizations": [
        {"name": "Labo Matériaux Test",
         "description": "Laboratoire de recherche en matériaux métalliques et composites : essais mécaniques, "
                        "fabrication additive, réalisation de prototypes de pièces pour les industriels.",
         "domains": ["Recherche", "Matériaux & Procédés"], "keywords": ["pièce métallique", "prototype"],
         "sites": [{"label": "Campus", "address": "1 allée des Sciences", "postal_code": "81000", "city": "Albi"}],
         "contacts": [{"role": "Relations entreprises", "email": "labo@example.org", "phone": "05 00 00 00 01"}],
         "website": "https://labo.example.org"},
        {"name": "Agence Aides Test",
         "description": "Agence publique qui finance l'innovation des entreprises : subventions, avances "
                        "remboursables et prêts pour les projets innovants et l'investissement.",
         "domains": ["Financement"], "sites": [{"city": "Toulouse"}],
         "contacts": [{"first_name": "Marie", "last_name": "Durand", "email": "aides@example.org"}]},
        {"name": "Centre Formation Test",
         "description": "Centre de formation professionnelle des métiers de l'industrie : apprentissage, "
                        "alternance, formation continue des salariés en usinage et maintenance.",
         "domains": ["Formation", "Recrutement & RH"], "sites": [{"city": "Albi"}]},
    ],
}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("chatbot")
    corpus = root / "corpus"
    corpus.mkdir()
    for name, text in DOCS.items():
        (corpus / name).write_text(text, encoding="utf-8")
    seed = root / "seed.json"
    seed.write_text(json.dumps(SEED, ensure_ascii=False), encoding="utf-8")
    settings = Settings(corpus_dir=corpus, data_dir=root / "data", seed_file=seed, api_key="secret-test",
                        min_score=MIN_SCORE, _env_file=None)
    with TestClient(create_app(settings)) as c:
        yield c


def test_health_after_seed_and_auto_index(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["documents"] == 2 and body["organizations"] == 3
    assert body["passages"] >= 5


def test_public_config_defaults(client):
    body = client.get("/config").json()
    assert body["name"] == "Assistant Grand Albigeois"
    assert len(body["initial_suggestions"]) == 4 and body["suggestions_enabled"] is True


def test_ask_orients_towards_organizations_and_documents(client):
    r = client.post("/ask", json={"question": "Je cherche des aides pour financer mon projet innovant",
                                  "session_id": "s1", "debug": True})
    assert r.status_code == 200
    body = r.json()
    assert body["answered"] is True and body["intent"] == "orientation"
    assert body["organizations"][0]["name"] == "Agence Aides Test"
    assert body["organizations"][0]["contacts"][0]["email"] == "aides@example.org"
    assert body["category"] == "Innovation & Financement"
    assert "Agence Aides Test" in body["answer"] and body["answer"].startswith("Voici les acteurs")
    assert "En savoir plus sur Agence Aides Test" in body["suggestions"]
    assert body["query_id"] is not None
    assert body["mode"] == "hybrid"                               # mode par défaut
    assert body["organizations"][0]["score"] >= MIN_SCORE         # score exposé = similarité cosinus
    assert body["hits"] and all(h["semantic_score"] is not None for h in body["hits"])
    if body["documents"]:   # l'extrait éventuel est le texte exact du document, jamais généré
        assert body["documents"][0]["text"] in DOCS["aides.md"]


def test_ask_named_organization_returns_its_card(client):
    body = client.post("/ask", json={"question": "En savoir plus sur Labo Matériaux Test"}).json()
    assert body["intent"] == "organization" and body["answered"] is True
    assert body["organizations"][0]["name"] == "Labo Matériaux Test"
    assert "Adresse (Campus) : 1 allée des Sciences, 81000 Albi" in body["answer"]
    assert "labo@example.org" in body["answer"] and "Site web : https://labo.example.org" in body["answer"]
    assert body["suggestions"] == ["Quels autres acteurs en Recherche ?", "Quels autres acteurs en Matériaux & Procédés ?"]


def test_ask_off_topic_is_refused_with_category_suggestions(client):
    body = client.post("/ask", json={"question": "Quelle est la capitale de l'Australie ?", "session_id": "s2"}).json()
    assert body["answered"] is False and body["intent"] == "no_answer"
    assert body["organizations"] == [] and body["documents"] == []
    assert "Je n'ai pas trouvé" in body["answer"] and "• Innovation & Financement" in body["answer"]
    assert "Je cherche des aides pour innover" in body["suggestions"]


def test_ask_keyword_mode(client):
    body = client.post("/ask", json={"question": "apprentissage alternance usinage", "mode": "keyword"}).json()
    assert body["answered"] is True and body["organizations"][0]["name"] == "Centre Formation Test"
    ko = client.post("/ask", json={"question": "Quand puis-je venir vous voir ?", "mode": "keyword"}).json()
    assert ko["answered"] is False


def test_ask_validation(client):
    assert client.post("/ask", json={"question": "a"}).status_code == 422
    assert client.post("/ask", json={"question": "ok ?", "mode": "magic"}).status_code == 422
    assert client.post("/ask", json={"question": "ok ?", "max_organizations": 0}).status_code == 422


def test_feedback_and_analytics(client):
    body = client.post("/ask", json={"question": "Où trouver un prototype de pièce métallique ?",
                                     "session_id": "s1"}).json()
    assert client.post("/feedback", json={"query_id": body["query_id"], "helpful": True}).json() == {"ok": True}
    assert client.post("/feedback", json={"query_id": 99999, "helpful": True}).status_code == 404

    assert client.get("/admin/analytics").status_code == 401
    assert client.get("/admin/analytics", headers={"X-API-Key": "wrong"}).status_code == 401
    s = client.get("/admin/analytics?days=7", headers=KEY).json()
    assert s["totals"]["conversations"] >= 4
    assert s["totals"]["unique_sessions"] >= 2
    assert s["totals"]["feedback_count"] >= 1 and s["totals"]["satisfaction_rate"] == 1.0
    assert any(q["question"] == "Quelle est la capitale de l'Australie ?" for q in s["unanswered_questions"])
    assert any(c["name"] == "Innovation & Financement" for c in s["categories"])
    assert s["top_organizations"] and len(s["per_day"]) == 7
    recent = client.get("/admin/analytics/questions?answered=false", headers=KEY).json()
    assert recent["total"] >= 1 and recent["items"][0]["answered"] is False


def test_public_directory_endpoints(client):
    listing = client.get("/organizations?q=formation").json()
    assert listing["total"] == 1 and listing["items"][0]["name"] == "Centre Formation Test"
    assert client.get("/organizations", params={"domain": "Financement"}).json()["total"] == 1
    org_id = listing["items"][0]["id"]
    assert client.get(f"/organizations/{org_id}").json()["domains"] == ["Formation", "Recrutement & RH"]
    assert client.get("/organizations/9999").status_code == 404
    domains = {d["name"]: d for d in client.get("/domains").json()}
    assert domains["Financement"]["description"] == "Aides et prêts." and domains["Financement"]["organizations"] == 1
    docs = client.get("/documents").json()
    assert sorted(d["doc_id"] for d in docs if d["kind"] == "document") == ["aides.md", "energie.md"]
    assert sum(1 for d in docs if d["kind"] == "organization") == 3


def test_admin_crud_updates_the_index_incrementally(client):
    payload = {"name": "Bureau Énergie Test",
               "description": "Bureau d'études qui installe des panneaux solaires photovoltaïques sur les toitures "
                              "des usines et accompagne l'autoconsommation.",
               "domains": ["Énergie & Environnement"], "sites": [{"city": "Albi"}]}
    assert client.post("/admin/organizations", json=payload).status_code == 401
    r = client.post("/admin/organizations", json=payload, headers=KEY)
    assert r.status_code == 201
    org_id = r.json()["id"]
    assert client.post("/admin/organizations", json=payload, headers=KEY).status_code == 409

    body = client.post("/ask", json={"question": "Je veux installer des panneaux solaires sur le toit de mon usine"}).json()
    assert [o["name"] for o in body["organizations"]][:1] == ["Bureau Énergie Test"]

    payload["active"] = False
    assert client.put(f"/admin/organizations/{org_id}", json=payload, headers=KEY).json()["active"] is False
    body = client.post("/ask", json={"question": "Je veux installer des panneaux solaires sur le toit de mon usine"}).json()
    assert all(o["name"] != "Bureau Énergie Test" for o in body["organizations"])
    assert client.get(f"/organizations/{org_id}").status_code == 404          # inactive = invisible au public
    assert client.get("/admin/organizations?active=false", headers=KEY).json()["total"] == 1

    assert client.delete(f"/admin/organizations/{org_id}", headers=KEY).status_code == 204
    assert client.delete(f"/admin/organizations/{org_id}", headers=KEY).status_code == 404
    assert client.put("/admin/organizations/9999", json=payload, headers=KEY).status_code == 404
    assert client.get("/health").json()["organizations"] == 3


def test_admin_export_import_and_reindex(client):
    export = client.get("/admin/organizations/export", headers=KEY).json()
    assert len(export) == 3 and {"created_at", "updated_at", "id"} <= set(export[0])
    r = client.post("/admin/organizations/import", json={"organizations": export, "replace": True}, headers=KEY)
    assert r.status_code == 200
    assert r.json()["updated"] == 3 and r.json()["created"] == 0 and r.json()["deleted"] == 0
    r = client.post("/admin/reindex", headers=KEY).json()
    assert r["documents"] == 2 and r["organizations"] == 3 and r["passages"] >= 5


def test_admin_config_roundtrip_changes_public_behaviour(client):
    cfg = client.get("/admin/config", headers=KEY).json()
    cfg["name"] = "Bot Test"
    cfg["suggestions_enabled"] = False
    assert client.put("/admin/config", json=cfg, headers=KEY).status_code == 200
    public = client.get("/config").json()
    assert public["name"] == "Bot Test" and public["initial_suggestions"] == []
    body = client.post("/ask", json={"question": "Je cherche des aides pour financer mon projet innovant"}).json()
    assert body["suggestions"] == []
    assert client.post("/admin/config/reset", headers=KEY).json()["name"] == "Assistant Grand Albigeois"
    assert client.get("/config").json()["suggestions_enabled"] is True
    assert client.put("/admin/config", json={"max_organizations": 50}, headers=KEY).status_code == 422
