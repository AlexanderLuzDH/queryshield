"""Production monitoring daemon for QueryShield"""

import os
import sys
import signal
import logging
import time
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

from queryshield_monitoring import MonitoringConfig, ProductionMonitor

logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(help="Manage production query monitoring")

# Global monitoring instance
_monitor: Optional[ProductionMonitor] = None


def _load_config(config_file: Optional[str] = None) -> MonitoringConfig:
    """Load monitoring config from file or environment"""
    
    # First try config file
    if config_file:
        config_path = Path(config_file)
        if config_path.exists():
            import yaml
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
                prod_config = data.get("production", {})
                
                return MonitoringConfig(
                    api_url=prod_config.get("api_url", "https://api.queryshield.app"),
                    api_key=prod_config.get("api_key", os.getenv("QUERYSHIELD_API_KEY", "")),
                    org_id=prod_config.get("org_id", os.getenv("QUERYSHIELD_ORG_ID", "")),
                    environment=prod_config.get("environment", "production"),
                    sample_rate=float(prod_config.get("sample_rate", 0.01)),
                    slow_query_threshold_ms=float(prod_config.get("slow_query_threshold_ms", 500)),
                    batch_size=int(prod_config.get("batch_size", 100)),
                    batch_timeout_seconds=int(prod_config.get("batch_timeout_seconds", 30)),
                    enabled=prod_config.get("enabled", True),
                )
    
    # Fall back to environment
    return MonitoringConfig.from_env()


def _print_config_status(config: MonitoringConfig):
    """Print configuration status"""
    
    status_table = Table(title="Production Monitoring Configuration")
    status_table.add_column("Setting", style="cyan")
    status_table.add_column("Value", style="green")
    
    status_table.add_row("Enabled", "✅ Yes" if config.enabled else "❌ No")
    status_table.add_row("API URL", config.api_url)
    status_table.add_row("API Key", f"{config.api_key[:10]}***" if config.api_key else "❌ Not set")
    status_table.add_row("Organization", config.org_id or "❌ Not set")
    status_table.add_row("Environment", config.environment)
    status_table.add_row("Sample Rate", f"{config.sample_rate * 100:.1f}%")
    status_table.add_row("Slow Query Threshold", f"{config.slow_query_threshold_ms:.0f}ms")
    status_table.add_row("Batch Size", str(config.batch_size))
    status_table.add_row("Batch Timeout", f"{config.batch_timeout_seconds}s")
    
    console.print(status_table)


@app.command()
def start(
    config_file: Optional[str] = typer.Option(
        "queryshield.yml",
        "--config",
        help="Path to queryshield.yml config file"
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Log level (debug, info, warning, error)"
    ),
):
    """Start production monitoring daemon"""
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    config = _load_config(config_file)
    
    # Validate configuration
    if not config.enabled:
        console.print("[yellow]⚠️  Production monitoring is disabled[/yellow]")
        return
    
    if not config.api_key:
        console.print("[red]❌ QUERYSHIELD_API_KEY not set[/red]")
        console.print("Set via environment variable or in queryshield.yml:")
        console.print("  export QUERYSHIELD_API_KEY=sk_xxx")
        sys.exit(1)
    
    if not config.org_id:
        console.print("[red]❌ QUERYSHIELD_ORG_ID not set[/red]")
        console.print("Set via environment variable or in queryshield.yml:")
        console.print("  export QUERYSHIELD_ORG_ID=org_xxx")
        sys.exit(1)
    
    console.print("[green]✅ Starting QueryShield Production Monitoring[/green]\n")
    _print_config_status(config)
    
    # Create monitor
    global _monitor
    _monitor = ProductionMonitor(config)
    
    console.print("\n[cyan]Monitoring active. Press Ctrl+C to stop.[/cyan]\n")
    
    # Setup signal handlers
    def shutdown_handler(signum, frame):
        console.print("\n[yellow]⏹️  Shutting down...[/yellow]")
        if _monitor:
            _monitor.shutdown()
        console.print("[green]✅ Shutdown complete[/green]")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_handler(None, None)


@app.command()
def status(
    config_file: Optional[str] = typer.Option(
        "queryshield.yml",
        "--config",
        help="Path to queryshield.yml config file"
    ),
):
    """Show production monitoring status"""
    
    config = _load_config(config_file)
    
    console.print("[cyan]Production Monitoring Status[/cyan]\n")
    _print_config_status(config)
    
    # Check connectivity
    if config.api_key and config.org_id:
        console.print("\n[cyan]Testing connectivity...[/cyan]")
        try:
            import httpx
            
            client = httpx.Client(timeout=5)
            response = client.get(
                f"{config.api_url}/api/health",
                headers={"Authorization": f"Bearer {config.api_key}"},
            )
            
            if response.status_code == 200:
                console.print("[green]✅ Connected to SaaS backend[/green]")
            else:
                console.print(f"[yellow]⚠️  SaaS returned {response.status_code}[/yellow]")
            
            client.close()
        except Exception as e:
            console.print(f"[red]❌ Connection failed: {e}[/red]")


