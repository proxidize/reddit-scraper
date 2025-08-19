import click
import json
import logging
import os
import sys
import time
from typing import Optional
from datetime import datetime
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from dotenv import load_dotenv

from .json_scraper import JSONScraper
from .requests_scraper import RequestsScraper
from .proxy_manager import ProxyManager
from .captcha_solver import CaptchaSolverManager
from .config import get_config_manager, ConfigManager

console = Console()
logger = logging.getLogger(__name__)

load_dotenv()


def setup_advanced_features(config_manager: ConfigManager) -> tuple:
    proxy_manager = None
    captcha_solver = None
    
    if config_manager.has_proxies():
        try:
            proxy_manager = ProxyManager()
            for proxy_config in config_manager.get_proxies():
                proxy_manager.add_proxy(
                    proxy_config.host,
                    proxy_config.port,
                    proxy_config.username,
                    proxy_config.password,
                    proxy_config.proxy_type
                )
            proxy_manager.health_check_all()
            console.print("[green]Proxy manager initialized successfully[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to initialize proxy manager: {e}[/yellow]")
    
    if config_manager.has_captcha_solvers():
        try:
            captcha_configs = config_manager.get_captcha_solvers()
            if captcha_configs:
                config = captcha_configs[0]
                captcha_solver = CaptchaSolverManager(
                    api_key=config.api_key,
                    site_keys=config.site_keys or {}
                )
                balance = captcha_solver.solver.get_balance()
                if balance is not None:
                    console.print(f"[green]Captcha solver initialized (Balance: ${balance})[/green]")
                else:
                    console.print("[yellow]Warning: Could not verify captcha solver balance[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to initialize captcha solver: {e}[/yellow]")
    
    return proxy_manager, captcha_solver


def save_data(data, output_file: str, format: str = "json"):
    if format == "json":
        with open(output_file, 'w') as f:
            import json as json_module
            json_module.dump(data, f, indent=2, default=str)
    elif format == "csv":
        if isinstance(data, list) and data:
            df = pd.json_normalize(data)
            df.to_csv(output_file, index=False)
        else:
            console.print("[red]Cannot save empty data or non-list data to CSV[/red]")
            return
    console.print(f"[green]Data saved to {output_file}[/green]")


@click.group()
@click.version_option()
def main():
    console.print("[bold blue]Reddit Scraper v0.1.0[/bold blue]")
    console.print("Choose from multiple scraping methods:\n")
    console.print("• [bold]json[/bold] - Fast scraping using Reddit's .json endpoints")
    console.print("• [bold]requests[/bold] - Advanced scraping with pagination\n")
    console.print("[bold cyan]Advanced Features:[/bold cyan]")
    console.print("• [green]Proxy rotation[/green] - Automatic proxy switching for scale")
    console.print("• [green]Captcha solving[/green] - Automated captcha handling")
    console.print("• [green]User agent rotation[/green] - Realistic browser simulation\n")


@main.group()
def json():
    pass



@main.group()
def requests():
    pass


@json.command()
@click.argument('subreddit')
@click.option('--sort', default='hot', help='Sort method (hot, new, top, rising)')
@click.option('--limit', default=25, help='Number of posts to fetch')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', default='json', type=click.Choice(['json', 'csv']), help='Output format')
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--delay', default=1.0, help='Delay between requests (seconds)')
def subreddit(subreddit, sort, limit, output, format, config, delay):
    import asyncio
    
    async def _async_subreddit():
        config_manager = get_config_manager(config)
        proxy_manager, captcha_solver = setup_advanced_features(config_manager)
        
        scraper = JSONScraper(
            delay=delay,
            proxy_manager=proxy_manager,
            captcha_solver=captcha_solver,
            rotate_user_agents=config_manager.get_scraping_config().rotate_user_agents
        )
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task(f"Scraping r/{subreddit}...", total=None)
            posts = await scraper.scrape_subreddit(subreddit, sort, limit)
            progress.update(task, completed=100)
        
        if not posts:
            console.print("[red]No posts found![/red]")
            return
            
        console.print(f"[green]Found {len(posts)} posts from r/{subreddit}[/green]")
        
        table = Table(title=f"r/{subreddit} Posts Preview")
        table.add_column("Title", style="cyan", no_wrap=False, max_width=50)
        table.add_column("Author", style="magenta")
        table.add_column("Score", style="green")
        table.add_column("Comments", style="yellow")
        
        for post in posts[:5]:  
            table.add_row(
                post.get('title', 'N/A')[:50] + "..." if len(post.get('title', '')) > 50 else post.get('title', 'N/A'),
                post.get('author', 'N/A'),
                str(post.get('score', 0)),
                str(post.get('num_comments', 0))
            )
        
        console.print(table)
        
        if output:
            save_data(posts, output, format)
    
    asyncio.run(_async_subreddit())


