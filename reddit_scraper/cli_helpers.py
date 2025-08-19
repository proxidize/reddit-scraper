import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .json_scraper import JSONScraper
from .requests_scraper import RequestsScraper
from .config import ConfigManager
from .validation import validate_subreddit_name, validate_limit, ValidationError

logger = logging.getLogger(__name__)
console = Console()


def create_scraper_with_config(config_manager: Optional[ConfigManager] = None) -> Tuple[JSONScraper, Optional[ConfigManager]]:

    from .cli import setup_advanced_features  
    
    if config_manager:
        proxy_manager, captcha_solver = setup_advanced_features(config_manager)
        scraper_config = config_manager.get_scraping_config()
        
        scraper = JSONScraper(
            delay=scraper_config.default_delay,
            proxy_manager=proxy_manager,
            captcha_solver=captcha_solver,
            rotate_user_agents=scraper_config.rotate_user_agents
        )
    else:
        scraper = JSONScraper()
    
    return scraper, config_manager


async def scrape_posts_with_progress(scraper: JSONScraper, subreddit: str, 
                                    sort: str, limit: int) -> List[Dict[str, Any]]:

    try:
        subreddit = validate_subreddit_name(subreddit)
        limit = validate_limit(limit)
    except ValidationError as e:
        console.print(f"[red]Validation error: {e}[/red]")
        return []
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Scraping r/{subreddit}...", total=None)
        posts = await scraper.scrape_subreddit(subreddit, sort, limit)
        progress.update(task, completed=100)
    
    return posts


async def add_comments_to_posts(scraper: JSONScraper, posts: List[Dict[str, Any]], 
                               subreddit: str, comment_sort: str, 
                               comment_limit: Optional[int] = None) -> None:

    if not posts:
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        comment_task = progress.add_task("Adding comments...", total=len(posts))
        
        for i, post in enumerate(posts):
            try:
                if i > 0:
                    await asyncio.sleep(1) 
                
                post_id = post.get('id')
                if post_id:
                    comment_data = await scraper.scrape_post_comments(subreddit, post_id, comment_sort)
                    if comment_data and 'comments' in comment_data:
                        comments = comment_data['comments']
                        if comment_limit:
                            comments = comments[:comment_limit]
                        post['comments'] = comments
                        post['comment_count_scraped'] = len(comments)
                    else:
                        post['comments'] = []
                        post['comment_count_scraped'] = 0
                else:
                    post['comments'] = []
                    post['comment_count_scraped'] = 0
                
                progress.update(comment_task, advance=1)
                
            except Exception as e:
                logger.warning(f"Failed to get comments for post {post.get('id', 'unknown')}: {e}")
                post['comments'] = []
                post['comment_count_scraped'] = 0
                progress.update(comment_task, advance=1)


def create_posts_table(posts: List[Dict[str, Any]], subreddit: str, 
                      include_comments: bool = False) -> Table:

    table_title = f"r/{subreddit} Posts"
    if include_comments:
        table_title += " with Comments"
    
    table = Table(title=table_title)
    table.add_column("Title", style="cyan", no_wrap=False, max_width=50)
    table.add_column("Author", style="magenta")
    table.add_column("Score", style="green")
    table.add_column("Comments", style="yellow")
    
    if include_comments:
        table.add_column("Scraped Comments", style="blue")
    
    for post in posts[:5]:
        title = post.get('title', 'N/A')
        if len(title) > 50:
            title = title[:47] + "..."
        
        row = [
            title,
            post.get('author', 'N/A'),
            str(post.get('score', 0)),
            str(post.get('num_comments', 0))
        ]
        
        if include_comments:
            row.append(str(post.get('comment_count_scraped', 0)))
        
        table.add_row(*row)
    
    return table


def display_scraping_results(posts: List[Dict[str, Any]], subreddit: str, 
                           include_comments: bool = False, 
                           output_file: Optional[str] = None) -> None:

    if not posts:
        console.print("[red]No posts found![/red]")
        return
    
    console.print(f"[green]Successfully scraped {len(posts)} posts[/green]")
    
    if include_comments:
        total_comments = sum(post.get('comment_count_scraped', 0) for post in posts)
        console.print(f"[blue]Total comments collected: {total_comments}[/blue]")
    
    if output_file:
        console.print(f"[green]Data saved to {output_file}[/green]")
    
    table = create_posts_table(posts, subreddit, include_comments)
    console.print(table)


async def handle_large_scraping_job(subject: str, post_count: int, sort_method: str, 
                                   scraper_config, proxy_manager, captcha_solver,
                                   use_proxies: bool, use_captcha: bool) -> List[Dict[str, Any]]:

    if use_proxies:
        scraper = JSONScraper(
            delay=scraper_config.default_delay,
            proxy_manager=proxy_manager,
            captcha_solver=captcha_solver if use_captcha else None,
            user_agent=scraper_config.user_agent
        )
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task(f"Scraping r/{subject} with proxies (large job)...", total=None)
            posts = await scraper.scrape_subreddit(subject, sort_method, post_count)
            progress.update(task, completed=100)
    else:
        scraper = RequestsScraper(
            delay=scraper_config.default_delay,
            user_agent=scraper_config.user_agent
        )
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task(f"Scraping r/{subject} with pagination...", total=None)
            posts = list(scraper.scrape_subreddit_paginated(subject, sort_method, post_count))
            progress.update(task, completed=100)
    
    return posts


