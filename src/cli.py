"""Command-line interface for Rocket League Coach."""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional
import logging

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
# Use standard logging instead of custom logging_config to avoid import issues
logger = logging.getLogger(__name__)

# Initialize rich console
console = Console()


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config-file', type=click.Path(), help='Path to configuration file')
def cli(debug: bool, config_file: Optional[str]):
    """Rocket League Coach - Automated coaching system with win/loss correlation analysis."""
    # Setup basic logging
    if debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if config_file:
        console.print(f"[yellow]Using config file: {config_file}[/yellow]")
    
    console.print("[bold blue]🚀 Rocket League Coach CLI[/bold blue]")


@cli.command()
@click.argument('gamertag')
@click.option('--games', '-g', default=10, help='Number of games to analyze (1-50)')
@click.option('--force-refresh', '-f', is_flag=True, help='Force refresh of cached data')
@click.option('--raw-data', is_flag=True, help='Include raw analysis data in output')
@click.option('--output', '-o', type=click.Path(), help='Save results to file (JSON format)')
def analyze(gamertag: str, games: int, force_refresh: bool, raw_data: bool, output: Optional[str]):
    """Analyze a player's performance and generate coaching insights."""
    
    if games < 1 or games > 50:
        console.print("[red]Error: Number of games must be between 1 and 50[/red]")
        return
    
    console.print(f"[bold]Analyzing player: [cyan]{gamertag}[/cyan][/bold]")
    console.print(f"Games to analyze: {games}")
    console.print(f"Force refresh: {'Yes' if force_refresh else 'No'}")
    
    try:
        from services.analysis_service import get_analysis_service
        from data.models import AnalysisRequest
        
        # Create analysis request
        request = AnalysisRequest(
            gamertag=gamertag,
            num_games=games,
            force_refresh=force_refresh,
            include_raw_data=raw_data
        )
        
        # Run analysis with progress tracking
        result = asyncio.run(_run_analysis_with_progress(request))
        
        if result:
            _display_analysis_result(result)
            
            if output:
                _save_result_to_file(result, output)
    except ImportError as e:
        console.print(f"[red]Error: Required modules not available. {str(e)}[/red]")
        console.print("[yellow]Note: Full analysis features may not be implemented yet.[/yellow]")
    except Exception as e:
        console.print(f"[red]Analysis failed: {str(e)}[/red]")


@cli.command()
@click.argument('gamertag')
@click.option('--limit', '-l', default=20, help='Limit number of games to show')
def history(gamertag: str, limit: int):
    """Show player's game history from cache."""
    
    console.print(f"[bold]Game history for: [cyan]{gamertag}[/cyan][/bold]")
    
    try:
        from data.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        history_data = cache_manager.get_player_game_history(gamertag, limit=limit)
        
        if not history_data:
            console.print(f"[yellow]No game history found for {gamertag}[/yellow]")
            return
        
        # Create table
        table = Table(title=f"{gamertag}'s Recent Games")
        table.add_column("Date", style="cyan")
        table.add_column("Result", style="bold")
        table.add_column("Rank Tier", style="magenta")
        table.add_column("Replay ID", style="dim")
        
        for game in history_data:
            result_style = "green" if game['game_result'] == 'win' else "red"
            result_text = f"[{result_style}]{game['game_result'].upper()}[/{result_style}]"
            
            rank_tier = str(game.get('rank_tier', 'Unknown'))
            game_date = game['game_date'][:10] if game['game_date'] else 'Unknown'
            
            table.add_row(
                game_date,
                result_text,
                rank_tier,
                game['replay_id'][:8] + "..."
            )
        
        console.print(table)
    except ImportError as e:
        console.print(f"[red]Error: Cache manager not available. {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]Failed to retrieve history: {str(e)}[/red]")


