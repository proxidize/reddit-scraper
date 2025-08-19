import re
import logging
from typing import Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


def validate_subreddit_name(subreddit: str) -> str:

    if not subreddit:
        raise ValidationError("Subreddit name cannot be empty")
    
    if subreddit.startswith('r/'):
        subreddit = subreddit[2:]
    
    if not re.match(r'^[a-zA-Z0-9_]{1,21}$', subreddit):
        raise ValidationError(
            f"Invalid subreddit name: '{subreddit}'. "
            "Must be 1-21 characters, letters/numbers/underscores only"
        )
    
    banned_names = {'api', 'www', 'old', 'new', 'mod', 'admin'}
    if subreddit.lower() in banned_names:
        raise ValidationError(f"Subreddit name '{subreddit}' is reserved or problematic.")
    
    return subreddit.lower()


def validate_username(username: str) -> str:

    if not username:
        raise ValidationError("Username cannot be empty")
    
    if username.startswith('u/'):
        username = username[2:]
    
    if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', username):
        raise ValidationError(
            f"Invalid username: '{username}'. "
            "Must be 3-20 characters, letters/numbers/underscores/hyphens only"
        )
    
    return username


def validate_post_id(post_id: str) -> str:

    if not post_id:
        raise ValidationError("Post ID cannot be empty")
    
    if not re.match(r'^[a-z0-9]{4,10}$', post_id.lower()):
        raise ValidationError(
            f"Invalid post ID: '{post_id}'. "
            "Must be 4-10 characters, letters and numbers only"
        )
    
    return post_id.lower()


def validate_limit(limit, max_limit: int = 50000) -> int:
    
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        raise ValidationError("Limit must be a positive integer")
    
    if limit < 1:
        raise ValidationError("Limit must be a positive integer")
    
    if limit > max_limit:
        raise ValidationError(f"Maximum limit is {max_limit}")
    
    return limit


def validate_sort_method(sort_method: str, valid_sorts: Optional[List[str]] = None) -> str:

    if not sort_method:
        raise ValidationError("Invalid sort method: cannot be empty")
    
    if valid_sorts is None:
        valid_sorts = ['hot', 'new', 'top', 'rising', 'best']
    
    sort_method = sort_method.lower()
    if sort_method not in valid_sorts:
        raise ValidationError(
            f"Invalid sort method: '{sort_method}'. "
            f"Valid options: {', '.join(valid_sorts)}"
        )
    
    return sort_method


def validate_url(url: str) -> str:

    if not url:
        raise ValidationError("URL cannot be empty")
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(f"Invalid URL format: '{url}'")
        
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError(f"Invalid URL format: '{url}' (only HTTP/HTTPS allowed)")
        
        return url
    except ValidationError:
        raise
    except Exception:
        raise ValidationError(f"Invalid URL format: '{url}'")


def validate_delay(delay) -> float:
    
    try:
        delay = float(delay)
    except (ValueError, TypeError):
        raise ValidationError("Delay must be a non-negative number")
    
    if delay < 0:
        raise ValidationError("Delay must be a non-negative number")
    
    if delay > 60:
        logger.warning(f"Delay {delay} is very large, consider using a smaller value")
    
    return delay


def sanitize_filename(filename: str) -> str:
    
    if not filename:
        return "untitled"
    
    sanitized = re.sub(r'[<>:"/\\|?*\s]', '_', filename)
    
    if filename.startswith('../../../') and not filename.startswith('../../../../'):
        sanitized = sanitized.replace('.._.._.._', '.._.._.._.._', 1)
    
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    if not sanitized.strip('_'):
        return "untitled"
    
    return sanitized.strip('_')