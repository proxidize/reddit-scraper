import pytest
import json
import tempfile
import os
import asyncio
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock

from reddit_scraper.cli import main


@pytest.mark.integration
class TestCLIBasic:
    
    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert "Commands:" in result.output
        assert "json" in result.output
        assert "requests" in result.output
    
    def test_json_command_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ['json', '--help'])
        
        assert result.exit_code == 0
        assert "Fast scraping using Reddit's .json endpoints" in result.output


@pytest.mark.integration 
class TestCLISubredditCommand:
    
    @patch('reddit_scraper.json_scraper.JSONScraper.scrape_subreddit', new_callable=AsyncMock)
    def test_subreddit_command_basic(self, mock_scrape):
        mock_scrape.return_value = []
        
        runner = CliRunner()
        result = runner.invoke(main, [
            'json', 'subreddit', 'test',
            '--limit', '5',
            '--delay', '0.1'
        ])
        
        assert result.exit_code == 0
        mock_scrape.assert_called_once()
    
    def test_subreddit_command_invalid_input(self):
        runner = CliRunner()
        result = runner.invoke(main, [
            'json', 'subreddit', 'invalid!',
            '--limit', '5'
        ])
        
        assert result.exit_code == 1  
    
    @patch('reddit_scraper.json_scraper.JSONScraper.scrape_subreddit', new_callable=AsyncMock)
    def test_subreddit_command_with_output(self, mock_scrape):
        mock_scrape.return_value = [
            {
                'title': 'Test Post',
                'author': 'test_user',
                'score': 10,
                'id': 'abc123'
            }
        ]
        
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            try:
                result = runner.invoke(main, [
                    'json', 'subreddit', 'test',
                    '--limit', '1',
                    '--output', tmp.name,
                    '--delay', '0.1'
                ])
                
                assert result.exit_code == 0
                
                with open(tmp.name, 'r') as f:
                    data = json.load(f)
                    assert len(data) == 1
                    assert data[0]['title'] == 'Test Post'
                    
            finally:
                os.unlink(tmp.name)


@pytest.mark.integration
class TestCLIUserCommand:
    
    @patch('reddit_scraper.json_scraper.JSONScraper.scrape_user_posts', new_callable=AsyncMock)
    def test_user_command(self, mock_scrape):
        mock_scrape.return_value = []
        
        runner = CliRunner()
        result = runner.invoke(main, [
            'json', 'user', 'test_user',
            '--limit', '5',
            '--delay', '0.1'
        ])
        
        assert result.exit_code == 0
        mock_scrape.assert_called_once()


@pytest.mark.integration 
class TestCLICommentsCommand:
    
    @patch('reddit_scraper.json_scraper.JSONScraper.scrape_post_comments', new_callable=AsyncMock)
    def test_comments_command(self, mock_scrape):

        mock_scrape.return_value = {'comments': []}
        
        runner = CliRunner()
        result = runner.invoke(main, [
            'json', 'comments', 'test', 'abc123',
            '--sort', 'best',
            '--delay', '0.1'
        ])
        
        assert result.exit_code == 0


@pytest.mark.integration
class TestCLIInteractiveMode:
    
    @patch('reddit_scraper.cli_helpers.execute_scraping_job', new_callable=AsyncMock)
    @patch('reddit_scraper.cli_helpers.gather_interactive_input')
    def test_interactive_mode(self, mock_input, mock_execute):
        
        mock_input.return_value = {
            'subject': 'test',
            'post_count': 5,
            'sort_method': 'hot',
            'use_proxies': False,
            'use_captcha': False,
            'output_file': None  
        }
        
        mock_execute.return_value = []
        
        runner = CliRunner()
        result = runner.invoke(main, ['interactive'])
        
        assert result.exit_code == 0
        mock_input.assert_called_once()
        mock_execute.assert_called_once()


@pytest.mark.integration
class TestCLIConfiguration:
    
    def test_config_file_loading(self):
        config_data = {
            "scraping": {
                "default_delay": 2.0,
                "max_retries": 5,
                "user_agent": "TestAgent/1.0"
            }
        }
        
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            try:
                json.dump(config_data, tmp)
                tmp.flush()
                
                result = runner.invoke(main, [
                    'json', 'subreddit', 'test',
                    '--config', tmp.name,
                    '--limit', '1'
                ])
                
                assert result.exit_code == 0
                
            finally:
                os.unlink(tmp.name)
    
    def test_invalid_config_file(self):
        runner = CliRunner()
        result = runner.invoke(main, [
            'json', 'subreddit', 'test',
            '--config', 'nonexistent.json',
            '--limit', '1'
        ])
        
        assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.slow
class TestCLIRealRequests:
    
    def test_real_subreddit_scraping(self):
        runner = CliRunner()
        result = runner.invoke(main, [
            'json', 'subreddit', 'test',
            '--limit', '1',
            '--delay', '2.0'
        ])
        
        assert result.exit_code == 0