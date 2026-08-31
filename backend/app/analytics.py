"""Journal des questions (anonymisé) et statistiques pour le tableau de bord administrateur.

Confidentialité (REQ-FUNC.4) : aucune adresse IP ni donnée nominative n'est enregistrée ; l'identifiant
de session éventuellement fourni par le widget est haché avec un sel propre à l'installation ; le journal
est purgé au-delà de CHATBOT_ANALYTICS_RETENTION_DAYS ; la collecte se désactive dans la configuration.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from .db import Database, utc_now
from .schemas import (AnalyticsSummary, DayCount, HourLatency, NamedCount, PeriodTotals, QueryList,
                      QueryRecord, QuestionCount)

_PUNCT = re.compile(r"[\s\?\!\.\,\;\:]+$")


def normalize_question(text: str) -> str:
    return _PUNCT.sub("", " ".join(text.lower().split()))


class Analytics:
    def __init__(self, db: Database, salt: str, retention_days: int = 365) -> None:
        self.db = db
        self.salt = salt
        self.retention_days = retention_days

    # ------------------------------------------------------------- écriture
    def log(self, *, question: str, answered: bool, intent: str, category: str | None, top_score: float | None,
            latency_ms: float, mode: str, organizations: list[str], session_id: str | None) -> int:
        now_local = datetime.now().astimezone()
        session_hash = None
        if session_id:
            session_hash = hashlib.sha256(f"{self.salt}:{session_id}".encode("utf-8")).hexdigest()[:32]
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO queries (ts, local_date, local_hour, question, question_norm, answered, intent, "
                "category, top_score, latency_ms, mode, organizations, session_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (utc_now(), now_local.strftime("%Y-%m-%d"), now_local.hour, question[:1000],
                 normalize_question(question)[:1000], int(answered), intent, category, top_score,
                 latency_ms, mode, json.dumps(organizations, ensure_ascii=False), session_hash),
            )
            return int(cur.lastrowid)

    def feedback(self, query_id: int, helpful: bool, comment: str | None = None) -> bool:
        with self.db.connect() as conn:
            cur = conn.execute(
                "UPDATE queries SET helpful = ?, feedback_comment = ?, feedback_ts = ? WHERE id = ?",
                (int(helpful), (comment or None), utc_now(), query_id),
            )
            return cur.rowcount > 0

    def purge(self) -> int:
        limit = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat(timespec="seconds")
        with self.db.connect() as conn:
            return conn.execute("DELETE FROM queries WHERE ts < ?", (limit,)).rowcount

    # -------------------------------------------------------------- lecture
    def summary(self, days: int = 7) -> AnalyticsSummary:
        days = max(1, days)
        today = datetime.now().astimezone().date()
        start = today - timedelta(days=days - 1)
        prev_start = start - timedelta(days=days)
        with self.db.connect() as conn:
            totals = self._totals(conn, start.isoformat(), today.isoformat())
            previous = self._totals(conn, prev_start.isoformat(), (start - timedelta(days=1)).isoformat())
            window = ("local_date >= ? AND local_date <= ?", [start.isoformat(), today.isoformat()])
            counts = {r["local_date"]: int(r["n"]) for r in conn.execute(
                f"SELECT local_date, COUNT(*) AS n FROM queries WHERE {window[0]} GROUP BY local_date", window[1])}
            per_day = [DayCount(date=(start + timedelta(days=i)).isoformat(),
                                count=counts.get((start + timedelta(days=i)).isoformat(), 0)) for i in range(days)]
            categories = [NamedCount(name=r["c"], count=int(r["n"])) for r in conn.execute(
                f"SELECT COALESCE(category, 'Autre') AS c, COUNT(*) AS n FROM queries WHERE {window[0]} "
                "GROUP BY c ORDER BY n DESC, c", window[1])]
            top_questions = self._questions(conn, window, answered=None, limit=10)
            unanswered = self._questions(conn, window, answered=False, limit=10)
            top_orgs = [NamedCount(name=r["name"], count=int(r["n"])) for r in conn.execute(
                f"SELECT j.value AS name, COUNT(*) AS n FROM queries q, json_each(q.organizations) j "
                f"WHERE {window[0]} GROUP BY j.value ORDER BY n DESC, name LIMIT 10", window[1])]
            by_hour = [HourLatency(hour=int(r["h"]), avg_latency_ms=round(float(r["l"]), 1), count=int(r["n"]))
                       for r in conn.execute(
                           f"SELECT local_hour AS h, AVG(latency_ms) AS l, COUNT(*) AS n FROM queries "
                           f"WHERE {window[0]} GROUP BY local_hour ORDER BY local_hour", window[1])]
        return AnalyticsSummary(days=days, since=start.isoformat(), totals=totals, previous=previous,
                                per_day=per_day, categories=categories, top_questions=top_questions,
                                unanswered_questions=unanswered, top_organizations=top_orgs,
                                latency_by_hour=by_hour)

    def recent(self, limit: int = 50, offset: int = 0, answered: bool | None = None) -> QueryList:
        where, params = "", []
        if answered is not None:
            where, params = " WHERE answered = ?", [int(answered)]
        with self.db.connect() as conn:
            total = int(conn.execute(f"SELECT COUNT(*) FROM queries{where}", params).fetchone()[0])
            rows = conn.execute(f"SELECT * FROM queries{where} ORDER BY id DESC LIMIT ? OFFSET ?",
                                [*params, limit, offset]).fetchall()
        return QueryList(total=total, items=[QueryRecord(
            id=r["id"], ts=r["ts"], question=r["question"], answered=bool(r["answered"]), intent=r["intent"],
            category=r["category"], top_score=r["top_score"], latency_ms=r["latency_ms"], mode=r["mode"],
            organizations=json.loads(r["organizations"] or "[]"),
            helpful=None if r["helpful"] is None else bool(r["helpful"]), feedback_comment=r["feedback_comment"],
        ) for r in rows])

    # -------------------------------------------------------------- interne
    @staticmethod
    def _totals(conn, start: str, end: str) -> PeriodTotals:
        r = conn.execute(
            "SELECT COUNT(*) AS n, COUNT(DISTINCT session_hash) AS s, COALESCE(SUM(answered), 0) AS a, "
            "COALESCE(SUM(helpful IS NOT NULL), 0) AS f, COALESCE(SUM(helpful = 1), 0) AS h, AVG(latency_ms) AS l "
            "FROM queries WHERE local_date >= ? AND local_date <= ?", (start, end)).fetchone()
        n, f = int(r["n"]), int(r["f"])
        return PeriodTotals(
            conversations=n, unique_sessions=int(r["s"]), answered=int(r["a"]),
            answer_rate=round(int(r["a"]) / n, 3) if n else None,
            feedback_count=f, satisfaction_rate=round(int(r["h"]) / f, 3) if f else None,
            avg_latency_ms=round(float(r["l"]), 1) if r["l"] is not None else None,
        )

    @staticmethod
    def _questions(conn, window, answered: bool | None, limit: int) -> list[QuestionCount]:
        clause, params = window[0], list(window[1])
        if answered is not None:
            clause += " AND answered = ?"
            params.append(int(answered))
        rows = conn.execute(
            f"SELECT MIN(question) AS q, COUNT(*) AS n FROM queries WHERE {clause} "
            f"GROUP BY question_norm ORDER BY n DESC, MIN(id) LIMIT ?", [*params, limit]).fetchall()
        return [QuestionCount(question=r["q"], count=int(r["n"])) for r in rows]