@json.command()
@click.argument('username')
@click.option('--sort', default='new', help='Sort method (new, hot, top)')
@click.option('--limit', default=25, help='Number of posts to fetch')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', default='json', type=click.Choice(['json', 'csv']), help='Output format')
def user(username, sort, limit, output, format):
    import asyncio
    
    async def _async_user():
        scraper = JSONScraper()
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task(f"Scraping u/{username}...", total=None)
            posts = await scraper.scrape_user_posts(username, sort, limit)
            progress.update(task, completed=100)
        
        console.print(f"[green]Found {len(posts)} posts from u/{username}[/green]")
        
        if output:
            save_data(posts, output, format)
    
    asyncio.run(_async_user())


@json.command()
@click.argument('subreddit')
@click.argument('post_id')
@click.option('--sort', default='best', help='Comment sort method')
@click.option('--output', '-o', help='Output file path')
def comments(subreddit, post_id, sort, output):
    import asyncio
    
    async def _async_comments():
        scraper = JSONScraper()
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Scraping comments...", total=None)
            data = await scraper.scrape_post_comments(subreddit, post_id, sort)
            progress.update(task, completed=100)
        
        if data:
            console.print(f"[green]Found {len(data.get('comments', []))} comments[/green]")
            if output:
                save_data(data, output)
        else:
            console.print("[red]No comments found![/red]")
    
    asyncio.run(_async_comments())


@json.command()
@click.argument('subreddit')
@click.option('--limit', default=25, help='Number of posts to scrape')
@click.option('--sort', default='hot', help='Sort method (hot, new, top, rising)')
@click.option('--include-comments', is_flag=True, help='Include comments for each post')
@click.option('--comment-limit', default=50, help='Max comments per post')
@click.option('--comment-sort', default='best', help='Comment sort method')
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--output', '-o', help='Output file path')
def subreddit_with_comments(subreddit, limit, sort, include_comments, comment_limit, comment_sort, config, output):
    import asyncio
    from .cli_helpers import create_scraper_with_config, scrape_posts_with_progress, add_comments_to_posts, display_scraping_results
    
    async def _async_scrape():
        config_manager = get_config_manager(config) if config else None
        scraper, _ = create_scraper_with_config(config_manager)
        
        posts = await scrape_posts_with_progress(scraper, subreddit, sort, limit)
        
        if include_comments and posts:
            await add_comments_to_posts(scraper, posts, subreddit, comment_sort, comment_limit)
        
        if posts and output:
            save_data(posts, output)
        
        display_scraping_results(posts, subreddit, include_comments, output)
    
    asyncio.run(_async_scrape())


@requests.command()
@click.argument('subreddit')
@click.option('--sort', default='hot', help='Sort method')
@click.option('--max-posts', default=1000, help='Maximum posts to fetch')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', default='json', type=click.Choice(['json', 'csv']), help='Output format')
def paginated(subreddit, sort, max_posts, output, format):
    scraper = RequestsScraper()
    
    posts = []
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Scraping r/{subreddit} with pagination...", total=None)
        for post in scraper.scrape_subreddit_paginated(subreddit, sort, max_posts):
            posts.append(post)
        progress.update(task, completed=100)
    
    console.print(f"[green]Found {len(posts)} posts from r/{subreddit}[/green]")
    
    if output:
        save_data(posts, output, format)


@main.command()
@click.argument('query')
@click.option('--subreddit', help='Subreddit to search in (leave empty for all Reddit)')
@click.option('--method', default='json', type=click.Choice(['json', 'requests']), help='Scraping method')
@click.option('--limit', default=100, help='Number of results')
@click.option('--output', '-o', help='Output file path')
def search(query, subreddit, method, limit, output):
    import asyncio
    
    async def _async_search():
        if method == 'json':
            scraper = JSONScraper()
            if subreddit:
                results = await scraper.search_subreddit(subreddit, query, limit=limit)
            else:
                console.print("[red]JSON method requires a specific subreddit for search[/red]")
                return
        else:  
            scraper = RequestsScraper()
            results = list(scraper.search_advanced(query, subreddit, max_results=limit))
        
        console.print(f"[green]Found {len(results)} results for '{query}'[/green]")
        
        if output:
            save_data(results, output)
    
    asyncio.run(_async_search())


