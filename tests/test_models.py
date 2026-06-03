from sqlmodel import Session, SQLModel, create_engine, select

from app.models import ContactRecord, Creator, Platform, PlatformAccount, SearchTask, TaskStatus


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
