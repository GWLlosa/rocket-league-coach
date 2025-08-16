"""Command-line interface for Rocket League Coach."""

import asyncio
import click
from typing import Optional

from .config import get_settings
from .logging_config import get_logger


logger = get_logger(__name__)


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
@click.pass_context
def cli(ctx, debug):
    """Rocket League Coach CLI - Automated coaching with win/loss correlation analysis."""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    
    if debug:
        click.echo("🐛 Debug mode enabled")


@cli.command()
@click.argument('gamertag')
@click.option('--games', '-g', default=10, help='Number of games to analyze (default: 10)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def analyze(ctx, gamertag: str, games: int, verbose: bool):
    """Analyze a player's performance and generate coaching insights."""
    if ctx.obj.get('debug'):
        click.echo(f"🔍 Analyzing {games} games for player: {gamertag}")
    
    if verbose:
        click.echo("📋 Analysis Configuration:")
        click.echo(f"  • Player: {gamertag}")
        click.echo(f"  • Games: {games}")
        click.echo(f"  • Debug: {ctx.obj.get('debug', False)}")
    
    try:
        # TODO: Implement actual analysis logic
        click.echo("⚠️  Analysis functionality not yet implemented")
        click.echo("🔨 This will be implemented in Phase 4: Data Management & Orchestration")
        
        # Placeholder for future implementation
        # from .services.analysis_service import analyze_player
        # result = asyncio.run(analyze_player(gamertag, games))
        # display_analysis_results(result, verbose)
        
    except Exception as e:
        logger.error(f"Analysis failed for {gamertag}", error=str(e))
        click.echo(f"❌ Analysis failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload/--no-reload', default=True, help='Enable auto-reload')
def serve(host: str, port: int, reload: bool):
    """Start the web server."""
    import uvicorn
    
    click.echo(f"🚀 Starting Rocket League Coach server on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@cli.command()
def config():
    """Display current configuration."""
    settings = get_settings()
    
    click.echo("⚙️  Rocket League Coach Configuration:")
    click.echo()
    click.echo("🌍 Environment:")
    click.echo(f"  • Environment: {settings.environment}")
    click.echo(f"  • Debug: {settings.debug}")
    click.echo(f"  • Log Level: {settings.log_level}")
    click.echo()
    click.echo("🎮 Ballchasing API:")
    click.echo(f"  • Base URL: {settings.ballchasing_base_url}")
    click.echo(f"  • Rate Limit: {settings.ballchasing_rate_limit_per_second}/sec, {settings.ballchasing_rate_limit_per_hour}/hour")
    api_key_status = "✅ Configured" if settings.ballchasing_api_key and settings.ballchasing_api_key != "your_ballchasing_api_key_here" else "❌ Not configured"
    click.echo(f"  • API Key: {api_key_status}")
    click.echo()
    click.echo("📊 Analysis:")
    click.echo(f"  • Default Games: {settings.default_games_count}")
    click.echo(f"  • Min Sample Size: {settings.min_sample_size_for_correlation}")
    click.echo(f"  • Significance Threshold: {settings.statistical_significance_threshold}")
    click.echo(f"  • Effect Size Threshold: {settings.effect_size_threshold}")
    click.echo()
    click.echo("📁 Storage:")
    click.echo(f"  • Replays: {settings.replays_dir}")
    click.echo(f"  • Cache: {settings.analysis_cache_dir}")
    click.echo(f"  • Player Data: {settings.player_data_dir}")
    click.echo(f"  • Logs: {settings.logs_dir}")


@cli.command()
def health():
    """Check application health and dependencies."""
    click.echo("🏥 Health Check:")
    
    # Check configuration
    try:
        settings = get_settings()
        click.echo("✅ Configuration loaded successfully")
    except Exception as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        return
    
    # Check API key
    if settings.ballchasing_api_key and settings.ballchasing_api_key != "your_ballchasing_api_key_here":
        click.echo("✅ Ballchasing API key configured")
    else:
        click.echo("❌ Ballchasing API key not configured")
    
    # Check directories
    directories = [
        ("Replays", settings.replays_dir),
        ("Cache", settings.analysis_cache_dir),
        ("Player Data", settings.player_data_dir),
        ("Logs", settings.logs_dir),
    ]
    
    for name, path in directories:
        if path.exists():
            click.echo(f"✅ {name} directory exists: {path}")
        else:
            click.echo(f"⚠️  {name} directory missing: {path}")
    
    # TODO: Check external dependencies
    click.echo("📡 External Dependencies:")
    click.echo("⚠️  Ballchasing API connectivity check not implemented yet")
    click.echo("⚠️  Redis connectivity check not implemented yet")


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
def init():
    """Initialize the database."""
    click.echo("🗄️ Database initialization not yet implemented")
    # TODO: Implement database initialization


@db.command()
def migrate():
    """Run database migrations."""
    click.echo("🗄️ Database migrations not yet implemented")
    # TODO: Implement database migrations


@cli.command()
def version():
    """Display version information."""
    click.echo("🚀 Rocket League Coach v1.0.0")
    click.echo("📧 Contact: gwllosa@gmail.com")
    click.echo("🔗 GitHub: https://github.com/GWLlosa/rocket-league-coach")


def display_analysis_results(result: dict, verbose: bool = False):
    """Display analysis results in a formatted way."""
    # TODO: Implement result display formatting
    click.echo("📊 Analysis Results:")
    click.echo("🔨 Result formatting not yet implemented")


if __name__ == '__main__':
    cli()
