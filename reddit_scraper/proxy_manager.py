import requests
import random
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: str
    password: str
    proxy_type: str  
    is_healthy: bool = True
    last_checked: float = 0
    failure_count: int = 0
    success_count: int = 0


class ProxyManager:
    
    def __init__(self, health_check_interval: int = 300, max_failures: int = 3):
        
        self.proxies: List[ProxyConfig] = []
        self.current_proxy_index = 0
        self.health_check_interval = health_check_interval
        self.max_failures = max_failures
        self.lock = threading.Lock()
        self.health_check_urls = [
            "http://httpbin.org/ip",
            "https://api.ipify.org?format=json",
            "http://icanhazip.com"
        ]
        
    def add_proxy(self, host: str, port: int, username: str, password: str, 
                  proxy_type: str = "http") -> None:
        proxy = ProxyConfig(
            host=host,
            port=port,
            username=username,
            password=password,
            proxy_type=proxy_type.lower()
        )
        self.proxies.append(proxy)
        logger.info(f"Added {proxy_type.upper()} proxy: {host}:{port}")
        
    def add_proxy_from_string(self, proxy_string: str, proxy_type: str = "http") -> None:
        
        try:
            parts = proxy_string.split(':')
            if len(parts) == 4:
                host, port, username, password = parts
                self.add_proxy(host, int(port), username, password, proxy_type)
            else:
                logger.error(f"Invalid proxy format: {proxy_string}")
        except ValueError as e:
            logger.error(f"Error parsing proxy string {proxy_string}: {e}")
            
    def get_proxy_dict(self, proxy: ProxyConfig) -> Dict[str, str]:
        if proxy.proxy_type == "http":
            proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        elif proxy.proxy_type == "socks5":
            proxy_url = f"socks5://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        else:
            raise ValueError(f"Unsupported proxy type: {proxy.proxy_type}")
            
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        with self.lock:
            if not self.proxies:
                return None
                
            healthy_proxies = [p for p in self.proxies if p.is_healthy]
            if not healthy_proxies:
                logger.warning("No healthy proxies available!")
                return None
                
            proxy = healthy_proxies[self.current_proxy_index % len(healthy_proxies)]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(healthy_proxies)
            
            logger.debug(f"Using proxy: {proxy.host}:{proxy.port}")
            return self.get_proxy_dict(proxy)
            
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        with self.lock:
            healthy_proxies = [p for p in self.proxies if p.is_healthy]
            if not healthy_proxies:
                return None
                
            proxy = random.choice(healthy_proxies)
            logger.debug(f"Using random proxy: {proxy.host}:{proxy.port}")
            return self.get_proxy_dict(proxy)
            
    def get_next_http_proxy(self) -> Optional[Dict[str, str]]:
        with self.lock:
            if not self.proxies:
                return None
                
            http_proxies = [p for p in self.proxies if p.is_healthy and p.proxy_type == 'http']
            if not http_proxies:
                logger.warning("No healthy HTTP proxies available!")
                return None
                
            proxy = http_proxies[self.current_proxy_index % len(http_proxies)]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(http_proxies)
            
            logger.debug(f"Using HTTP proxy: {proxy.host}:{proxy.port}")
            return self.get_proxy_dict(proxy)
            
    def check_proxy_health(self, proxy: ProxyConfig) -> bool:
        try:
            proxy_dict = self.get_proxy_dict(proxy)
            test_url = random.choice(self.health_check_urls)
            
            response = requests.get(
                test_url,
                proxies=proxy_dict,
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            if response.status_code == 200:
                proxy.success_count += 1
                proxy.failure_count = 0  
                proxy.is_healthy = True
                proxy.last_checked = time.time()
                logger.debug(f"Proxy {proxy.host}:{proxy.port} is healthy")
                return True
            else:
                raise requests.exceptions.RequestException(f"Status code: {response.status_code}")
                
        except Exception as e:
            proxy.failure_count += 1
            if proxy.failure_count >= self.max_failures:
                proxy.is_healthy = False
                logger.warning(f"Proxy {proxy.host}:{proxy.port} marked as unhealthy after {proxy.failure_count} failures")
            else:
                logger.debug(f"Proxy {proxy.host}:{proxy.port} failed health check: {e}")
            proxy.last_checked = time.time()
            return False
            
    def health_check_all(self) -> None:
        if not self.proxies:
            return
            
        logger.info("Starting proxy health check...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {
                executor.submit(self.check_proxy_health, proxy): proxy 
                for proxy in self.proxies
            }
            
            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Health check error for {proxy.host}:{proxy.port}: {e}")
                    
        healthy_count = sum(1 for p in self.proxies if p.is_healthy)
        logger.info(f"Health check complete: {healthy_count}/{len(self.proxies)} proxies healthy")
        
    def get_proxy_stats(self) -> Dict[str, Any]:
        total_proxies = len(self.proxies)
        healthy_proxies = sum(1 for p in self.proxies if p.is_healthy)
        
        stats = {
            'total_proxies': total_proxies,
            'healthy_proxies': healthy_proxies,
            'unhealthy_proxies': total_proxies - healthy_proxies,
            'health_rate': (healthy_proxies / total_proxies * 100) if total_proxies > 0 else 0,
            'proxy_details': []
        }
        
        for proxy in self.proxies:
            stats['proxy_details'].append({
                'host': proxy.host,
                'port': proxy.port,
                'type': proxy.proxy_type,
                'is_healthy': proxy.is_healthy,
                'success_count': proxy.success_count,
                'failure_count': proxy.failure_count,
                'last_checked': proxy.last_checked
            })
            
        return stats
        
    def mark_proxy_failed(self, proxy_dict: Dict[str, str]) -> None:

        try:
            proxy_url = proxy_dict.get('http', proxy_dict.get('https', ''))
            if '@' in proxy_url:
                host_port = proxy_url.split('@')[1]
                host = host_port.split(':')[0]
                port = int(host_port.split(':')[1])
                
                with self.lock:
                    for proxy in self.proxies:
                        if proxy.host == host and proxy.port == port:
                            proxy.failure_count += 1
                            if proxy.failure_count >= self.max_failures:
                                proxy.is_healthy = False
                                logger.warning(f"Proxy {host}:{port} marked unhealthy due to failures")
                            break
        except Exception as e:
            logger.error(f"Error marking proxy as failed: {e}")
            
    def start_health_monitoring(self) -> None:
        
        def monitor():
            while True:
                time.sleep(self.health_check_interval)
                self.health_check_all()
                
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        logger.info("Started proxy health monitoring thread")


def create_default_proxy_manager() -> ProxyManager:
    
    from .config import get_config_manager
    
    config_manager = get_config_manager("config.json")
    manager = ProxyManager()
    
    if config_manager.has_proxies():
        for proxy_config in config_manager.get_proxies():
            manager.add_proxy(
                proxy_config.host,
                proxy_config.port,
                proxy_config.username,
                proxy_config.password,
                proxy_config.proxy_type
            )
        manager.health_check_all()
    
    return manager