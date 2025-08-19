import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from fake_useragent import UserAgent

from .base_scraper import BaseScraper
from .proxy_manager import ProxyManager
from .captcha_solver import CaptchaSolverManager, CaptchaSolution
from .validation import (
    validate_subreddit_name, validate_username, validate_post_id,
    validate_limit, validate_sort_method, validate_url, ValidationError
)

logger = logging.getLogger(__name__)


class JSONScraper(BaseScraper):
    
    def __init__(self, delay: float = 1.0, user_agent: Optional[str] = None, 
                 proxy_manager: Optional[ProxyManager] = None,
                 captcha_solver: Optional[CaptchaSolverManager] = None,
                 rotate_user_agents: bool = True,
                 timeout: int = 30):
        super().__init__(delay)
        self.user_agent = user_agent or "RedditScraper/1.0" 
        self.proxy_manager = proxy_manager
        self.captcha_solver = captcha_solver
        self.rotate_user_agents = rotate_user_agents
        self.timeout = timeout
        self.ua = UserAgent() if rotate_user_agents else None
        self._session = None
        self._owned_session = False
        
        self.default_headers = {
            'User-Agent': self.user_agent if not rotate_user_agents else (self.ua.random if self.ua else self.user_agent),
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def _get_headers(self) -> Dict[str, str]:
        headers = self.default_headers.copy()
        if self.rotate_user_agents and self.ua:
            headers['User-Agent'] = self.ua.random
        return headers
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._get_headers()
            )
            self._owned_session = True
        return self._session
    
    async def close_session(self):
        if self._owned_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self._owned_session = False
    
    async def _make_request(self, url: str, params: Optional[Dict] = None, 
                           max_retries: int = 3) -> Optional[Dict[str, Any]]:

        url = validate_url(url)
        
        proxy_url = None
        if self.proxy_manager:
            proxy_dict = self.proxy_manager.get_next_http_proxy()
            if proxy_dict:
                proxy_url = proxy_dict.get('http', proxy_dict.get('https'))
        
        for attempt in range(max_retries + 1):
            try:
                session = await self._get_session()
                logger.info(f"Fetching: {url} (attempt {attempt + 1})")
                
                async with session.get(url, params=params, proxy=proxy_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Successfully fetched {url}")
                        return data
                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None
                        
            except aiohttp.ClientProxyConnectionError as e:
                logger.warning(f"Proxy error for {url}: {e}")
                if self.proxy_manager and proxy_url:
                    self.proxy_manager.mark_proxy_failed({'http': proxy_url})
                continue
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Request failed for {url} (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                continue
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode failed for {url}: {e}")
                return None
                
        logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
        return None
    
    async def _handle_captcha_async(self, url: str, response_text: str) -> bool:

        if not self.captcha_solver:
            return False
            
        try:
            if "recaptcha" in response_text.lower():
                logger.info("Attempting to solve reCAPTCHA...")
                
                site_key = self.captcha_solver.get_site_key(url)
                if not site_key:
                    logger.error(f"No reCAPTCHA site key configured for {url}")
                    return False
                
                solution = self.captcha_solver.check_balance_and_solve(
                    self.captcha_solver.solver.solve_recaptcha_v2,
                    url,
                    site_key
                )
                
                if solution.success:
                    logger.info("reCAPTCHA solved successfully")
                    return True
                    
            logger.warning("Unable to solve captcha automatically")
            return False
            
        except Exception as e:
            logger.error(f"Error handling captcha: {e}")
            return False
    
    async def scrape_subreddit(self, subreddit: str, sort_by: str = "hot", 
                              limit: int = 25) -> List[Dict[str, Any]]:
        subreddit = validate_subreddit_name(subreddit)
        sort_by = validate_sort_method(sort_by, ['hot', 'new', 'top', 'rising'])
        limit = validate_limit(limit)
        
        url = f"https://www.reddit.com/r/{subreddit}/{sort_by}.json"
        posts = []
        after = None
        posts_fetched = 0
        batch_size = 100  
        
        while posts_fetched < limit:
            current_limit = min(batch_size, limit - posts_fetched)
            
            params = {
                'limit': current_limit,
                'raw_json': 1
            }
            
            if after:
                params['after'] = after
                
            data = await self._make_request(url, params)
            if not data or 'data' not in data:
                logger.warning("No more data available or request failed")
                break
                
            children = data['data'].get('children', [])
            if not children:
                logger.info("No more posts available")
                break
                
            for child in children:
                if child['kind'] == 't3' and posts_fetched < limit:
                    cleaned_post = self._clean_post_data(child['data'])
                    posts.append(cleaned_post)
                    posts_fetched += 1
                    
            after = data['data'].get('after')
            if not after:
                logger.info("Reached end of available posts")
                break
                
            await asyncio.sleep(self.delay)
                    
        logger.info(f"Scraped {len(posts)} posts from r/{subreddit}")
        
        await self.close_session()
        return posts
    
    async def scrape_post_comments(self, subreddit: str, post_id: str, 
                                  sort: str = "best") -> Dict[str, Any]:

        subreddit = validate_subreddit_name(subreddit)
        post_id = validate_post_id(post_id)
        sort = validate_sort_method(sort, ['best', 'top', 'new', 'controversial', 'old', 'qa'])
        
        url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        params = {'sort': sort} if sort else None
            
        data = await self._make_request(url, params)
        if not data or not isinstance(data, list) or len(data) < 2:
            return {}
            
        raw_post_data = data[0]['data']['children'][0]['data'] if data[0]['data']['children'] else {}
        post_data = self._clean_post_data(raw_post_data) if raw_post_data else {}
        comments_data = self._extract_comments(data[1]['data']['children'])
        
        return {
            'post': post_data,
            'comments': comments_data
        }
    
    async def scrape_user_posts(self, username: str, sort_by: str = "new", 
                               limit: int = 25) -> List[Dict[str, Any]]:

        username = validate_username(username)
        sort_by = validate_sort_method(sort_by, ['new', 'hot', 'top'])
        limit = validate_limit(limit)
        
        url = f"https://www.reddit.com/user/{username}/submitted.json"
        params = {}
        if sort_by:
            params['sort'] = sort_by
        if limit:
            params['limit'] = limit
            
        data = await self._make_request(url, params if params else None)
        if not data:
            return []
            
        posts = []
        if 'data' in data and 'children' in data['data']:
            for child in data['data']['children']:
                if child['kind'] == 't3':
                    cleaned_post = self._clean_post_data(child['data'])
                    posts.append(cleaned_post)
                    
        logger.info(f"Scraped {len(posts)} posts from u/{username}")
        return posts
    
    async def search_subreddit(self, subreddit: str, query: str, sort_by: str = "relevance",
                              time_filter: str = "all", limit: int = 25) -> List[Dict[str, Any]]:
        subreddit = validate_subreddit_name(subreddit)
        sort_by = validate_sort_method(sort_by, ['relevance', 'hot', 'top', 'new', 'comments'])
        limit = validate_limit(limit)
        
        if not query.strip():
            raise ValidationError("Search query cannot be empty")
            
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            'q': query.strip(),
            'restrict_sr': 'on',
            'sort': sort_by,
            't': time_filter,
            'limit': limit
        }
        
        data = await self._make_request(url, params)
        if not data:
            return []
            
        posts = []
        if 'data' in data and 'children' in data['data']:
            for child in data['data']['children']:
                if child['kind'] == 't3':
                    cleaned_post = self._clean_post_data(child['data'])
                    posts.append(cleaned_post)
                    
        logger.info(f"Found {len(posts)} posts matching '{query}' in r/{subreddit}")
        return posts
    
    async def scrape_multiple_subreddits(self, subreddits: List[str], 
                                        sort_by: str = "hot", 
                                        limit_per_subreddit: int = 25) -> Dict[str, List[Dict[str, Any]]]:

        if not subreddits:
            return {}
        
        validated_subreddits = [validate_subreddit_name(sr) for sr in subreddits]
        
        tasks = [
            self.scrape_subreddit(subreddit, sort_by, limit_per_subreddit)
            for subreddit in validated_subreddits
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = {}
        for subreddit, result in zip(validated_subreddits, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to scrape r/{subreddit}: {result}")
                final_results[subreddit] = []
            else:
                final_results[subreddit] = result
        
        return final_results