@app.command()
def test(
    config_file: Optional[str] = typer.Option(
        "queryshield.yml",
        "--config",
        help="Path to queryshield.yml config file"
    ),
):
    """Test production monitoring with sample data"""
    
    config = _load_config(config_file)
    
    if not config.api_key or not config.org_id:
        console.print("[red]❌ API key and org ID required[/red]")
        sys.exit(1)
    
    console.print("[cyan]Testing production monitoring...[/cyan]\n")
    _print_config_status(config)
    
    # Create monitor
    monitor = ProductionMonitor(config)
    
    # Record test queries
    test_queries = [
        ("SELECT * FROM users WHERE id = ?", 45.2),
        ("SELECT * FROM posts WHERE user_id = ?", 125.8),
        ("SELECT COUNT(*) FROM comments WHERE post_id = ?", 8.3),
        ("SELECT * FROM users WHERE email = ?", 52.1),
        ("SELECT * FROM posts WHERE created_at > ?", 85.6),
    ]
    
    console.print(f"\nRecording {len(test_queries)} test queries...\n")
    
    query_table = Table(title="Test Queries")
    query_table.add_column("SQL", style="cyan")
    query_table.add_column("Duration", style="green")
    query_table.add_column("Slow", style="yellow")
    
    for sql, duration_ms in test_queries:
        slow = "🔴 Yes" if duration_ms > config.slow_query_threshold_ms else "✅ No"
        query_table.add_row(sql[:50] + "...", f"{duration_ms}ms", slow)
        monitor.record_query(sql, duration_ms)
    
    console.print(query_table)
    
    # Flush
    console.print("\n[cyan]Flushing batch to SaaS...[/cyan]")
    monitor.shutdown()
    
    console.print("[green]✅ Test complete[/green]")


@app.command()
def validate(
    config_file: Optional[str] = typer.Option(
        "queryshield.yml",
        "--config",
        help="Path to queryshield.yml config file"
    ),
):
    """Validate production monitoring configuration"""
    
    try:
        config = _load_config(config_file)
    except Exception as e:
        console.print(f"[red]❌ Config error: {e}[/red]")
        sys.exit(1)
    
    console.print("[cyan]Validating configuration...[/cyan]\n")
    
    errors = []
    warnings = []
    
    # Check API key
    if not config.api_key:
        errors.append("QUERYSHIELD_API_KEY not set")
    
    # Check org ID
    if not config.org_id:
        errors.append("QUERYSHIELD_ORG_ID not set")
    
    # Validate sample rate
    if not (0 <= config.sample_rate <= 1):
        errors.append(f"Invalid sample_rate: {config.sample_rate} (must be 0-1)")
    
    # Validate thresholds
    if config.slow_query_threshold_ms < 0:
        errors.append(f"Invalid slow_query_threshold_ms: {config.slow_query_threshold_ms}")
    
    # Validate batch settings
    if config.batch_size < 1:
        errors.append(f"Invalid batch_size: {config.batch_size} (must be >0)")
    
    if config.batch_timeout_seconds < 1:
        errors.append(f"Invalid batch_timeout_seconds: {config.batch_timeout_seconds} (must be >0)")
    
    # Warnings
    if config.sample_rate < 0.001:
        warnings.append(f"Low sample_rate: {config.sample_rate * 100:.4f}% (very little data)")
    
    if config.sample_rate > 0.5:
        warnings.append(f"High sample_rate: {config.sample_rate * 100:.1f}% (high overhead)")
    
    # Report
    if errors:
        console.print("[red]❌ Configuration invalid:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        sys.exit(1)
    
    if warnings:
        console.print("[yellow]⚠️  Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  • {warning}")
    
    console.print("[green]✅ Configuration valid[/green]")
    _print_config_status(config)


@app.command()
def config_example():
    """Show example queryshield.yml configuration"""
    
    example_config = """
# QueryShield Production Monitoring Configuration

# Test analysis settings (existing)
tests:
  runner: django
  explain: true
  
# Production monitoring settings (NEW)
production:
  # SaaS API configuration
  api_url: https://api.queryshield.app
  api_key: ${QUERYSHIELD_API_KEY}  # or set QUERYSHIELD_API_KEY env var
  org_id: ${QUERYSHIELD_ORG_ID}    # or set QUERYSHIELD_ORG_ID env var
  
  # Environment name
  environment: production
  
  # Query sampling rate (0.0 = off, 1.0 = 100%)
  sample_rate: 0.01  # 1% sampling
  
  # Slow query threshold
  slow_query_threshold_ms: 500
  
  # Batch upload settings
  batch_size: 100          # queries per batch
  batch_timeout_seconds: 30  # max time to wait
  
  # Enable/disable
  enabled: true

# Budget settings (existing)
budgets:
  test_name: "*"
  max_queries: 100
  max_query_time_ms: 50000
"""
    
    console.print(Panel(example_config, title="Example queryshield.yml"))


if __name__ == "__main__":
    app()
