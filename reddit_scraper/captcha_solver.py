import requests
import time
import base64
import logging
from typing import Dict, Optional, Any, Union
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    RECAPTCHA_V2 = "ReCaptchaV2TaskProxyLess"
    RECAPTCHA_V3 = "ReCaptchaV3TaskProxyLess"
    HCAPTCHA = "HCaptchaTaskProxyLess"
    FUNCAPTCHA = "FunCaptchaTaskProxyLess"
    IMAGE_TO_TEXT = "ImageToTextTask"
    RECAPTCHA_V2_ENTERPRISE = "ReCaptchaV2EnterpriseTaskProxyLess"
    RECAPTCHA_V3_ENTERPRISE = "ReCaptchaV3EnterpriseTaskProxyLess"


@dataclass
class CaptchaSolution:
    success: bool
    solution: Optional[str] = None
    error_message: Optional[str] = None
    task_id: Optional[str] = None
    cost: Optional[float] = None


class CapsolverAPI:
    
    def __init__(self, api_key: str, base_url: str = "https://api.capsolver.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'RedditScraper-Capsolver/1.0'
        })
        
    def create_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        
        payload = {
            "clientKey": self.api_key,
            "task": task_data
        }
        
        try:
            response = self.session.post(f"{self.base_url}/createTask", json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get("errorId") == 0:
                task_id = result.get("taskId")
                logger.info(f"Created captcha task: {task_id}")
                return task_id
            else:
                logger.error(f"Failed to create task: {result.get('errorDescription')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed when creating task: {e}")
            return None
            
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        
        payload = {
            "clientKey": self.api_key,
            "taskId": task_id
        }
        
        try:
            response = self.session.post(f"{self.base_url}/getTaskResult", json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get("errorId") == 0:
                if result.get("status") == "ready":
                    return result.get("solution")
                elif result.get("status") == "processing":
                    return None 
                else:
                    logger.error(f"Task failed: {result.get('errorDescription')}")
                    return None
            else:
                logger.error(f"Error getting task result: {result.get('errorDescription')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed when getting task result: {e}")
            return None
            
    def solve_captcha_async(self, task_data: Dict[str, Any], 
                           max_wait_time: int = 120, poll_interval: int = 3) -> CaptchaSolution:
        
        task_id = self.create_task(task_data)
        if not task_id:
            return CaptchaSolution(success=False, error_message="Failed to create task")
            
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            time.sleep(poll_interval)
            
            solution = self.get_task_result(task_id)
            if solution:
                logger.info(f"Captcha solved successfully: {task_id}")
                return CaptchaSolution(
                    success=True,
                    solution=solution.get("gRecaptchaResponse") or solution.get("text") or solution.get("token"),
                    task_id=task_id
                )
                
        return CaptchaSolution(
            success=False, 
            error_message="Timeout waiting for captcha solution",
            task_id=task_id
        )
        
    def solve_recaptcha_v2(self, website_url: str, website_key: str, 
                          proxy: Optional[Dict[str, str]] = None) -> CaptchaSolution:
        
        task_data = {
            "type": CaptchaType.RECAPTCHA_V2.value,
            "websiteURL": website_url,
            "websiteKey": website_key
        }
        
        if proxy:
            task_data.update({
                "type": "ReCaptchaV2Task", 
                "proxyType": "http",
                "proxyAddress": proxy.get("host"),
                "proxyPort": proxy.get("port"),
                "proxyLogin": proxy.get("username"),
                "proxyPassword": proxy.get("password")
            })
            
        return self.solve_captcha_async(task_data)
        
    def solve_recaptcha_v3(self, website_url: str, website_key: str, 
                          action: str = "submit", min_score: float = 0.3) -> CaptchaSolution:
        
        task_data = {
            "type": CaptchaType.RECAPTCHA_V3.value,
            "websiteURL": website_url,
            "websiteKey": website_key,
            "pageAction": action,
            "minScore": min_score
        }
        
        return self.solve_captcha_async(task_data)
        
    def solve_hcaptcha(self, website_url: str, website_key: str) -> CaptchaSolution:
        
        task_data = {
            "type": CaptchaType.HCAPTCHA.value,
            "websiteURL": website_url,
            "websiteKey": website_key
        }
        
        return self.solve_captcha_async(task_data)
        
    def solve_image_captcha(self, image_data: Union[str, bytes], 
                           case_sensitive: bool = False) -> CaptchaSolution:
        
        if isinstance(image_data, bytes):
            image_b64 = base64.b64encode(image_data).decode('utf-8')
        else:
            image_b64 = image_data
            
        task_data = {
            "type": CaptchaType.IMAGE_TO_TEXT.value,
            "body": image_b64,
            "case": case_sensitive
        }
        
        return self.solve_captcha_async(task_data)
        
    def get_balance(self) -> Optional[float]:
        
        payload = {"clientKey": self.api_key}
        
        try:
            response = self.session.post(f"{self.base_url}/getBalance", json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get("errorId") == 0:
                balance = result.get("balance", 0)
                logger.info(f"Account balance: ${balance}")
                return float(balance)
            else:
                logger.error(f"Failed to get balance: {result.get('errorDescription')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed when getting balance: {e}")
            return None


class CaptchaSolverManager: 
    
    def __init__(self, captcha_config_or_api_key, max_retries: int = 3, site_keys: Optional[Dict[str, str]] = None):
        if hasattr(captcha_config_or_api_key, 'api_key'):  
            config = captcha_config_or_api_key
            self.solver = CapsolverAPI(config.api_key)
            self.max_retries = max_retries
            self.site_keys = config.site_keys or {}
        else:  
            api_key = captcha_config_or_api_key
            self.solver = CapsolverAPI(api_key)
            self.max_retries = max_retries
            self.site_keys = site_keys or {}
    
    def get_site_key(self, url: str) -> Optional[str]:
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            if domain in self.site_keys:
                return self.site_keys[domain]
            
            if domain.startswith('www.'):
                base_domain = domain[4:]
                if base_domain in self.site_keys:
                    return self.site_keys[base_domain]
            
            www_domain = f"www.{domain}"
            if www_domain in self.site_keys:
                return self.site_keys[www_domain]
                
            logger.warning(f"No site key configured for domain: {domain}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing URL {url}: {e}")
            return None
        
    def solve_with_retry(self, solve_func, *args, **kwargs) -> CaptchaSolution:
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                wait_time = 2 ** attempt  
                logger.info(f"Retrying captcha solve in {wait_time} seconds (attempt {attempt + 1}/{self.max_retries + 1})")
                time.sleep(wait_time)
                
            try:
                solution = solve_func(*args, **kwargs)
                if solution.success:
                    return solution
                else:
                    last_error = solution.error_message
                    logger.warning(f"Captcha solve attempt {attempt + 1} failed: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Exception during captcha solve attempt {attempt + 1}: {e}")
                
        return CaptchaSolution(
            success=False,
            error_message=f"Failed after {self.max_retries + 1} attempts. Last error: {last_error}"
        )
        
    def check_balance_and_solve(self, solve_func, *args, **kwargs) -> CaptchaSolution:
        
        balance = self.solver.get_balance()
        if balance is None:
            return CaptchaSolution(success=False, error_message="Failed to check account balance")
        elif balance < 0.01:  
            return CaptchaSolution(success=False, error_message=f"Insufficient balance: ${balance}")
            
        logger.info(f"Account balance: ${balance} - proceeding with captcha solve")
        return self.solve_with_retry(solve_func, *args, **kwargs)


def create_default_captcha_solver() -> CaptchaSolverManager:
    
    from .config import get_config_manager
    
    config_manager = get_config_manager("config.json")
    
    if config_manager.has_captcha_solvers():
        captcha_configs = config_manager.get_captcha_solvers()
        if captcha_configs:
            config = captcha_configs[0]
            return CaptchaSolverManager(
                api_key=config.api_key,
                site_keys=config.site_keys or {}
            )
    
    raise ValueError("No captcha solver API key found in config.json. Please add your API key to the configuration file.")