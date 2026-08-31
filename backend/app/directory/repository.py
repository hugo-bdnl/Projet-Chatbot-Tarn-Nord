"""Accès à l'annuaire (tables organizations / sites / contacts / domains — MCD du recueil des besoins).

Une organisation est manipulée comme un document complet (sites, contacts et domaines inclus) :
la création / mise à jour remplace ses collections dans une seule transaction.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..db import Database, utc_now
from ..schemas import (ContactOut, DomainIn, DomainOut, DomainUpdate, OrganizationIn, OrganizationOut, SiteOut)


class DuplicateOrganization(Exception):
    """Une organisation du même nom existe déjà (comparaison insensible à la casse)."""


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    deleted: int = 0


@dataclass
class SeedData:
    domains: list[DomainIn]
    organizations: list[OrganizationIn]


def load_seed_file(path: Path) -> SeedData:
    """Fichier JSON : liste d'organisations, ou objet {"domains": [...], "organizations": [...]}."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        domains, items = raw.get("domains", []), raw.get("organizations", [])
    else:
        domains, items = [], raw
    return SeedData(domains=[DomainIn.model_validate(d) for d in domains],
                    organizations=[OrganizationIn.model_validate(item) for item in items])


class DirectoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------- lecture
    def count(self, active_only: bool = True) -> int:
        sql = "SELECT COUNT(*) FROM organizations" + (" WHERE active = 1" if active_only else "")
        with self.db.connect() as conn:
            return int(conn.execute(sql).fetchone()[0])

    def list(self, q: str | None = None, domain: str | None = None, active: bool | None = True,
             limit: int = 100, offset: int = 0) -> tuple[int, list[OrganizationOut]]:
        where: list[str] = []
        params: list = []
        if active is not None:
            where.append("o.active = ?")
            params.append(1 if active else 0)
        if domain:
            where.append("EXISTS (SELECT 1 FROM organization_domains od JOIN domains d ON d.id = od.domain_id "
                         "WHERE od.organization_id = o.id AND d.name = ?)")
            params.append(domain)
        if q:
            like = f"%{q.strip()}%"
            where.append("(o.name LIKE ? OR o.description LIKE ? OR o.keywords LIKE ? "
                         "OR EXISTS (SELECT 1 FROM sites s WHERE s.organization_id = o.id AND s.city LIKE ?) "
                         "OR EXISTS (SELECT 1 FROM organization_domains od JOIN domains d ON d.id = od.domain_id "
                         "WHERE od.organization_id = o.id AND d.name LIKE ?))")
            params += [like] * 5
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        with self.db.connect() as conn:
            total = int(conn.execute(f"SELECT COUNT(*) FROM organizations o{clause}", params).fetchone()[0])
            rows = conn.execute(
                f"SELECT o.* FROM organizations o{clause} ORDER BY o.name COLLATE NOCASE LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
            return total, self._hydrate(conn, rows)

    def all_active(self) -> list[OrganizationOut]:
        return self.list(active=True, limit=100_000)[1]

    def get(self, org_id: int) -> OrganizationOut | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
            return self._hydrate(conn, [row])[0] if row else None

    def get_by_name(self, name: str) -> OrganizationOut | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM organizations WHERE name = ?", (name.strip(),)).fetchone()
            return self._hydrate(conn, [row])[0] if row else None

    def names(self, active_only: bool = True) -> list[tuple[int, str]]:
        sql = "SELECT id, name FROM organizations" + (" WHERE active = 1" if active_only else "")
        with self.db.connect() as conn:
            return [(int(r["id"]), str(r["name"])) for r in conn.execute(sql)]

    # ------------------------------------------------------------ écriture
    def create(self, data: OrganizationIn) -> OrganizationOut:
        with self.db.connect() as conn:
            org_id = self._insert(conn, data)
            return self._hydrate(conn, [self._row(conn, org_id)])[0]

    def update(self, org_id: int, data: OrganizationIn) -> OrganizationOut | None:
        with self.db.connect() as conn:
            if not self._update(conn, org_id, data):
                return None
            return self._hydrate(conn, [self._row(conn, org_id)])[0]

    def delete(self, org_id: int) -> bool:
        with self.db.connect() as conn:
            return conn.execute("DELETE FROM organizations WHERE id = ?", (org_id,)).rowcount > 0

    def import_many(self, items: list[OrganizationIn], replace: bool = False) -> ImportResult:
        """Import « upsert » par nom (insensible à la casse). `replace` supprime les absentes."""
        result = ImportResult()
        with self.db.connect() as conn:
            kept: list[int] = []
            for item in items:
                row = conn.execute("SELECT id FROM organizations WHERE name = ?", (item.name,)).fetchone()
                if row:
                    self._update(conn, int(row["id"]), item)
                    kept.append(int(row["id"]))
                    result.updated += 1
                else:
                    kept.append(self._insert(conn, item))
                    result.created += 1
            if replace:
                placeholders = ",".join("?" * len(kept)) or "NULL"
                cur = conn.execute(f"DELETE FROM organizations WHERE id NOT IN ({placeholders})", kept)
                result.deleted = cur.rowcount
        return result

    # ------------------------------------------------------------- domaines
    def upsert_domains(self, domains: list[DomainIn]) -> None:
        """Crée les domaines manquants et met à jour leur description."""
        with self.db.connect() as conn:
            for d in domains:
                domain_id = self._ensure_domain(conn, d.name.strip())
                conn.execute("UPDATE domains SET description = ? WHERE id = ?", (d.description.strip(), domain_id))

    def list_domains(self) -> list[DomainOut]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT d.id, d.name, d.description, "
                "(SELECT COUNT(*) FROM organization_domains od JOIN organizations o ON o.id = od.organization_id "
                " WHERE od.domain_id = d.id AND o.active = 1) AS organizations "
                "FROM domains d ORDER BY d.name COLLATE NOCASE"
            ).fetchall()
            return [DomainOut(**dict(r)) for r in rows]

    def update_domain(self, domain_id: int, data: DomainUpdate) -> DomainOut | None:
        with self.db.connect() as conn:
            if data.name is not None:
                try:
                    conn.execute("UPDATE domains SET name = ? WHERE id = ?", (data.name.strip(), domain_id))
                except sqlite3.IntegrityError as exc:
                    raise DuplicateOrganization(f"domaine « {data.name} » déjà existant") from exc
            if data.description is not None:
                conn.execute("UPDATE domains SET description = ? WHERE id = ?", (data.description.strip(), domain_id))
        return next((d for d in self.list_domains() if d.id == domain_id), None)

    # ------------------------------------------------------------- interne
    @staticmethod
    def _row(conn: sqlite3.Connection, org_id: int) -> sqlite3.Row:
        return conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()

    def _insert(self, conn: sqlite3.Connection, data: OrganizationIn) -> int:
        now = utc_now()
        try:
            cur = conn.execute(
                "INSERT INTO organizations (name, description, website, keywords, active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (data.name, data.description, data.website, json.dumps(data.keywords, ensure_ascii=False),
                 int(data.active), now, now),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateOrganization(data.name) from exc
        org_id = int(cur.lastrowid)
        self._write_children(conn, org_id, data)
        return org_id

    def _update(self, conn: sqlite3.Connection, org_id: int, data: OrganizationIn) -> bool:
        try:
            cur = conn.execute(
                "UPDATE organizations SET name = ?, description = ?, website = ?, keywords = ?, active = ?, "
                "updated_at = ? WHERE id = ?",
                (data.name, data.description, data.website, json.dumps(data.keywords, ensure_ascii=False),
                 int(data.active), utc_now(), org_id),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateOrganization(data.name) from exc
        if cur.rowcount == 0:
            return False
        conn.execute("DELETE FROM sites WHERE organization_id = ?", (org_id,))
        conn.execute("DELETE FROM contacts WHERE organization_id = ?", (org_id,))
        conn.execute("DELETE FROM organization_domains WHERE organization_id = ?", (org_id,))
        self._write_children(conn, org_id, data)
        return True

    def _write_children(self, conn: sqlite3.Connection, org_id: int, data: OrganizationIn) -> None:
        conn.executemany(
            "INSERT INTO sites (organization_id, label, address, postal_code, city, position) VALUES (?, ?, ?, ?, ?, ?)",
            [(org_id, s.label, s.address, s.postal_code, s.city, i) for i, s in enumerate(data.sites)],
        )
        conn.executemany(
            "INSERT INTO contacts (organization_id, last_name, first_name, role, email, phone, position) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(org_id, c.last_name, c.first_name, c.role, c.email, c.phone, i) for i, c in enumerate(data.contacts)],
        )
        for i, name in enumerate(data.domains):
            conn.execute("INSERT INTO organization_domains (organization_id, domain_id, position) VALUES (?, ?, ?)",
                         (org_id, self._ensure_domain(conn, name), i))

    @staticmethod
    def _ensure_domain(conn: sqlite3.Connection, name: str) -> int:
        row = conn.execute("SELECT id FROM domains WHERE name = ?", (name,)).fetchone()
        if row:
            return int(row["id"])
        return int(conn.execute("INSERT INTO domains (name) VALUES (?)", (name,)).lastrowid)

    @staticmethod
    def _hydrate(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> list[OrganizationOut]:
        if not rows:
            return []
        ids = [int(r["id"]) for r in rows]
        marks = ",".join("?" * len(ids))
        sites: dict[int, list[SiteOut]] = {i: [] for i in ids}
        for s in conn.execute(f"SELECT * FROM sites WHERE organization_id IN ({marks}) ORDER BY position, id", ids):
            sites[int(s["organization_id"])].append(SiteOut(
                id=s["id"], label=s["label"], address=s["address"], postal_code=s["postal_code"], city=s["city"]))
        contacts: dict[int, list[ContactOut]] = {i: [] for i in ids}
        for c in conn.execute(f"SELECT * FROM contacts WHERE organization_id IN ({marks}) ORDER BY position, id", ids):
            contacts[int(c["organization_id"])].append(ContactOut(
                id=c["id"], last_name=c["last_name"], first_name=c["first_name"], role=c["role"],
                email=c["email"], phone=c["phone"]))
        domains: dict[int, list[str]] = {i: [] for i in ids}
        for d in conn.execute(
            f"SELECT od.organization_id, d.name FROM organization_domains od JOIN domains d ON d.id = od.domain_id "
            f"WHERE od.organization_id IN ({marks}) ORDER BY od.position, d.name", ids,
        ):
            domains[int(d["organization_id"])].append(str(d["name"]))
        return [OrganizationOut(
            id=int(r["id"]), name=r["name"], description=r["description"], website=r["website"],
            keywords=json.loads(r["keywords"] or "[]"), active=bool(r["active"]),
            domains=domains[int(r["id"])], sites=sites[int(r["id"])], contacts=contacts[int(r["id"])],
            created_at=r["created_at"], updated_at=r["updated_at"],
        ) for r in rows]
