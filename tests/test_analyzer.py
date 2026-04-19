import pytest

from src.analyzer import RelationshipAnalyzer


class MockStorage:
    def __init__(self, followers, following):
        self.followers = followers
        self.following = following

    def get_relations(self, username, rel_type):
        if rel_type == "followers":
            return self.followers
        return self.following


@pytest.fixture
def analyzer():
    followers = [
        {"id": 1, "login": "user1", "avatar_url": "", "html_url": ""},
        {"id": 2, "login": "user2", "avatar_url": "", "html_url": ""},
    ]
    following = [
        {"id": 2, "login": "user2", "avatar_url": "", "html_url": ""},
        {"id": 3, "login": "user3", "avatar_url": "", "html_url": ""},
    ]
    storage = MockStorage(followers, following)
    return RelationshipAnalyzer("test_user", storage)


def test_get_mutual(analyzer):
    mutual = analyzer.get_mutual()
    assert len(mutual) == 1
    assert mutual[0]["id"] == 2


def test_get_one_way_following(analyzer):
    following = analyzer.get_one_way_following()
    assert len(following) == 1
    assert following[0]["id"] == 3


def test_get_one_way_followers(analyzer):
    followers = analyzer.get_one_way_followers()
    assert len(followers) == 1
    assert followers[0]["id"] == 1


def test_get_union(analyzer):
    union = analyzer.get_union()
    assert len(union) == 3

    user1 = next(u for u in union if u["id"] == 1)
    assert user1["relation_type"] == "followers"
    assert user1["is_following_back"] is False

    user2 = next(u for u in union if u["id"] == 2)
    assert user2["relation_type"] == "both"
    assert user2["is_following_back"] is True

    user3 = next(u for u in union if u["id"] == 3)
    assert user3["relation_type"] == "following"
    assert user3["is_following_back"] is True
