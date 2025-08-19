import os
import json
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: str
    password: str
    proxy_type: str  


@dataclass
class CaptchaConfig:
    api_key: str
    provider: str = "capsolver"
    site_keys: Optional[Dict[str, str]] = None  


@dataclass
class ScrapingConfig:
    default_delay: float = 1.0
    max_retries: int = 3
    requests_per_minute: int = 60
    user_agent: str = "RedditScraper/1.0.0"
    rotate_user_agents: bool = True


class ConfigManager:
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.proxies: List[ProxyConfig] = []
        self.captcha_solvers: List[CaptchaConfig] = []
        self.scraping_config = ScrapingConfig()
        
        self._load_config()
    
    def _load_config(self):
        self._load_from_env()
        
        if self.config_file and os.path.exists(self.config_file):
            self._load_from_file()
    
    def _load_from_env(self):
        self._load_proxies_from_env()
        
        self._load_captcha_from_env()
        
        self._load_scraping_from_env()
    
    def _load_proxies_from_env(self):
        proxies_json = os.getenv('PROXIES_JSON')
        if proxies_json:
            try:
                proxy_data = json.loads(proxies_json)
                for proxy in proxy_data:
                    self.proxies.append(ProxyConfig(**proxy))
                return
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse PROXIES_JSON: {e}")
        
        http_host = os.getenv('PROXY_HTTP_HOST')
        if http_host:
            self.proxies.append(ProxyConfig(
                host=http_host,
                port=int(os.getenv('PROXY_HTTP_PORT', 8080)),
                username=os.getenv('PROXY_HTTP_USERNAME', ''),
                password=os.getenv('PROXY_HTTP_PASSWORD', ''),
                proxy_type='http'
            ))
        
        socks_host = os.getenv('PROXY_SOCKS_HOST')
        if socks_host:
            self.proxies.append(ProxyConfig(
                host=socks_host,
                port=int(os.getenv('PROXY_SOCKS_PORT', 1080)),
                username=os.getenv('PROXY_SOCKS_USERNAME', ''),
                password=os.getenv('PROXY_SOCKS_PASSWORD', ''),
                proxy_type='socks5'
            ))
    
    def _load_captcha_from_env(self):
        captcha_json = os.getenv('CAPTCHA_SOLVERS_JSON')
        if captcha_json:
            try:
                captcha_data = json.loads(captcha_json)
                for captcha in captcha_data:
                    self.captcha_solvers.append(CaptchaConfig(**captcha))
                return
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse CAPTCHA_SOLVERS_JSON: {e}")
        
        capsolver_key = os.getenv('CAPSOLVER_API_KEY')
        if capsolver_key:
            self.captcha_solvers.append(CaptchaConfig(
                api_key=capsolver_key,
                provider='capsolver'
            ))
    
    def _load_scraping_from_env(self):
        self.scraping_config.default_delay = float(os.getenv('DEFAULT_DELAY', 1.0))
        self.scraping_config.max_retries = int(os.getenv('MAX_RETRIES', 3))
        self.scraping_config.requests_per_minute = int(os.getenv('REQUESTS_PER_MINUTE', 60))
        self.scraping_config.user_agent = os.getenv('USER_AGENT', 'RedditScraper/1.0.0')
        self.scraping_config.rotate_user_agents = os.getenv('ROTATE_USER_AGENTS', 'true').lower() == 'true'
    
    def _load_from_file(self):
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            if 'proxies' in config_data:
                self.proxies.extend([
                    ProxyConfig(**proxy) for proxy in config_data['proxies']
                ])
            
            if 'captcha_solvers' in config_data:
                for captcha_data in config_data['captcha_solvers']:
                    captcha_config = CaptchaConfig(
                        api_key=captcha_data['api_key'],
                        provider=captcha_data.get('provider', 'capsolver'),
                        site_keys=captcha_data.get('site_keys', {})
                    )
                    self.captcha_solvers.append(captcha_config)
            
            if 'scraping' in config_data:
                scraping_data = config_data['scraping']
                for key, value in scraping_data.items():
                    if hasattr(self.scraping_config, key):
                        setattr(self.scraping_config, key, value)
                        
        except Exception as e:
            logger.warning(f"Failed to load config file {self.config_file}: {e}")
    
    def get_proxies(self) -> List[ProxyConfig]:
        return self.proxies
    
    def get_captcha_solvers(self) -> List[CaptchaConfig]:
        return self.captcha_solvers
    
    def get_scraping_config(self) -> ScrapingConfig:
        return self.scraping_config
    
    def has_proxies(self) -> bool:
        return len(self.proxies) > 0
    
    def has_captcha_solvers(self) -> bool:
        return len(self.captcha_solvers) > 0
    
    def save_example_config(self, file_path: str = "config.json"):
        example_config = {
            "proxies": [
                {
                    "host": "proxy1.example.com",
                    "port": 8080,
                    "username": "user1",
                    "password": "pass1",
                    "proxy_type": "http"
                },
                {
                    "host": "proxy2.example.com",
                    "port": 1080,
                    "username": "user2",
                    "password": "pass2",
                    "proxy_type": "socks5"
                }
            ],
            "captcha_solvers": [
                {
                    "api_key": "CAP-XXXXXXXXXXXXXXX",
                    "provider": "capsolver",
                    "site_keys": {
                        "reddit.com": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
                        "www.reddit.com": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"
                    }
                }
            ],
            "scraping": {
                "default_delay": 1.0,
                "max_retries": 3,
                "requests_per_minute": 60,
                "user_agent": "RedditScraper/1.0.0",
                "rotate_user_agents": True
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(example_config, f, indent=2)
        
        logger.info(f"Example configuration saved to {file_path}")
    
    def validate_config(self) -> Dict[str, Any]:
        status = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "proxy_count": len(self.proxies),
            "captcha_solver_count": len(self.captcha_solvers)
        }
        
        for i, proxy in enumerate(self.proxies):
            if not proxy.host or not proxy.port:
                status["errors"].append(f"Proxy {i+1}: Missing host or port")
                status["valid"] = False
        
        for i, captcha in enumerate(self.captcha_solvers):
            if not captcha.api_key:
                status["errors"].append(f"Captcha solver {i+1}: Missing API key")
                status["valid"] = False
        
        if not self.proxies:
            status["warnings"].append("No proxies configured - scraping may be limited")
        
        if not self.captcha_solvers:
            status["warnings"].append("No captcha solvers configured - may fail on protected content")
        
        return status


_config_manager = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        if config_file is None and os.path.exists("config.json"):
            config_file = "config.json"
        _config_manager = ConfigManager(config_file)
    return _config_manager


def reload_config(config_file: Optional[str] = None):
    global _config_manager
    _config_manager = ConfigManager(config_file)