@cli.command()
def cache_stats():
    """Show cache statistics and health information."""
    
    console.print("[bold]Cache Statistics[/bold]")
    
    try:
        from data.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        stats = cache_manager.get_cache_stats()
        
        # Create stats table
        table = Table(title="Cache Health")
        table.add_column("Component", style="cyan")
        table.add_column("Entries", justify="right", style="yellow")
        table.add_column("Size", justify="right", style="green")
        
        # Replay cache
        replay_stats = stats['replay_cache']
        replay_size = _format_file_size(replay_stats['directory_size'])
        table.add_row("Replay Cache", str(replay_stats['entries']), replay_size)
        
        # Analysis cache
        analysis_stats = stats['analysis_cache']
        analysis_size = _format_file_size(analysis_stats['directory_size'])
        table.add_row("Analysis Cache", str(analysis_stats['entries']), analysis_size)
        
        # Player history
        player_stats = stats['player_history']
        table.add_row("Player History", str(player_stats['unique_players']), "N/A")
        
        # Total
        total_size = _format_file_size(stats['total_cache_size'])
        table.add_row("[bold]Total", "", f"[bold]{total_size}")
        
        console.print(table)
    except ImportError as e:
        console.print(f"[red]Error: Cache system not available. {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]Failed to retrieve cache stats: {str(e)}[/red]")


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to clear the entire cache?')
def cache_clear():
    """Clear all cached data. WARNING: This will delete all cached replays and analysis results."""
    
    try:
        from data.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        
        with console.status("[bold yellow]Clearing cache..."):
            cache_manager.clear_cache(confirm=True)
        
        console.print("[bold green]✅ Cache cleared successfully[/bold green]")
    except Exception as e:
        console.print(f"[red]Failed to clear cache: {str(e)}[/red]")


@cli.command()
def cache_cleanup():
    """Clean up expired cache entries."""
    
    console.print("[bold]Cleaning up expired cache entries...[/bold]")
    
    try:
        from data.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        
        with console.status("[bold yellow]Running cleanup..."):
            stats = cache_manager.cleanup_expired_cache()
        
        console.print(f"[green]✅ Cleanup completed![/green]")
        console.print(f"Removed {stats['replays_removed']} expired replays")
        console.print(f"Removed {stats['analysis_removed']} expired analysis results")
        console.print(f"Removed {stats['files_removed']} files total")
    except Exception as e:
        console.print(f"[red]Cleanup failed: {str(e)}[/red]")


@cli.command()
def health():
    """Check application health and component status."""
    
    console.print("[bold]System Health Check[/bold]\n")
    
    settings = get_settings()
    
    # Check configuration
    config_status = "✅ OK" if settings.ballchasing_api_token else "❌ Missing API token"
    console.print(f"Configuration: {config_status}")
    
    if settings.ballchasing_api_token:
        token_preview = settings.ballchasing_api_token[:10] + "..." if len(settings.ballchasing_api_token) > 10 else "SET"
        console.print(f"  API Token: {token_preview}")
    
    # Check cache system
    try:
        from data.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        cache_stats = cache_manager.get_cache_stats()
        cache_status = "✅ OK"
    except ImportError:
        cache_status = "⚠️  Module not implemented"
    except Exception as e:
        cache_status = f"❌ Error: {str(e)}"
    
    console.print(f"Cache System: {cache_status}")
    
    # Check analysis service
    try:
        from services.analysis_service import get_analysis_service
        analysis_service = get_analysis_service()
        analysis_status = "✅ OK"
    except ImportError:
        analysis_status = "⚠️  Module not implemented"
    except Exception as e:
        analysis_status = f"❌ Error: {str(e)}"
    
    console.print(f"Analysis Service: {analysis_status}")
    
    # Show directory status
    console.print(f"\n[bold]Directory Status:[/bold]")
    console.print(f"Replays: {settings.replays_dir}")
    console.print(f"Cache: {settings.analysis_cache_dir}")
    console.print(f"Player Data: {settings.player_data_dir}")
    console.print(f"Logs: {settings.logs_dir}")
    
    # Test API endpoint
    console.print(f"\n[bold]API Status:[/bold]")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            console.print(f"Health Endpoint: ✅ OK (Status {response.status_code})")
            data = response.json()
            console.print(f"  Service: {data.get('service', 'Unknown')}")
            console.print(f"  Version: {data.get('version', 'Unknown')}")
        else:
            console.print(f"Health Endpoint: ⚠️  Status {response.status_code}")
    except Exception as e:
        console.print(f"Health Endpoint: ❌ Cannot connect to API")
    
    console.print(f"\n[bold]Environment:[/bold]")
    console.print(f"Environment: {settings.environment}")
    console.print(f"Debug Mode: {settings.debug}")
    console.print(f"Host: {settings.host}:{settings.port}")


