import pytest

from src.storage import StorageEngine


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    engine = StorageEngine(str(db_path))
    yield engine
    engine.close()


def test_init_db(storage):
    cursor = storage.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert "users" in tables
    assert "relations" in tables


def test_save_and_get_relations(storage):
    users = [
        {"id": 1, "login": "user1", "avatar_url": "url1", "html_url": "html1"},
        {"id": 2, "login": "user2", "avatar_url": "url2", "html_url": "html2"},
    ]

    storage.save_users("owner1", users, "followers")

    # Get followers
    followers = storage.get_relations("owner1", "followers")
    assert len(followers) == 2
    assert followers[0]["login"] == "user1"

    # Get following (should be empty)
    following = storage.get_relations("owner1", "following")
    assert len(following) == 0


def test_save_users_upsert(storage):
    users = [{"id": 1, "login": "user1", "avatar_url": "url1", "html_url": "html1"}]
    storage.save_users("owner1", users, "followers")

    # Update user data
    users_updated = [
        {"id": 1, "login": "user1_new", "avatar_url": "url1_new", "html_url": "html1"}
    ]
    storage.save_users("owner1", users_updated, "followers")

    followers = storage.get_relations("owner1", "followers")
    assert len(followers) == 1
    assert followers[0]["login"] == "user1_new"
    assert followers[0]["avatar_url"] == "url1_new"