@main.command()
@click.option('--config', '-c', help='Path to configuration file')
def interactive(config):
    import asyncio
    from .cli_helpers import (
        validate_and_display_config_status, gather_interactive_input, 
        display_scraping_plan, execute_scraping_job, create_interactive_preview_table
    )
    
    async def _async_interactive():
        console.print("[bold]Reddit Scraper - Interactive Mode[/bold]\n")
        
        config_manager = get_config_manager(config)
        if not validate_and_display_config_status(config_manager):
            return
        
        console.print()
        
        inputs = gather_interactive_input(config_manager)
        
        display_scraping_plan(inputs)
        
        posts = await execute_scraping_job(inputs, config_manager)
        
        if posts:
            console.print(f"[green]Successfully scraped {len(posts)} posts![/green]")
            save_data(posts, inputs['output_file'])
            console.print(f"\n[bold]Preview of scraped data:[/bold]")
            table = create_interactive_preview_table(posts, inputs['subject'])
            console.print(table)
        else:
            console.print("[red]No posts were scraped. Check your configuration and try again.[/red]")
    
    asyncio.run(_async_interactive())



@main.command()
@click.option('--config', '-c', help='Path to configuration file')
def status(config):
    console.print("[bold]Checking Advanced Features Status...[/bold]\n")
    
    try:
        config_manager = get_config_manager(config)
        proxy_manager, _ = setup_advanced_features(config_manager)
        if not proxy_manager:
            console.print("[yellow]No proxies configured[/yellow]\\n")
            return
        stats = proxy_manager.get_proxy_stats()
        
        table = Table(title="Proxy Status")
        table.add_column("Host", style="cyan")
        table.add_column("Port", style="magenta")
        table.add_column("Type", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Success/Failures", style="blue")
        
        for proxy in stats['proxy_details']:
            status_text = "Healthy" if proxy['is_healthy'] else "Unhealthy"
            success_fail = f"{proxy['success_count']}/{proxy['failure_count']}"
            
            table.add_row(
                proxy['host'],
                str(proxy['port']),
                proxy['type'].upper(),
                status_text,
                success_fail
            )
        
        console.print(table)
        console.print(f"Overall Health Rate: {stats['health_rate']:.1f}%\n")
        
    except Exception as e:
        console.print(f"[red]Error checking proxy status: {e}[/red]\n")
    
    try:
        config_manager = get_config_manager(config)
        _, captcha_solver = setup_advanced_features(config_manager)
        if not captcha_solver:
            console.print("[yellow]No captcha solvers configured[/yellow]")
            return
        balance = captcha_solver.solver.get_balance()
        
        if balance is not None:
            console.print(f"[green]Captcha Solver Status: Active[/green]")
            console.print(f"[green]Balance: ${balance}[/green]")
            
            if balance < 1.0:
                console.print("[yellow]Warning: Low balance, consider topping up[/yellow]")
        else:
            console.print("[red]Captcha Solver Status: Error getting balance[/red]")
            
    except Exception as e:
        console.print(f"[red]Error checking captcha solver status: {e}[/red]")


@main.command()
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--test-urls', default=3, help='Number of test URLs to check')
def test_proxies(config, test_urls):
    console.print("[bold]Testing Proxy Performance...[/bold]\n")
    
    try:
        config_manager = get_config_manager(config)
        proxy_manager, _ = setup_advanced_features(config_manager)
        if not proxy_manager:
            console.print("[yellow]No proxies configured for testing[/yellow]")
            return
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Testing proxies...", total=None)
            proxy_manager.health_check_all()
            progress.update(task, completed=100)
        
        stats = proxy_manager.get_proxy_stats()
        console.print(f"[green]Proxy test complete![/green]")
        console.print(f"Healthy proxies: {stats['healthy_proxies']}/{stats['total_proxies']}")
        console.print(f"Health rate: {stats['health_rate']:.1f}%")
        
    except Exception as e:
        console.print(f"[red]Error testing proxies: {e}[/red]")


if __name__ == '__main__':
    main()