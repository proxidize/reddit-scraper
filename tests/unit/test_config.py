import pytest
import json
import tempfile
import os
from unittest.mock import patch, mock_open

from reddit_scraper.config import ConfigManager, ProxyConfig, CaptchaConfig, ScrapingConfig


@pytest.mark.unit
class TestProxyConfig:
    
    def test_proxy_config_creation(self):
        config = ProxyConfig(
            host="proxy.example.com",
            port=8080,
            username="user",
            password="pass",
            proxy_type="http"
        )
        
        assert config.host == "proxy.example.com"
        assert config.port == 8080
        assert config.username == "user"
        assert config.password == "pass"
        assert config.proxy_type == "http"


@pytest.mark.unit
class TestCaptchaConfig:
    
    def test_captcha_config_creation(self):
        site_keys = {"reddit.com": "test-key"}
        config = CaptchaConfig(
            api_key="test-api-key",
            provider="capsolver",
            site_keys=site_keys
        )
        
        assert config.api_key == "test-api-key"
        assert config.provider == "capsolver"
        assert config.site_keys == site_keys
    
    def test_captcha_config_defaults(self):
        config = CaptchaConfig(api_key="test-key")
        
        assert config.api_key == "test-key"
        assert config.provider == "capsolver"
        assert config.site_keys is None


@pytest.mark.unit
class TestScrapingConfig:
    
    def test_scraping_config_defaults(self):
        config = ScrapingConfig()
        
        assert config.default_delay == 1.0
        assert config.max_retries == 3
        assert config.requests_per_minute == 60
        assert config.user_agent == "RedditScraper/1.0.0"
        assert config.rotate_user_agents is True


@pytest.mark.unit
class TestConfigManager:
    
    def test_config_manager_init_no_file(self):
        with patch('os.path.exists', return_value=False):
            manager = ConfigManager("nonexistent.json")
            
            assert len(manager.proxies) == 0
            assert len(manager.captcha_solvers) == 0
            assert isinstance(manager.scraping_config, ScrapingConfig)
    
    def test_config_manager_init_with_file(self):
        config_data = {
            "proxies": [
                {
                    "host": "proxy.example.com",
                    "port": 8080,
                    "username": "user",
                    "password": "pass",
                    "proxy_type": "http"
                }
            ],
            "captcha_solvers": [
                {
                    "api_key": "test-key",
                    "provider": "capsolver",
                    "site_keys": {"reddit.com": "site-key"}
                }
            ],
            "scraping": {
                "default_delay": 2.0,
                "max_retries": 5
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            try:
                json.dump(config_data, tmp)
                tmp.flush()
                
                manager = ConfigManager(tmp.name)
                
                assert len(manager.proxies) == 1
                assert manager.proxies[0].host == "proxy.example.com"
                assert len(manager.captcha_solvers) == 1
                assert manager.captcha_solvers[0].api_key == "test-key"
                assert manager.scraping_config.default_delay == 2.0
                
            finally:
                os.unlink(tmp.name)
    
    @patch.dict(os.environ, {
        'PROXY_HTTP_HOST': 'env-proxy.com',
        'PROXY_HTTP_PORT': '9090',
        'PROXY_HTTP_USERNAME': 'env-user',
        'PROXY_HTTP_PASSWORD': 'env-pass'
    })
    def test_config_manager_env_variables(self):
        with patch('os.path.exists', return_value=False):
            manager = ConfigManager("nonexistent.json")
            
            assert len(manager.proxies) == 1
            assert manager.proxies[0].host == "env-proxy.com"
            assert manager.proxies[0].port == 9090
            assert manager.proxies[0].proxy_type == "http"
    
    @patch.dict(os.environ, {
        'CAPSOLVER_API_KEY': 'env-api-key'
    })
    def test_config_manager_captcha_env(self):
        with patch('os.path.exists', return_value=False):
            manager = ConfigManager("nonexistent.json")
            
            assert len(manager.captcha_solvers) == 1
            assert manager.captcha_solvers[0].api_key == "env-api-key"
    
    def test_config_manager_methods(self):
        manager = ConfigManager("nonexistent.json")
        
        assert not manager.has_proxies()
        assert not manager.has_captcha_solvers()
        
        assert manager.get_proxies() == []
        assert manager.get_captcha_solvers() == []
        assert isinstance(manager.get_scraping_config(), ScrapingConfig)
    
    def test_save_example_config(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            try:
                manager = ConfigManager("nonexistent.json")
                manager.save_example_config(tmp.name)
                
                with open(tmp.name, 'r') as f:
                    data = json.load(f)
                    
                assert 'proxies' in data
                assert 'captcha_solvers' in data
                assert 'scraping' in data
                assert len(data['proxies']) > 0
                assert len(data['captcha_solvers']) > 0
                
            finally:
                os.unlink(tmp.name)
    
    def test_validate_config(self):
        manager = ConfigManager("nonexistent.json")
        
        try:
            manager.validate_config()
        except Exception as e:
            pytest.fail(f"Config validation failed: {e}")
    
    def test_invalid_json_handling(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            try:
                tmp.write("invalid json content")
                tmp.flush()
                
                manager = ConfigManager(tmp.name)
                assert len(manager.proxies) == 0
                
            finally:
                os.unlink(tmp.name)