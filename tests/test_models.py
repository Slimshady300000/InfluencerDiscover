import os
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import (
    ContactRecord,
    ContentSample,
    Creator,
    FollowUp,
    Platform,
    PlatformAccount,
    ScoreResult,
    SearchTask,
    TaskStatus,
)


def test_creator_platform_account_and_contact_persist():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        task = SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="youtube,tiktok,instagram",
            status=TaskStatus.queued,
        )
        creator = Creator(display_name="Creator A", primary_topics="skincare,beauty")
        account = PlatformAccount(
            creator=creator,
            platform=Platform.youtube,
            handle="@creator_a",
            profile_url="https://youtube.com/@creator_a",
            follower_count=310000,
        )
        contact = ContactRecord(
            creator=creator,
            contact_type="email",
            value="biz@example.com",
            source_url="https://youtube.com/@creator_a/about",
            is_public=True,
        )
        session.add(task)
        session.add(account)
        session.add(contact)
        session.commit()

        saved = session.exec(select(Creator)).one()
        assert saved.display_name == "Creator A"
        assert saved.accounts[0].platform == Platform.youtube
        assert saved.contacts[0].value == "biz@example.com"


def test_init_db_registers_task_tables_when_only_db_module_imported(tmp_path):
    db_path = tmp_path / "models.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    script = textwrap.dedent(
        """
        from sqlalchemy import inspect

        import app.db as db

        db.init_db()
        tables = set(inspect(db.engine).get_table_names())
        expected = {
            "contentsample",
            "contactrecord",
            "creator",
            "followup",
            "platformaccount",
            "scoreresult",
            "searchtask",
        }
        missing = expected - tables
        assert not missing, sorted(missing)
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_creator_created_at_round_trips_as_naive_utc():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    before = datetime.now(timezone.utc).replace(tzinfo=None)

    with Session(engine) as session:
        creator = Creator(display_name="Creator B")
        assert creator.created_at.tzinfo is None
        session.add(creator)
        session.commit()
        session.refresh(creator)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert creator.created_at.tzinfo is None
        assert before <= creator.created_at <= after


def test_required_parent_links_are_non_nullable():
    assert PlatformAccount.__table__.c.creator_id.nullable is False
    assert ContentSample.__table__.c.account_id.nullable is False
    assert ContactRecord.__table__.c.creator_id.nullable is False
    assert FollowUp.__table__.c.creator_id.nullable is False
    assert ScoreResult.__table__.c.task_id.nullable is False
    assert ScoreResult.__table__.c.creator_id.nullable is False
    assert ScoreResult.__table__.c.platform_account_id.nullable is False


def test_platform_account_without_creator_violates_constraints():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        account = PlatformAccount(
            platform=Platform.youtube,
            handle="@orphan",
            profile_url="https://youtube.com/@orphan",
        )
        session.add(account)

        with pytest.raises(IntegrityError):
            session.commit()


def test_build_engine_rejects_dangling_sqlite_foreign_key(tmp_path, monkeypatch):
    import app.db as db

    db_path = tmp_path / "foreign_keys.db"
    monkeypatch.setattr(
        db,
        "get_settings",
        lambda: SimpleNamespace(database_url=f"sqlite:///{db_path.as_posix()}"),
    )
    engine = db.build_engine()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        account = PlatformAccount(
            creator_id=999999,
            platform=Platform.youtube,
            handle="@missing",
            profile_url="https://youtube.com/@missing",
        )
        session.add(account)

        with pytest.raises(IntegrityError):
            session.commit()


def test_score_result_links_to_task_creator_and_account():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        task = SearchTask(
            input_text="skincare",
            input_type="keyword",
            platforms="instagram",
            status=TaskStatus.queued,
        )
        creator = Creator(display_name="Creator Score")
        account = PlatformAccount(
            creator=creator,
            platform=Platform.instagram,
            handle="@creator_score",
            profile_url="https://instagram.com/creator_score",
        )
        result = ScoreResult(
            task=task,
            creator=creator,
            platform_account=account,
            final_score=0.91,
        )
        session.add(result)
        session.commit()

        saved = session.exec(select(ScoreResult)).one()
        assert saved.task.input_text == "skincare"
        assert saved.creator.display_name == "Creator Score"
        assert saved.platform_account.handle == "@creator_score"
