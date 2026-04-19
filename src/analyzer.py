from typing import Any, Dict, List

from src.storage import StorageEngine


class RelationshipAnalyzer:
    def __init__(self, username: str, storage: StorageEngine):
        self.username = username
        self.storage = storage
        self.followers = {
            u["id"]: u for u in storage.get_relations(username, "followers")
        }
        self.following = {
            u["id"]: u for u in storage.get_relations(username, "following")
        }

    def get_mutual(self) -> List[Dict[str, Any]]:
        """Return mutuals (followers ∩ following)."""
        mutual_ids = set(self.followers.keys()) & set(self.following.keys())
        return [self.followers[uid] for uid in mutual_ids]

    def get_one_way_following(self) -> List[Dict[str, Any]]:
        """Return users I am following who do not follow me back."""
        following_ids = set(self.following.keys()) - set(self.followers.keys())
        return [self.following[uid] for uid in following_ids]

    def get_one_way_followers(self) -> List[Dict[str, Any]]:
        """Return users who follow me but I do not follow back."""
        follower_ids = set(self.followers.keys()) - set(self.following.keys())
        return [self.followers[uid] for uid in follower_ids]

    def get_union(self) -> List[Dict[str, Any]]:
        """Return union of followers and following with relation_type tags."""
        union_ids = set(self.followers.keys()) | set(self.following.keys())
        result = []
        for uid in union_ids:
            user = self.followers.get(uid, self.following.get(uid))
            is_follower = uid in self.followers
            is_following = uid in self.following

            if is_follower and is_following:
                user["relation_type"] = "both"
            elif is_follower:
                user["relation_type"] = "followers"
            else:
                user["relation_type"] = "following"

            user["is_following_back"] = is_following
            result.append(user)

        return result
