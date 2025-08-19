<div align="center">
  <a href="https://proxidize.com/" target="_blank" rel="noopener noreferrer">
    <img src="https://proxidize.com/wp-content/uploads/2025/08/new-logo.png" alt="Proxidize Logo" width="100%"/>
  </a>
</div>

# Reddit Scraper

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/proxidize/reddit-scraper)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

### Multiple Scraping Methods
- **JSON Endpoint Scraper** - Fast scraping using Reddit's `.json` endpoints (no authentication required)
- **Advanced Requests Scraper** - Custom pagination and bulk scraping capabilities

### Advanced Capabilities
- **Proxy Rotation** - Automatic proxy switching with health monitoring
- **Captcha Solving** - Automated captcha handling using [Capsolver API](https://docs.capsolver.com/en/api/)
- **User Agent Rotation** - Realistic browser simulation
- **Rate Limiting** - Respectful request throttling
- **Rich CLI Interface** - Beautiful command-line interface with progress bars
- **Multiple Export Formats** - JSON and CSV output with full comment thread data

## Installation

### Using uv (Recommended)
```bash
git clone https://github.com/proxidize/reddit-scraper.git
cd reddit-scraper

uv venv
source .venv/bin/activate 

uv pip install -e .
```

### Using pip
```bash
git clone https://github.com/proxidize/reddit-scraper.git
cd reddit-scraper

python -m venv .venv
source .venv/bin/activate 

pip install -e .
```

## Development

### Setup for Development
```bash
pip install -e .[dev]

uv pip install -e .[dev]
```

### Running Tests
```bash
python tests/run_tests.py

pytest tests/ -v --cov=reddit_scraper

pytest tests/unit/ -v -m unit        
pytest tests/integration/ -v -m integration  
pytest tests/ -v -m "not slow"     

pytest tests/ --cov=reddit_scraper --cov-report=html
```

### Test Markers
- `unit` - Fast unit tests
- `integration` - Integration tests that may hit external APIs
- `slow` - Slow tests that should be skipped in CI

## Docker Support

### Building and Running with Docker
```bash
docker build -t reddit-scraper .

docker run -v $(pwd)/config.json:/app/config.json reddit-scraper interactive --config config.json

docker run -v $(pwd)/config.json:/app/config.json reddit-scraper json subreddit python --limit 10 --config config.json

docker run -v $(pwd)/config.json:/app/config.json -v $(pwd)/output:/app/output reddit-scraper json subreddit python --limit 10 --output output/posts.json --config config.json
```

## Quick Start

### 1. Interactive Mode (Recommended)
```bash
python3 -m reddit_scraper.cli interactive

python3 -m reddit_scraper.cli interactive --config config.json
```

### 2. Direct Commands
```bash
python3 -m reddit_scraper.cli json subreddit python --limit 10

python3 -m reddit_scraper.cli json subreddit technology --config config.json --limit 50
```

**Note**: If you've properly installed the package with `pip install -e .`, you can use `reddit-scraper` directly instead of `python3 -m reddit_scraper.cli`

## Configuration

The scraper uses a JSON configuration file to manage all settings including proxies, captcha solvers, and scraping preferences.

Copy `config.example.json` to `config.json` and edit:

```json
{
  "proxies": [
    {
      "host": "proxy1.example.com",
      "port": 8080,
      "username": "your_proxy_username",
      "password": "your_proxy_password",
      "proxy_type": "http"
    },
    {
      "host": "proxy2.example.com",
      "port": 1080,
      "username": "your_proxy_username",
      "password": "your_proxy_password",
      "proxy_type": "socks5"
    }
  ],
  "captcha_solvers": [
    {
      "api_key": "CAP-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
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
    "rotate_user_agents": true
  }
}
```

### Key Features

- **Multiple Proxies**: Add multiple HTTP and SOCKS5 proxies for automatic rotation
- **Captcha Solving**: Integrate with Capsolver for automated captcha handling with custom site keys
- **Input Validation**: Automatic validation of subreddit names, usernames, and other inputs
- **Flexible Configuration**: Easy JSON-based configuration management with validation
- **Health Monitoring**: Built-in proxy health checking and performance monitoring

### Setup Commands
```bash
cp config.example.json config.json

nano config.json  

python3 -m reddit_scraper.cli status --config config.json
```

## Data Validation & Processing

The scraper includes robust input validation and data processing capabilities:

### Input Validation
- **Subreddit Names**: Validates format, length (1-21 chars), and checks for reserved names
- **Usernames**: Validates Reddit username format (3-20 chars, alphanumeric plus underscore/hyphen)
- **Post IDs**: Ensures proper Reddit post ID format
- **URLs**: Validates and normalizes Reddit URLs

### Data Processing
- **Comment Threading**: Maintains proper parent-child relationships in comment trees
- **Data Cleaning**: Removes unnecessary metadata while preserving essential information
- **Field Standardization**: Consistent field names and data types across all scraped content

### Error Handling
```python
from reddit_scraper import ValidationError

try:
    posts = scraper.scrape_subreddit("invalid-name!", "hot", 10)
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Available Commands

### Interactive Mode
```bash
python3 -m reddit_scraper.cli interactive [--config CONFIG_FILE]
```

### Core Scraping Commands

#### JSON Scraper (Fastest)
```bash
python3 -m reddit_scraper.cli json subreddit SUBREDDIT_NAME [--config CONFIG_FILE] [options]

python3 -m reddit_scraper.cli json user USERNAME [options]

python3 -m reddit_scraper.cli json comments SUBREDDIT POST_ID [options]

python3 -m reddit_scraper.cli json subreddit-with-comments SUBREDDIT_NAME [options]
```

#### Comment Scraping
Extract rich comment data with full thread structure:

```bash
python3 -m reddit_scraper.cli json subreddit-with-comments python --limit 10 --include-comments --comment-limit 20 --output posts_with_comments.json

python3 -m reddit_scraper.cli json comments python POST_ID --sort best --output single_post_comments.json

python3 -m reddit_scraper.cli json user username --limit 25 --sort top --output user_posts.json
```

**Comment Data Includes:**
- Author information and scores
- Full comment text and timestamps  
- Nested reply structure
- Thread hierarchy and relationships
- Community engagement metrics

**Real Example (Actual Scraped Data):**
```json
{
  "title": "A simple home server to wirelessly stream any video file",
  "author": "Enzo10091",
  "score": 8,
  "num_comments": 1,
  "comment_count_scraped": 1,
  "comments": [
    {
      "id": "lwg8h3x",
      "author": "ismail_the_whale",
      "body": "nice, but you really have to clean this up. i guess you're not a python dev.\n\n- use snake_case\n- use a pyproject.toml file",
      "score": 2,
      "created_utc": 1755262448.0,
      "parent_id": "t3_1mqw7zr",
      "replies": []
    }
  ]
}
```


#### Advanced Requests Scraper (Best for Bulk)
```bash
python3 -m reddit_scraper.cli requests paginated SUBREDDIT_NAME [options]
```

### Utility Commands

#### System Health & Status
```bash
python3 -m reddit_scraper.cli status --config config.json

python3 -m reddit_scraper.cli test-proxies --config config.json --test-urls 3
```

#### Setup and Configuration
```bash
cp config.example.json config.json
nano config.json

python3 -m reddit_scraper.cli status --config config.json
```

### Global Search
```bash
python3 -m reddit_scraper.cli search "python tips" --subreddit python

python3 -m reddit_scraper.cli search "neural networks" --subreddit MachineLearning
```

### **Current Reddit Restrictions**

Reddit has some protection against automated scraping:
- **Some subreddits** may trigger captcha challenges (r/webscraping, etc.)
- **Large bulk requests** may hit rate limits
- **Search endpoints** work but may be slower than direct scraping

**Recommended approach:**
- Use **interactive mode** for best success rate
- Start with **popular, stable subreddits** like `python`, `technology`
- Use **proxies and captcha solving** for reliable large-scale scraping
- **Search functionality** works well for targeted queries

### **Working Examples (Tested)**

```bash
python3 -m reddit_scraper.cli interactive --config config.json

python3 -m reddit_scraper.cli json subreddit python --limit 10
python3 -m reddit_scraper.cli json subreddit technology --config config.json --limit 50

python3 -m reddit_scraper.cli search "python tips" --subreddit python

python3 -m reddit_scraper.cli requests paginated python --max-posts 100

python3 -m reddit_scraper.cli status --config config.json
python3 -m reddit_scraper.cli test-proxies --config config.json
```

**Subreddits that work well:**
- `python`, `programming`, `technology`
- `news`, `todayilearned` 
- `entrepreneur`, `startups`

## Command Options

### Common Options
- `--config`, `-c` - Path to configuration file
- `--output`, `-o` - Output file path
- `--format` - Output format (json, csv)
- `--limit` - Number of items to fetch
- `--sort` - Sort method (hot, new, top, rising, etc.)
- `--delay` - Delay between requests (seconds)

## Python API

### Basic Usage
```python
from reddit_scraper import JSONScraper, get_config_manager

scraper = JSONScraper()
posts = scraper.scrape_subreddit("python", "hot", 50)

config_manager = get_config_manager("config.json")
proxy_manager, captcha_solver = setup_advanced_features(config_manager)

advanced_scraper = JSONScraper(
    proxy_manager=proxy_manager,
    captcha_solver=captcha_solver,
    delay=config_manager.get_scraping_config().default_delay
)

posts = advanced_scraper.scrape_subreddit("MachineLearning", "top", 1000)
```

### Proxy Management
```python
from reddit_scraper import ProxyManager

proxy_manager = ProxyManager()
proxy_manager.add_proxy("proxy.example.com", 8080, "user", "pass", "http")

proxy_manager.health_check_all()
stats = proxy_manager.get_proxy_stats()
print(f"Healthy proxies: {stats['healthy_proxies']}/{stats['total_proxies']}")
```

### Captcha Solving
```python
from reddit_scraper import CaptchaSolverManager

solver = CaptchaSolverManager("YOUR_CAPSOLVER_API_KEY")

solution = solver.check_balance_and_solve(
    solver.solver.solve_recaptcha_v2,
    "https://reddit.com",
    "site_key_here"
)

if solution.success:
    print(f"Captcha solved: {solution.solution}")
```

## Best Practices

### Ethical Scraping
- Always respect Reddit's Terms of Service
- Don't overload Reddit's servers
- Consider using the official API for commercial use

### Rate Limiting
- Default: 1 second delay between requests
- Use appropriate delays between requests
- Increase delay for large-scale operations
- Monitor proxy health to avoid IP bans

### Data Usage
- Store scraped data responsibly
- Respect user privacy
- Don't republish personal information

## Troubleshooting

### Common Issues

#### "No healthy proxies available"
```bash
reddit-scraper test-proxies

reddit-scraper status
```

#### "Captcha solver balance error"
```bash
reddit-scraper status
```

#### Rate limiting errors
- Increase `--delay` parameter
- Use configuration file with multiple proxies
- Reduce `--limit` per request

## API Documentation

### Capsolver Integration
This project integrates with capsolver for automated captcha solving, supporting:
- reCAPTCHA v2/v3
- hCaptcha
- FunCaptcha
- Image-to-text captchas

### Reddit API Compatibility
Compatible with Reddit's public JSON endpoints for FREE data access.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is for educational and research purposes. Please respect Reddit's Terms of Service and robots.txt.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Note**: This tool is designed for ethical data collection and research purposes. Always comply with Reddit's Terms of Service and respect rate limits.