from datetime import date, timedelta

import pytest

from app.analytics import Analytics, normalize_question
from app.chatbot_config import ConfigStore, default_config
from app.db import Database
from app.schemas import ChatbotConfig


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.sqlite3")


def _log(a: Analytics, question: str, answered: bool = True, session: str | None = None, category=None) -> int:
    return a.log(question=question, answered=answered, intent="orientation" if answered else "no_answer",
                 category=category, top_score=0.9 if answered else 0.7, latency_ms=20.0, mode="semantic",
                 organizations=["IMT Mines Albi"] if answered else [], session_id=session)


def test_normalize_question():
    assert normalize_question("  Quelles   AIDES pour innover ?? ") == "quelles aides pour innover"


def test_log_feedback_and_summary(db):
    a = Analytics(db, salt="s", retention_days=30)
    q1 = _log(a, "Je cherche des aides pour innover", session="abc", category="Innovation & Financement")
    _log(a, "je cherche des aides pour innover ?", session="abc", category="Innovation & Financement")
    q3 = _log(a, "Quelle est la météo ?", answered=False, session="xyz")
    assert a.feedback(q1, True) and a.feedback(q3, False, "pas utile")
    assert a.feedback(999, True) is False

    s = a.summary(days=7)
    assert s.totals.conversations == 3 and s.totals.unique_sessions == 2 and s.totals.answered == 2
    assert s.totals.answer_rate == pytest.approx(0.667, abs=0.001)
    assert s.totals.feedback_count == 2 and s.totals.satisfaction_rate == 0.5
    assert s.totals.avg_latency_ms == 20.0
    assert s.previous.conversations == 0 and s.previous.answer_rate is None
    assert len(s.per_day) == 7 and s.per_day[-1].date == date.today().isoformat() and s.per_day[-1].count == 3
    assert s.top_questions[0].count == 2                      # les deux formulations sont regroupées
    assert [q.question for q in s.unanswered_questions] == ["Quelle est la météo ?"]
    assert {c.name: c.count for c in s.categories} == {"Innovation & Financement": 2, "Autre": 1}
    assert s.top_organizations[0].name == "IMT Mines Albi" and s.top_organizations[0].count == 2
    assert len(s.latency_by_hour) == 1 and s.latency_by_hour[0].count == 3

    recent = a.recent(limit=10, answered=False)
    assert recent.total == 1 and recent.items[0].helpful is False and recent.items[0].feedback_comment == "pas utile"
    assert a.recent().items[0].id == q3   # plus récent d'abord


def test_session_hash_is_salted_and_never_stores_raw_id(db):
    a = Analytics(db, salt="secret", retention_days=30)
    _log(a, "q", session="user-42")
    with db.connect() as conn:
        row = conn.execute("SELECT session_hash FROM queries").fetchone()
    assert row["session_hash"] and "user-42" not in row["session_hash"]
    b = Analytics(db, salt="other", retention_days=30)
    _log(b, "q", session="user-42")
    assert a.summary(1).totals.unique_sessions == 2   # sel différent -> hachés différents


def test_purge_respects_retention(db):
    a = Analytics(db, salt="s", retention_days=10)
    _log(a, "récente")
    old = (date.today() - timedelta(days=30)).isoformat()
    with db.connect() as conn:
        conn.execute("UPDATE queries SET ts = ?, local_date = ? WHERE id = 1", (old + "T10:00:00+00:00", old))
        _ = conn
    _log(a, "nouvelle")
    assert a.purge() == 1
    assert a.recent().total == 1


def test_config_store_roundtrip_and_reset(db):
    store = ConfigStore(db)
    assert store.get() == default_config()
    cfg = store.get()
    cfg.name = "Bot test"
    cfg.categories = cfg.categories[:2]
    store.save(cfg)
    assert store.get().name == "Bot test" and len(store.get().categories) == 2
    assert store.reset().name == ChatbotConfig().name
    assert store.get().name == "Assistant Grand Albigeois"
    salt = store.analytics_salt()
    assert len(salt) == 32 and store.analytics_salt() == salt
