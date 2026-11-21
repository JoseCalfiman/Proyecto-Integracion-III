"""Matriz HTTP contra la aplicación real y una base efímera, sin Docker."""
import asyncio
import json
import os
from pathlib import Path
import secrets
import sys
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import bcrypt
import jwt
from sqlalchemy import Integer, MetaData, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import Base, get_db
from main import app
from models import AlertAudit, Company, GeneratedAlert, Role, User


class RoleMatrix(unittest.TestCase):
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
        with sessions.begin() as session:
            session.add(Company(id_company=company, tax_id="demo"))
            hashed = bcrypt.hashpw(b"demo", bcrypt.gensalt(rounds=4)).decode()
            for i, role in enumerate(("gerente", "tecnico"), 1):
                self.users[role] = uuid4()
                session.add(Role(id_role=i, role_name=role))
                session.add(User(id_user=self.users[role], id_company=company, id_role=i,
                                 email=role+"@test.invalid", password_hash=hashed))
            session.add(GeneratedAlert(id_alert=1, severity="high", status="active"))
        self.tokens = {}
        for role in self.users:
            status, body = self.request("POST", "/auth/login", data={"email":role+"@test.invalid","password":"demo"})
            self.assertEqual(status, 200)
            self.tokens[role] = body["access_token"]

    def request(self, method, path, token=None, data=None):
        async def run():
            messages = []
            async def send(message):
                messages.append(message)
            async def receive():
                return {"type":"http.request","body":json.dumps(data).encode()}
            headers = [(b"content-type", b"application/json")]
            if token:
                headers.append((b"authorization", ("Bearer "+token).encode()))
            await app({"type":"http","method":method,"path":"/api/v1"+path,"headers":headers,
                       "query_string":b"","scheme":"http","http_version":"1.1"}, receive, send)
            return messages[0]["status"], json.loads(messages[1]["body"])
        return asyncio.run(run())

    def test_matrix(self):
        for method, path, data, manager, tech in (
            ("GET","/usuarios",None,200,403), ("GET","/empresa",None,200,403),
            ("PUT","/empresa",{"nombre":"Demo"},200,403),
            ("GET","/alerts",None,200,200), ("GET","/chambers",None,200,200),
            ("GET","/haccp/rules",None,200,200),
            ("PUT","/alerts/1/acknowledge",{},403,200),
            ("PUT","/alerts/1/resolve",{"id_user":str(self.users["gerente"])},403,200),
        ):
            for role, expected in ((None,401),("gerente",manager),("tecnico",tech)):
                with self.subTest(method=method,path=path,role=role):
                    code, body = self.request(method,path,self.tokens.get(role),data)
                    self.assertEqual(code,expected,body)
                    if path.endswith("/resolve") and code==200:
                        self.assertEqual(body["id_user_resolved"],str(self.users["tecnico"]))

    def test_alert_audit_uses_authenticated_technician(self):
        token = self.tokens["tecnico"]
        for action, payload in (("acknowledge", {}), ("resolve", {"note": "Sensor revisado"})):
            code, body = self.request("PUT", f"/alerts/1/{action}", token, payload)
            self.assertEqual(code, 200, body)

        with self.sessions() as session:
            alert = session.get(GeneratedAlert, 1)
            audits = session.query(AlertAudit).filter_by(id_alert=1).order_by(AlertAudit.id_audit).all()
            self.assertEqual(alert.status, "resolved")
            self.assertEqual([row.action for row in audits], ["acknowledged", "resolved"])
            self.assertEqual(audits[1].detail, "Sensor revisado")
            for audit, actor, date in (
                (audits[0], alert.id_user_acknowledged, alert.acknowledgment_date),
                (audits[1], alert.id_user_resolved, alert.resolution_date),
            ):
                self.assertEqual(actor, self.users["tecnico"])
                self.assertEqual(audit.id_user, actor)
                self.assertIsNotNone(date)
                self.assertEqual(audit.action_date, date)

    def test_invalid_tokens_and_disabled_account(self):
        claims = {"sub":str(self.users["gerente"]),"role":"gerente","exp":int(time.time())+60}
        key = os.environ["JWT_SECRET"]
        for token in ("invalid", jwt.encode(claims, secrets.token_hex(32)),
                      jwt.encode(dict(claims, exp=1), key)):
            self.assertEqual(self.request("GET","/empresa",token)[0],401)
        self.assertEqual(self.request("PUT","/usuarios/"+str(self.users["tecnico"]),
                                      self.tokens["gerente"],{"activo":False})[0],200)
        self.assertEqual(self.request("GET","/alerts",self.tokens["tecnico"])[0],401)
