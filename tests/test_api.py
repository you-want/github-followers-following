from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api import GitHubAPI


class AsyncContextManagerMock:
    def __init__(self, mock_obj):
        self.mock_obj = mock_obj

    async def __aenter__(self):
        return self.mock_obj

    async def __aexit__(self, exc_type, exc, tb):
        pass


@pytest.mark.asyncio
async def test_fetch_page_rate_limit():
    api = GitHubAPI(token="fake")

    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "0"}

    mock_success = AsyncMock()
    mock_success.status = 200
    mock_success.headers = {}
    mock_success.json.return_value = [{"id": 1}]

    session = MagicMock()
    session.get.side_effect = [
        AsyncContextManagerMock(mock_response),
        AsyncContextManagerMock(mock_success),
    ]

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        data, next_url = await api._fetch_page(session, "http://fake")
        assert len(data) == 1
        assert mock_sleep.called


@pytest.mark.asyncio
async def test_fetch_page_pagination():
    api = GitHubAPI(token="fake")
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {
        "Link": '<https://api.github.com/users/test/followers?page=2>; rel="next", <https://api.github.com/users/test/followers?page=5>; rel="last"'
    }
    mock_response.json.return_value = [{"id": 1}]

    session = MagicMock()
    session.get.return_value = AsyncContextManagerMock(mock_response)

    data, last_page = await api._fetch_page(session, "http://fake")
    assert last_page == 5


@pytest.mark.asyncio
async def test_fetch_users_and_all():
    api = GitHubAPI(token="fake")

    with patch.object(api, "_fetch_page", new_callable=AsyncMock) as mock_fetch_page:
        # Mock fetch_page to return a list of users on first call and empty on second
        mock_fetch_page.side_effect = [
            ([{"id": 1, "login": "user1"}], 2),
            ([{"id": 2, "login": "user2"}], 2),
        ]

        # Test fetch_users
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            with patch("src.api.Path.mkdir"):
                users = await api.fetch_users("testuser", "followers")

                assert len(users) == 2
                assert mock_open.called

    with patch.object(api, "fetch_users", new_callable=AsyncMock) as mock_fetch_users:
        mock_fetch_users.side_effect = [[{"id": 1}], [{"id": 2}]]

        followers, following = await api.fetch_all("testuser")
        assert len(followers) == 1
        assert len(following) == 1
