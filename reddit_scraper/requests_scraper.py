import requests
import time
import json
from typing import Dict, List, Optional, Any, Generator
import logging
from urllib.parse import urljoin, urlencode
from datetime import datetime

from .base_scraper import BaseScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestsScraper(BaseScraper):
    
    def __init__(self, delay: float = 2.0, user_agent: str = "RedditScraper/1.0"):
        
        super().__init__(delay)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'application/json'
        })
        
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        
        try:
            logger.debug(f"Fetching: {url} with params: {params}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            self._sleep_with_delay()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode failed for {url}: {e}")
            return None
    
    def scrape_subreddit_paginated(self, subreddit: str, sort_by: str = "hot",
                                  max_posts: int = 1000, batch_size: int = 100) -> Generator[Dict[str, Any], None, None]:

        url = f"https://www.reddit.com/r/{subreddit}/{sort_by}.json"
        after = None
        posts_fetched = 0
        
        while posts_fetched < max_posts:
            params = {
                'limit': min(batch_size, 100),  
                'raw_json': 1
            }
            
            if after:
                params['after'] = after
                
            data = self._make_request(url, params)
            if not data or 'data' not in data:
                logger.warning("No more data available or request failed")
                break
                
            children = data['data'].get('children', [])
            if not children:
                logger.info("No more posts available")
                break
                
            for child in children:
                if child['kind'] == 't3' and posts_fetched < max_posts:
                    cleaned_post = self._clean_post_data(child['data'])
                    yield cleaned_post
                    posts_fetched += 1
                    
            after = data['data'].get('after')
            if not after:
                logger.info("Reached end of available posts")
                break
                
        logger.info(f"Finished scraping {posts_fetched} posts from r/{subreddit}")
    
    def scrape_multiple_subreddits(self, subreddits: List[str], sort_by: str = "hot",
                                  posts_per_subreddit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        
        results = {}
        
        for subreddit in subreddits:
            logger.info(f"Scraping r/{subreddit}")
            posts = list(self.scrape_subreddit_paginated(
                subreddit, sort_by, posts_per_subreddit
            ))
            results[subreddit] = posts
            
            time.sleep(self.delay * 2)
            
        return results
    
    def scrape_comments_deep(self, subreddit: str, post_id: str, 
                           max_depth: int = 10) -> Dict[str, Any]:
        
        url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        params = {
            'raw_json': 1,
            'limit': 500,  
            'depth': max_depth
        }
        
        data = self._make_request(url, params)
        if not data or not isinstance(data, list) or len(data) < 2:
            return {}
            
        post_data = data[0]['data']['children'][0]['data'] if data[0]['data']['children'] else {}
        
        all_comments = []
        self._extract_all_comments(data[1]['data']['children'], all_comments)
        
        return {
            'post': post_data,
            'comments': all_comments,
            'total_comments': len(all_comments)
        }
    
    def _extract_all_comments(self, comments_children: List[Dict], 
                             all_comments: List[Dict[str, Any]], depth: int = 0) -> None:
        
        for child in comments_children:
            if child['kind'] == 't1':  
                comment_data = child['data']
                comment = self._clean_comment_data(comment_data)
                comment['depth'] = depth
                if comment_data.get('permalink'):
                    comment['permalink'] = comment_data.get('permalink')
                all_comments.append(comment)
                
                if 'replies' in comment_data and comment_data['replies']:
                    if isinstance(comment_data['replies'], dict):
                        reply_children = comment_data['replies']['data']['children']
                        self._extract_all_comments(reply_children, all_comments, depth + 1)
    
    def search_advanced(self, query: str, subreddit: Optional[str] = None,
                       sort_by: str = "relevance", time_filter: str = "all",
                       max_results: int = 1000) -> Generator[Dict[str, Any], None, None]:
        
        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            restrict_sr = 'on'
        else:
            url = "https://www.reddit.com/search.json"
            restrict_sr = 'off'
        
        after = None
        results_fetched = 0
        
        while results_fetched < max_results:
            params = {
                'q': query,
                'restrict_sr': restrict_sr,
                'sort': sort_by,
                't': time_filter,
                'limit': min(100, max_results - results_fetched),
                'raw_json': 1
            }
            
            if after:
                params['after'] = after
                
            data = self._make_request(url, params)
            if not data or 'data' not in data:
                break
                
            children = data['data'].get('children', [])
            if not children:
                break
                
            for child in children:
                if child['kind'] == 't3' and results_fetched < max_results:
                    cleaned_post = self._clean_post_data(child['data'])
                    yield cleaned_post
                    results_fetched += 1
                    
            after = data['data'].get('after')
            if not after:
                break
                
        logger.info(f"Found {results_fetched} results for query: '{query}'")
    
    def scrape_user_activity(self, username: str, activity_type: str = "submitted",
                           max_items: int = 1000) -> Generator[Dict[str, Any], None, None]:

        url = f"https://www.reddit.com/user/{username}/{activity_type}.json"
        after = None
        items_fetched = 0
        
        while items_fetched < max_items:
            params = {
                'limit': min(100, max_items - items_fetched),
                'raw_json': 1
            }
            
            if after:
                params['after'] = after
                
            data = self._make_request(url, params)
            if not data or 'data' not in data:
                break
                
            children = data['data'].get('children', [])
            if not children:
                break
                
            for child in children:
                if items_fetched < max_items:
                    item_data = child['data']
                    item_data['item_type'] = 'post' if child['kind'] == 't3' else 'comment'
                    yield item_data
                    items_fetched += 1
                    
            after = data['data'].get('after')
            if not after:
                break
                
        logger.info(f"Scraped {items_fetched} {activity_type} items from u/{username}")
    
    def bulk_scrape_subreddits(self, subreddit_list_file: str, 
                              output_format: str = "json") -> None:
        
        try:
            with open(subreddit_list_file, 'r') as f:
                subreddits = [line.strip() for line in f if line.strip()]
                
            for subreddit in subreddits:
                logger.info(f"Bulk scraping r/{subreddit}")
                posts = list(self.scrape_subreddit_paginated(subreddit, max_posts=500))
                
                filename = f"{subreddit}_posts.{output_format}"
                if output_format == "json":
                    with open(filename, 'w') as f:
                        json.dump(posts, f, indent=2)
                        
                logger.info(f"Saved {len(posts)} posts to {filename}")
                
                time.sleep(self.delay * 3)
                
        except FileNotFoundError:
            logger.error(f"Subreddit list file not found: {subreddit_list_file}")
        except Exception as e:
            logger.error(f"Error in bulk scraping: {e}")