def handle_regular_scraping_job(subject: str, post_count: int, sort_method: str,
                               scraper_config, proxy_manager, captcha_solver,
                               use_proxies: bool, use_captcha: bool) -> List[Dict[str, Any]]:
    scraper = RequestsScraper(
        delay=scraper_config.default_delay,
        user_agent=scraper_config.user_agent
    )
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Scraping r/{subject} (direct requests)...", total=None)
        posts = list(scraper.scrape_subreddit_paginated(subject, sort_method, post_count))
        progress.update(task, completed=100)
    
    return posts


def create_interactive_preview_table(posts: List[Dict[str, Any]], subject: str) -> Table:

    table = Table(title=f"r/{subject} Posts")
    table.add_column("Title", style="cyan", no_wrap=False, max_width=50)
    table.add_column("Author", style="magenta")
    table.add_column("Score", style="green")
    table.add_column("Comments", style="yellow")
    
    for post in posts[:5]:
        title = post.get('title', 'N/A')
        if len(title) > 50:
            title = title[:47] + "..."
        
        table.add_row(
            title,
            post.get('author', 'N/A'),
            str(post.get('score', 0)),
            str(post.get('num_comments', 0))
        )
    
    return table


def validate_and_display_config_status(config_manager: ConfigManager) -> bool:

    status = config_manager.validate_config()
    
    console.print("Configuration status:")
    console.print(f"  Proxies: {status['proxy_count']}")
    console.print(f"  Captcha solvers: {status['captcha_solver_count']}")
    
    if status['warnings']:
        for warning in status['warnings']:
            console.print(f"[yellow]Warning: {warning}[/yellow]")
    
    if status['errors']:
        for error in status['errors']:
            console.print(f"[red]Error: {error}[/red]")
        return False
    
    return True


def gather_interactive_input(config_manager: ConfigManager) -> Dict[str, Any]:

    import click
    
    subject = click.prompt("Enter subreddit name (without r/)", type=str)
    post_count = click.prompt("How many posts do you want to scrape?", type=int, default=50)
    sort_method = click.prompt("Sort method", 
                              type=click.Choice(['hot', 'new', 'top', 'rising']), 
                              default='hot')
    
    use_proxies = post_count > 100 and config_manager.has_proxies()
    use_captcha = False
    
    if config_manager.has_captcha_solvers():
        use_captcha = click.confirm("Use captcha solving?", default=True)
    
    if config_manager.has_proxies():
        proxy_msg = "Yes (automatic for >100 posts)" if use_proxies else "No (automatic for ≤100 posts)"
        click.echo(f"Proxy usage: {proxy_msg}")
    
    output_file = click.prompt("Output filename (optional)", default="", show_default=False)
    if not output_file:
        output_file = f"{subject}_posts.json"
    
    return {
        'subject': subject,
        'post_count': post_count,
        'sort_method': sort_method,
        'use_proxies': use_proxies,
        'use_captcha': use_captcha,
        'output_file': output_file
    }


def display_scraping_plan(inputs: Dict[str, Any]) -> None:

    console.print(f"\n[bold]Starting scrape:[/bold]")
    console.print(f"  Subreddit: r/{inputs['subject']}")
    console.print(f"  Posts: {inputs['post_count']}")
    console.print(f"  Sort: {inputs['sort_method']}")
    if inputs['post_count'] > 100:
        console.print(f"  Method: JSONScraper with proxies (large job)")
    else:
        console.print(f"  Method: RequestsScraper direct (small job)")
    console.print(f"  Proxies: {'Yes' if inputs['use_proxies'] else 'No'}")
    console.print(f"  Captcha: {'Yes' if inputs['use_captcha'] else 'No'}")
    console.print(f"  Output: {inputs['output_file']}\n")


async def execute_scraping_job(inputs: Dict[str, Any], config_manager: ConfigManager) -> List[Dict[str, Any]]:
    from .cli import setup_advanced_features 
    
    proxy_manager, captcha_solver = setup_advanced_features(config_manager)
    scraper_config = config_manager.get_scraping_config()
    
    use_proxies = inputs['post_count'] > 100 and config_manager.has_proxies()
    use_captcha = inputs['use_captcha']
    
    if inputs['post_count'] > 100:
        return await handle_large_scraping_job(
            inputs['subject'], inputs['post_count'], inputs['sort_method'],
            scraper_config, proxy_manager, captcha_solver,
            use_proxies, use_captcha
        )
    else:
        return handle_regular_scraping_job(
            inputs['subject'], inputs['post_count'], inputs['sort_method'],
            scraper_config, proxy_manager, captcha_solver,
            use_proxies, use_captcha
        )