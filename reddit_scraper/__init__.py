__version__ = "0.1.0"
__author__ = "Reddit Scraper Team"

from .base_scraper import BaseScraper
from .json_scraper import JSONScraper
from .requests_scraper import RequestsScraper
from .proxy_manager import ProxyManager
from .captcha_solver import CaptchaSolverManager
from .config import get_config_manager, ConfigManager
from .validation import ValidationError


__all__ = ["BaseScraper", "JSONScraper", "RequestsScraper", "ProxyManager", 
           "CaptchaSolverManager", "ConfigManager", "get_config_manager", "ValidationError"]