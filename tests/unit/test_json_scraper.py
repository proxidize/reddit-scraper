import pytest
import aiohttp
from unittest.mock import Mock, AsyncMock, patch
from aioresponses import aioresponses

from reddit_scraper import JSONScraper
from reddit_scraper.validation import ValidationError


@pytest.mark.unit
class TestJSONScraperInit:
    
    def test_init_with_defaults(self):
        scraper = JSONScraper()
        assert scraper.delay == 1.0
        assert scraper.user_agent == "RedditScraper/1.0" 
        assert scraper.proxy_manager is None
        assert scraper.captcha_solver is None
        assert scraper.rotate_user_agents is True
    
    def test_init_with_custom_values(self):
        scraper = JSONScraper(
            delay=2.0,
            user_agent="TestAgent/1.0",
            rotate_user_agents=False
        )
        assert scraper.delay == 2.0
        assert scraper.user_agent == "TestAgent/1.0"
        assert scraper.rotate_user_agents is False


@pytest.mark.unit 
class TestJSONScraperHeaders:
    
    def test_headers_with_custom_user_agent(self):
        scraper = JSONScraper(user_agent="TestAgent/1.0", rotate_user_agents=False)
        headers = scraper._get_headers()
        
        assert headers['User-Agent'] == "TestAgent/1.0"
        assert headers['Accept'] == 'application/json'
        assert 'Accept-Language' in headers
    
    def test_headers_with_default_user_agent(self):
        scraper = JSONScraper(rotate_user_agents=False)
        headers = scraper._get_headers()
        
        assert headers['User-Agent'] == "RedditScraper/1.0"


@pytest.mark.unit
class TestJSONScraperRequests:
    
    async def test_make_request_success(self, json_scraper, aiohttp_mock, sample_reddit_response):
        url = "https://www.reddit.com/r/test/hot.json"
        aiohttp_mock.get(url, payload=sample_reddit_response)
        
        result = await json_scraper._make_request(url)
        
        assert result == sample_reddit_response
    
    async def test_make_request_with_params(self, json_scraper, aiohttp_mock, sample_reddit_response):
        url = "https://www.reddit.com/r/test/hot.json"
        params = {"limit": 25}
        aiohttp_mock.get(url, payload=sample_reddit_response)
        
        result = await json_scraper._make_request(url, params=params)
        
        assert result == sample_reddit_response
    
    async def test_make_request_failure(self, json_scraper, aiohttp_mock):
        url = "https://www.reddit.com/r/test/hot.json"
        aiohttp_mock.get(url, status=404)
        
        result = await json_scraper._make_request(url)
        
        assert result is None
    
    async def test_make_request_retry_logic(self, json_scraper, aiohttp_mock, sample_reddit_response):
        url = "https://www.reddit.com/r/test/hot.json"
        aiohttp_mock.get(url, status=500)
        aiohttp_mock.get(url, payload=sample_reddit_response)
        
        result = await json_scraper._make_request(url, max_retries=2)
        
        assert result == sample_reddit_response


@pytest.mark.unit
class TestJSONScraperSubreddit:
    
    async def test_scrape_subreddit_valid_input(self, json_scraper, aiohttp_mock, sample_reddit_response):
        url = "https://www.reddit.com/r/test/hot.json"
        aiohttp_mock.get(url, payload=sample_reddit_response)
        
        posts = await json_scraper.scrape_subreddit("test", "hot", 25)
        
        assert len(posts) == 1
        assert posts[0]['title'] == "Test Post Title"
        assert posts[0]['author'] == "test_user"
        assert posts[0]['score'] == 42
    
    async def test_scrape_subreddit_invalid_input(self, json_scraper):
        with pytest.raises(ValidationError):
            await json_scraper.scrape_subreddit("invalid!", "hot", 25)
    
    async def test_scrape_subreddit_no_posts(self, json_scraper, aiohttp_mock):
        url = "https://www.reddit.com/r/test/hot.json"
        empty_response = {
            "kind": "Listing",
            "data": {"children": []}
        }
        aiohttp_mock.get(url, payload=empty_response)
        
        posts = await json_scraper.scrape_subreddit("test", "hot", 25)
        
        assert posts == []
    
    async def test_scrape_subreddit_api_failure(self, json_scraper, aiohttp_mock):

        url = "https://www.reddit.com/r/test/hot.json"
        aiohttp_mock.get(url, status=503)
        
        posts = await json_scraper.scrape_subreddit("test", "hot", 25)
        
        assert posts == []


@pytest.mark.unit
class TestJSONScraperComments:
    
    async def test_scrape_post_comments_success(self, json_scraper, aiohttp_mock):
        url = "https://www.reddit.com/r/test/comments/abc123.json"
        comment_response = [
            {"kind": "Listing", "data": {"children": []}},
            {
                "kind": "Listing", 
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": "comment1",
                                "author": "commenter1",
                                "body": "Great post!",
                                "score": 10
                            }
                        }
                    ]
                }
            }
        ]
        aiohttp_mock.get(url, payload=comment_response)
        
        result = await json_scraper.scrape_post_comments("test", "abc123", "best")
        
        assert 'comments' in result
        assert len(result['comments']) == 1
        assert result['comments'][0]['body'] == "Great post!"
    
    async def test_scrape_post_comments_invalid_input(self, json_scraper):
        with pytest.raises(ValidationError):
            await json_scraper.scrape_post_comments("invalid!", "abc123", "best")


@pytest.mark.unit
class TestJSONScraperSession:
    
    async def test_session_creation(self, json_scraper):
        session = await json_scraper._get_session()
        assert isinstance(session, aiohttp.ClientSession)
    
    async def test_session_reuse(self, json_scraper):
        session1 = await json_scraper._get_session()
        session2 = await json_scraper._get_session()
        assert session1 is session2
    
    async def test_close_session(self, json_scraper):
        await json_scraper._get_session()  
        await json_scraper.close_session()
        
        assert json_scraper._session is None


@pytest.mark.unit
class TestJSONScraperDataCleaning:
    
    def test_clean_post_data(self, json_scraper, sample_reddit_post):
        cleaned = json_scraper._clean_post_data(sample_reddit_post['data'])
        
        expected_keys = ['id', 'title', 'author', 'score', 'num_comments', 'url']
        for key in expected_keys:
            assert key in cleaned
            
        assert cleaned['title'] == "Test Post Title"
        assert cleaned['author'] == "test_user"
        assert cleaned['score'] == 42
    
    def test_clean_comment_data(self, json_scraper):    
        comment_data = {
            "id": "comment1",
            "author": "commenter1", 
            "body": "Great post!",
            "score": 10,
            "created_utc": 1640995200
        }
        
        cleaned = json_scraper._clean_comment_data(comment_data)
        
        expected_keys = ['id', 'author', 'body', 'score', 'created_utc']
        for key in expected_keys:
            assert key in cleaned
            
        assert cleaned['body'] == "Great post!"
        assert cleaned['score'] == 10