async def _run_analysis_with_progress(request):
    """Run analysis with progress tracking."""
    
    try:
        from services.analysis_service import get_analysis_service
        from data.models import AnalysisStatus
        
        analysis_service = get_analysis_service()
        
        # Progress tracking variables
        current_status = None
        
        def progress_callback(status: AnalysisStatus):
            nonlocal current_status
            current_status = status
        
        # Start analysis in background
        analysis_task = asyncio.create_task(
            analysis_service.analyze_player(request, progress_callback)
        )
        
        # Show progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            task = progress.add_task("Starting analysis...", total=100)
            
            while not analysis_task.done():
                if current_status:
                    progress.update(
                        task,
                        completed=current_status.progress,
                        description=current_status.current_step
                    )
                
                await asyncio.sleep(0.1)
            
            # Complete the progress bar
            progress.update(task, completed=100, description="Analysis complete")
        
        result = await analysis_task
        return result
    except ImportError as e:
        console.print(f"[yellow]Analysis service not fully implemented: {str(e)}[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]Analysis failed: {str(e)}[/red]")
        return None


def _display_analysis_result(result):
    """Display analysis results in a formatted way."""
    
    # Header
    header = Panel(
        f"[bold cyan]{result.gamertag}[/bold cyan] Analysis Results\n"
        f"Games Analyzed: {result.total_games} | "
        f"Win Rate: {result.win_rate:.1f}% | "
        f"Confidence: {result.confidence_score:.1%}",
        title="🎯 Player Analysis",
        border_style="blue"
    )
    console.print(header)
    
    # Data quality warning
    if not result.has_sufficient_data:
        console.print(Panel(
            "[yellow]⚠️  Limited data available. Analysis may be less reliable.\n"
            "For best results, ensure the player has at least 5 wins and 5 losses.[/yellow]",
            title="Data Quality Warning",
            border_style="yellow"
        ))
    
    # Top Priority Insights
    if result.top_priority_insights:
        console.print("\n[bold]🔥 Top Priority Improvements:[/bold]")
        for i, insight in enumerate(result.top_priority_insights[:3], 1):
            priority_color = "red" if insight.priority <= 2 else "yellow" if insight.priority <= 3 else "blue"
            console.print(f"  {i}. [{priority_color}]{insight.title}[/{priority_color}]")
            console.print(f"     {insight.message}")
            if insight.specific_actions:
                console.print(f"     💡 Actions: {', '.join(insight.specific_actions[:2])}")
            console.print()
    
    # Key Strengths
    if result.key_strengths:
        console.print("[bold green]💪 Key Strengths:[/bold green]")
        for strength in result.key_strengths:
            console.print(f"  ✅ {strength}")
        console.print()
    
    # Improvement Areas
    if result.improvement_areas:
        console.print("[bold yellow]📈 Primary Improvement Areas:[/bold yellow]")
        for area in result.improvement_areas:
            console.print(f"  🎯 {area}")
        console.print()


def _save_result_to_file(result, output_path: str):
    """Save analysis result to JSON file."""
    
    import json
    from datetime import datetime
    
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert result to dict and save
        result_data = result.dict()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, default=str)
        
        console.print(f"[green]✅ Results saved to: {output_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to save results: {str(e)}[/red]")


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


@cli.command()
@click.argument('gamertag')
def quick(gamertag: str):
    """Quick analysis with default settings (10 games, cached results)."""
    
    console.print(f"[bold]Quick analysis for: [cyan]{gamertag}[/cyan][/bold]")
    
    try:
        from services.analysis_service import get_analysis_service
        from data.models import AnalysisRequest
        
        request = AnalysisRequest(
            gamertag=gamertag,
            num_games=10,
            force_refresh=False,
            include_raw_data=False
        )
        
        result = asyncio.run(_run_analysis_with_progress(request))
        
        if result:
            # Show condensed results
            console.print(f"\n[bold]📊 Quick Summary for {gamertag}[/bold]")
            console.print(f"Win Rate: {result.win_rate:.1f}% ({result.wins}W-{result.losses}L)")
            console.print(f"Confidence: {result.confidence_score:.1%}")
            
            if result.top_priority_insights:
                console.print(f"\n[bold]🎯 Top Recommendation:[/bold]")
                top_insight = result.top_priority_insights[0]
                console.print(f"   {top_insight.title}")
                console.print(f"   {top_insight.message}")
    except ImportError as e:
        console.print(f"[yellow]Quick analysis not available - required modules not implemented: {str(e)}[/yellow]")
        console.print("[blue]Tip: The health command can show you what components are available.[/blue]")
    except Exception as e:
        console.print(f"[red]Quick analysis failed: {str(e)}[/red]")


if __name__ == '__main__':
    cli()
