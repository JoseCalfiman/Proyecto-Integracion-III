"""Reglas HACCP contra la aplicación real y una base efímera, sin Docker."""
import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

import bcrypt
from sqlalchemy import Integer, MetaData, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import Base, get_db
from main import app
from models import Chamber, Company, HaccpRule, Role, User

VALID = {"max_absolute_temp": 5.0, "min_absolute_temp": -25.0,
         "tolerance_time_min": 20, "severity": "medium", "active": True}


class HaccpRulesTests(unittest.TestCase):
    def setUp(self):
        key = patch.dict(os.environ, JWT_SECRET=secrets.token_hex(32))
        key.start()
        self.addCleanup(key.stop)
        engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        tables = MetaData()
        for table in Base.metadata.tables.values():
            table.to_metadata(tables)
        tables.tables["alert_audit"].c.id_audit.type = Integer()
        tables.tables["haccp_rules"].c.id_rule.type = Integer()
        tables.tables["sensor_data"].c.id_data.autoincrement = False
        tables.create_all(engine)
        sessions = sessionmaker(engine)
        self.sessions = sessions
        def db():
            with sessions() as session:
                yield session
        app.dependency_overrides[get_db] = db
        self.addCleanup(app.dependency_overrides.pop, get_db)

        company = uuid4()
        self.users = {}
        self.with_rule, self.without_rule, self.multi, self.inactive = (uuid4() for _ in range(4))
        base = datetime(2026, 1, 1)
        with sessions.begin() as session:
            session.add(Company(id_company=company, tax_id="demo"))
            hashed = bcrypt.hashpw(b"demo", bcrypt.gensalt(rounds=4)).decode()
            for i, role in enumerate(("gerente", "tecnico"), 1):
                self.users[role] = uuid4()
                session.add(Role(id_role=i, role_name=role))
                session.add(User(id_user=self.users[role], id_company=company, id_role=i, name=role.title() + " Demo",
                                 email=role + "@test.invalid", password_hash=hashed))
            for id_chamber, name, active in ((self.with_rule, "A con regla", True), (self.without_rule, "B sin regla", True),
                                             (self.multi, "C varias", True), (self.inactive, "D inactiva", False)):
                session.add(Chamber(id_chamber=id_chamber, id_company=company, name=name, active=active))
            session.add(HaccpRule(id_rule=1, id_chamber=self.with_rule, max_absolute_temp=4, min_absolute_temp=-30,
                                  tolerance_time_min=15, severity="medium", active=True, review_date=base))
            # Varias reglas: 3 y 4 empatan en fecha; gana la de mayor id (4).
            for id_rule, days, temp in ((2, 0, 1), (3, 5, 2), (4, 5, 3)):
                session.add(HaccpRule(id_rule=id_rule, id_chamber=self.multi, max_absolute_temp=temp, min_absolute_temp=-30,
                                      tolerance_time_min=15, severity="low", active=True,
                                      review_date=base + timedelta(days=days)))
            session.add(HaccpRule(id_rule=5, id_chamber=self.inactive, max_absolute_temp=4, min_absolute_temp=-30,
                                  tolerance_time_min=15, severity="medium", active=True, review_date=base))
        self.tokens = {}
        for role in self.users:
            code, body = self.request("POST", "/auth/login", data={"email": role + "@test.invalid", "password": "demo"})
            self.assertEqual(code, 200)
            self.tokens[role] = body["access_token"]

    def request(self, method, path, token=None, data=None):
        async def run():
            messages = []
            async def send(message):
                messages.append(message)
            async def receive():
                return {"type": "http.request", "body": json.dumps(data).encode()}
            headers = [(b"content-type", b"application/json")]
            if token:
                headers.append((b"authorization", ("Bearer " + token).encode()))
            await app({"type": "http", "method": method, "path": "/api/v1" + path, "headers": headers,
                       "query_string": b"", "scheme": "http", "http_version": "1.1"}, receive, send)
            return messages[0]["status"], json.loads(messages[1]["body"])
        return asyncio.run(run())

    def put(self, id_chamber, data=VALID, role="gerente"):
        return self.request("PUT", f"/haccp/rules/{id_chamber}", self.tokens.get(role), data)

    def get(self, id_chamber, role="tecnico"):
        return self.request("GET", f"/haccp/rules/{id_chamber}", self.tokens.get(role))

    def test_put_permissions(self):
        for role, expected in (("gerente", 200), ("tecnico", 403), (None, 401)):
            with self.subTest(role=role):
                code, body = self.put(self.with_rule, role=role)
                self.assertEqual(code, expected, body)

    def test_put_validation(self):
        for change in ({"min_absolute_temp": 5.0}, {"min_absolute_temp": 6.0},
                       {"max_absolute_temp": 51.0}, {"min_absolute_temp": -51.0},
                       {"tolerance_time_min": 0}, {"severity": "urgent"}):
            with self.subTest(change=change):
                code, body = self.put(self.with_rule, dict(VALID, **change))
                self.assertEqual(code, 422, body)

    def test_severity_high_is_saved(self):
        code, body = self.put(self.with_rule, dict(VALID, severity="high"))
        self.assertEqual((code, body["severity"]), (200, "high"))
        self.assertEqual(self.get(self.with_rule)[1]["severity"], "high")
        with self.sessions() as session:
            self.assertEqual(session.get(HaccpRule, 1).severity, "high")

    def test_chamber_without_rule(self):
        code, body = self.get(self.without_rule)
        self.assertEqual(code, 200, body)
        self.assertFalse(body["has_rule"])
        self.assertFalse(body["active"])
        for field in ("id_rule", "review_date", "id_user_modified", "modified_by_name"):
            self.assertIsNone(body[field], field)
        self.assertEqual(body["max_absolute_temp"], 4.0)  # sugerencia para el formulario

        code, body = self.put(self.without_rule)
        self.assertEqual(code, 200, body)
        self.assertTrue(body["has_rule"])
        self.assertIsNotNone(body["id_rule"])
        code, body = self.get(self.without_rule)
        self.assertTrue(body["has_rule"])
        self.assertTrue(body["active"])
        self.assertEqual(body["max_absolute_temp"], VALID["max_absolute_temp"])

    def test_list_one_row_per_active_chamber_with_current_rule(self):
        code, body = self.request("GET", "/haccp/rules", self.tokens["tecnico"])
        self.assertEqual(code, 200, body)
        self.assertEqual([r["chamber_name"] for r in body], ["A con regla", "B sin regla", "C varias"])
        multi = next(r for r in body if r["id_chamber"] == str(self.multi))
        self.assertEqual((multi["id_rule"], multi["max_absolute_temp"]), (4, 3.0))
        self.assertFalse(next(r for r in body if r["id_chamber"] == str(self.without_rule))["has_rule"])

        self.assertEqual(self.get(self.multi)[1]["id_rule"], 4)
        code, body = self.put(self.multi)
        self.assertEqual((code, body["id_rule"]), (200, 4))
        with self.sessions() as session:
            active = [r.id_rule for r in session.query(HaccpRule).filter_by(id_chamber=self.multi, active=True)]
            self.assertEqual(active, [4])
        listed = self.request("GET", "/haccp/rules", self.tokens["gerente"])[1]
        self.assertEqual([r["id_rule"] for r in listed if r["id_chamber"] == str(self.multi)], [4])

    def test_put_without_changes_keeps_review_date(self):
        _, before = self.get(self.with_rule)
        unchanged = {k: before[k] for k in VALID}
        code, body = self.put(self.with_rule, unchanged)
        self.assertEqual(code, 200, body)
        self.assertEqual(body["review_date"], before["review_date"])
        self.assertIsNone(body["id_user_modified"])
        with self.sessions() as session:
            self.assertIsNone(session.get(HaccpRule, 1).id_user_modified)

        code, changed = self.put(self.with_rule, dict(unchanged, tolerance_time_min=30))
        self.assertEqual(code, 200, changed)
        self.assertNotEqual(changed["review_date"], before["review_date"])

    def test_modified_by_name(self):
        self.assertIsNone(self.get(self.with_rule)[1]["modified_by_name"])
        code, body = self.put(self.with_rule)
        self.assertEqual(code, 200, body)
        self.assertEqual(body["id_user_modified"], str(self.users["gerente"]))
        self.assertEqual(body["modified_by_name"], "Gerente Demo")
        self.assertEqual(self.get(self.with_rule)[1]["modified_by_name"], "Gerente Demo")

    def test_inactive_or_missing_chamber_is_404(self):
        for id_chamber in (self.inactive, uuid4()):
            with self.subTest(id_chamber=id_chamber):
                for code, body in (self.get(id_chamber), self.put(id_chamber)):
                    self.assertEqual((code, body["detail"]), (404, "Cámara no encontrada"))
        with self.sessions() as session:
            self.assertEqual(session.get(HaccpRule, 5).max_absolute_temp, 4)


if __name__ == "__main__":
    unittest.main()
