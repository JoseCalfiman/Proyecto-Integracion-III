from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crud import get_active_rule
from models import Base, Chamber, HaccpRule


def test_active_rule_selection_uses_latest_review_date():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    chamber_id = UUID("44444444-4444-4444-4444-444444444444")
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        session.add(Chamber(id_chamber=chamber_id))
        older_rule = HaccpRule(
            id_chamber=chamber_id,
            active=True,
            review_date=now - timedelta(days=1),
            severity="medium",
        )
        latest_rule = HaccpRule(
            id_chamber=chamber_id,
            active=True,
            review_date=now,
            severity="high",
        )
        newest_inactive_rule = HaccpRule(
            id_chamber=chamber_id,
            active=False,
            review_date=now + timedelta(minutes=1),
            severity="critical",
        )
        session.add_all([older_rule, latest_rule, newest_inactive_rule])
        session.flush()

        selected_rule = get_active_rule(session, chamber_id)

        assert selected_rule is not None
        assert selected_rule.id_rule == latest_rule.id_rule
