import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
    
    def _clean_post_data(self, raw_post: Dict[str, Any]) -> Dict[str, Any]:

        essential_fields = {
            'id': raw_post.get('id'),
            'title': raw_post.get('title'),
            'author': raw_post.get('author'),
            'selftext': raw_post.get('selftext'),
            'score': raw_post.get('score'),
            'upvote_ratio': raw_post.get('upvote_ratio'),
            'num_comments': raw_post.get('num_comments'),
            'created_utc': raw_post.get('created_utc'),
            'subreddit': raw_post.get('subreddit'),
            'permalink': raw_post.get('permalink'),
            'url': raw_post.get('url'),
            'link_flair_text': raw_post.get('link_flair_text'),
        }
        
        if raw_post.get('edited'):
            essential_fields['edited'] = raw_post.get('edited')
        
        if raw_post.get('over_18'):
            essential_fields['over_18'] = raw_post.get('over_18')
            
        if raw_post.get('is_self'):
            essential_fields['is_self'] = raw_post.get('is_self')
            
        if not raw_post.get('is_self') and raw_post.get('domain'):
            essential_fields['domain'] = raw_post.get('domain')
        
        return {k: v for k, v in essential_fields.items() if v is not None}
    
    def _clean_comment_data(self, raw_comment: Dict[str, Any]) -> Dict[str, Any]:

        essential_fields = {
            'id': raw_comment.get('id'),
            'author': raw_comment.get('author'),
            'body': raw_comment.get('body'),
            'score': raw_comment.get('score'),
            'created_utc': raw_comment.get('created_utc'),
            'parent_id': raw_comment.get('parent_id'),
        }
        
        if 'replies' in raw_comment and raw_comment['replies']:
            essential_fields['replies'] = raw_comment.get('replies', [])
        
        return {k: v for k, v in essential_fields.items() if v is not None}
    
    def _extract_comments(self, comments_children: List[Dict]) -> List[Dict[str, Any]]:

        comments = []
        
        for child in comments_children:
            if child['kind'] == 't1':
                comment_data = child['data']
                comment = self._clean_comment_data(comment_data)
                
                if 'replies' in comment_data and comment_data['replies']:
                    if isinstance(comment_data['replies'], dict):
                        reply_children = comment_data['replies']['data']['children']
                        comment['replies'] = self._extract_comments(reply_children)
                    else:
                        comment['replies'] = []
                
                comments.append(comment)
                
        return comments
    
    def _sleep_with_delay(self) -> None:
        if self.delay > 0:
            time.sleep(self.delay)
    
    async def _async_sleep_with_delay(self) -> None:
        if self.delay > 0:
            await asyncio.sleep(self.delay)
    
    @abstractmethod
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:

        pass