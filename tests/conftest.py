import pytest
import asyncio
import json
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
import aiohttp
from aioresponses import aioresponses

from reddit_scraper import JSONScraper, ConfigManager
from reddit_scraper.proxy_manager import ProxyManager
from reddit_scraper.captcha_solver import CaptchaSolverManager


@pytest.fixture
def sample_reddit_post():
    return {
        "kind": "t3",
        "data": {
            "id": "abc123",
            "title": "Test Post Title",
            "author": "test_user",
            "score": 42,
            "num_comments": 5,
            "url": "https://reddit.com/r/test/comments/abc123/test_post/",
            "selftext": "This is a test post content",
            "created_utc": 1640995200,
            "subreddit": "test",
            "permalink": "/r/test/comments/abc123/test_post/"
        }
    }


@pytest.fixture
def sample_reddit_response(sample_reddit_post):
    return {
        "kind": "Listing",
        "data": {
            "after": "t3_next123",
            "before": None,
            "children": [sample_reddit_post],
            "dist": 1
        }
    }


@pytest.fixture 
def sample_config():
    return {
        "proxies": [
            {
                "host": "test-proxy.com",
                "port": 8080,
                "username": "testuser",
                "password": "testpass",
                "proxy_type": "http"
            }
        ],
        "captcha_solvers": [
            {
                "api_key": "test-api-key",
                "provider": "capsolver",
                "site_keys": {
                    "reddit.com": "test-site-key"
                }
            }
        ],
        "scraping": {
            "default_delay": 0.1,
            "max_retries": 2,
            "requests_per_minute": 120,
            "user_agent": "TestScraper/1.0",
            "rotate_user_agents": False
        }
    }


@pytest.fixture
def mock_config_manager(sample_config):
    mock = Mock(spec=ConfigManager)
    mock.get_scraping_config.return_value = Mock(
        default_delay=0.1,
        max_retries=2,
        user_agent="TestScraper/1.0",
        rotate_user_agents=False
    )
    mock.has_proxies.return_value = False
    mock.has_captcha_solvers.return_value = False
    return mock


@pytest.fixture
def mock_proxy_manager():
    mock = Mock(spec=ProxyManager)
    mock.get_random_proxy.return_value = None
    mock.mark_proxy_failed = Mock()
    return mock


@pytest.fixture
def mock_captcha_solver():
    mock = Mock(spec=CaptchaSolverManager)
    mock.solve_with_retry = AsyncMock(return_value="test-captcha-solution")
    mock.get_site_key.return_value = "test-site-key"
    return mock


@pytest.fixture
async def json_scraper():
    scraper = JSONScraper(delay=0.1, rotate_user_agents=False)
    yield scraper
    await scraper.close_session()


@pytest.fixture
async def json_scraper_with_session():
    async with aiohttp.ClientSession() as session:
        scraper = JSONScraper(delay=0.1, session=session, rotate_user_agents=False)
        yield scraper


@pytest.fixture
def aiohttp_mock():
    with aioresponses() as mock:
        yield mock


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()