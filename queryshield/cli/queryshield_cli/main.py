"""QueryShield CLI - Database query performance analysis"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

try:
    from queryshield_probe.runners.django_runner import run_django_tests
except Exception:  # pragma: no cover - allows importing CLI without Django present
    run_django_tests = None  # type: ignore[assignment]

from queryshield_probe.budgets import check_budgets, load_budgets
from .production_monitor import app as production_app


app = typer.Typer(help="QueryShield - Database Query Performance Analysis")


def _print_summary(report: dict) -> None:
    table = Table(title="QueryShield Summary")
    table.add_column("Test", style="cyan", no_wrap=True)
    table.add_column("Queries", justify="right")
    table.add_column("p95 (ms)", justify="right")
    table.add_column("Problems", justify="left")
    table.add_column("Est. Cost", justify="right", style="yellow")
    for t in report.get("tests", []) or []:
        problems = ", ".join(sorted({p.get("type", "?") for p in t.get("problems", [])}))
        cost_analysis = t.get("cost_analysis", {})
        cost_str = f"${cost_analysis.get('estimated_monthly_cost', 0)}/mo"
        table.add_row(
            t.get("name", "<unknown>"),
            str(t.get("queries_total", 0)),
            f"{t.get('queries_p95_ms', 0):.1f}",
            problems,
            cost_str,
        )
    rprint(table)
    
    # Print cost analysis summary
    cost_analysis = report.get("cost_analysis", {})
    if cost_analysis.get("estimated_monthly_cost"):
        rprint(f"\n[bold]💰 Cost Analysis:[/bold]")
        rprint(f"  Estimated Monthly Cost: ${cost_analysis.get('estimated_monthly_cost')}")
        rprint(f"  Total Queries: {cost_analysis.get('total_queries'):,}")
    
    # Print suggested DDL snippets if present
    ddls = []
    for t in report.get("tests", []) or []:
        for p in t.get("problems", []) or []:
            sug = p.get("suggestion") or {}
            ddl = sug.get("ddl")
            if ddl and ddl not in ddls:
                ddls.append(ddl)
    if ddls:
        rprint("[bold]Suggested indexes (DDL):[/bold]")
        for d in ddls[:5]:
            rprint(f"  {d}")
    report.setdefault("_suggested_ddl", ddls)


@app.command()
def analyze(
    runner: str = typer.Option("django", help="Test runner to use: django|pytest"),
    explain: Optional[bool] = typer.Option(None, "--explain/--no-explain", help="Enable EXPLAIN on Postgres (default on)"),
    budgets: str = typer.Option("queryshield.yml", help="Budgets YAML"),
    output: str = typer.Option(".queryshield/queryshield_report.json", help="Output report path"),
    nplus1_threshold: int = typer.Option(5, help="N+1 cluster threshold"),
    explain_timeout_ms: int = typer.Option(500, help="Per-EXPLAIN timeout (ms)"),
    explain_max_plans: int = typer.Option(50, help="Max EXPLAIN plans per run"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="QueryShield API key for uploading to SaaS"),
    submit: bool = typer.Option(False, "--submit", help="Submit report to QueryShield dashboard"),
    save_baseline: bool = typer.Option(False, "--save-baseline", help="Save report as local baseline"),
):
    """Run tests under the probe and write a report."""
    if os.getenv("QUERYSHIELD_DEBUG"):
        rprint(
            f"[grey]DEBUG explain={explain} nplus1={nplus1_threshold} timeout={explain_timeout_ms} max_plans={explain_max_plans}[/grey]"
        )
    if runner != "django":
        rprint("[red]Only Django runner is implemented in v1[/red]")
        raise typer.Exit(code=2)
    if run_django_tests is None:
        rprint("[red]Django not available in this environment[/red]")
        raise typer.Exit(code=1)
    try:
        report = run_django_tests(
            explain=explain,
            budgets_file=budgets,
            explain_timeout_ms=explain_timeout_ms,
            explain_max_plans=explain_max_plans,
            nplus1_threshold=nplus1_threshold,
        )
    except Exception as e:  # pragma: no cover
        rprint(f"[red]Runtime error:[/red] {e}")
        raise typer.Exit(code=1)
    
    # Persist report
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    # Write DDL suggestions file
    ddls = report.get("_suggested_ddl", []) or []
    ddl_path = os.path.join(os.path.dirname(output) or ".", "ddl-suggestions.txt")
    try:
        with open(ddl_path, "w", encoding="utf-8") as df:
            for line in ddls[:5]:
                df.write(line + "\n")
    except Exception:
        pass
    
    # Save local baseline if requested
    if save_baseline:
        from queryshield_probe.api_client import LocalBaseline
        baseline = LocalBaseline()
        baseline.save_baseline(report)
        rprint("[green]✓ Baseline saved locally[/green]")
    
    # Submit to SaaS if requested or API key provided
    if submit or api_key:
        if not api_key:
            api_key = os.getenv("QUERYSHIELD_API_KEY")
        
        if not api_key:
            rprint("[yellow]⚠ API key not provided. Skipping upload to dashboard.[/yellow]")
            rprint("[grey]Hint: Use --api-key or set QUERYSHIELD_API_KEY environment variable[/grey]")
        else:
            from queryshield_probe.api_client import QueryShieldAPIClient
            try:
                rprint("[dim]📤 Uploading report to QueryShield dashboard...[/dim]")
                with QueryShieldAPIClient(api_key=api_key) as client:
                    response = client.submit_report(report)
                    report_id = response.get("id", "unknown")
                    rprint(f"[green]✓ Report uploaded: {report_id}[/green]")
                    rprint(f"[cyan]📊 View at: https://app.queryshield.io/reports/{report_id}[/cyan]")
            except Exception as e:
                rprint(f"[red]✗ Failed to upload report: {e}[/red]")
                rprint("[grey]Report saved locally but not uploaded to dashboard[/grey]")
    
    # Summary: tests count, total queries, problem count
    total_queries = sum(t.get("queries_total", 0) for t in report.get("tests", []))
    problems_count = sum(len(t.get("problems", [])) for t in report.get("tests", []))
    _print_summary(report)
    overhead = 0.0
    run_ms = (report.get("run", {}) or {}).get("duration_ms") or 0.0
    exp_ms = (report.get("run", {}) or {}).get("explain_runtime_ms") or 0.0
    if run_ms:
        overhead = (exp_ms / float(run_ms)) * 100.0
    rprint(
        f"[bold]Tests:[/bold] {len(report.get('tests', []))}  [bold]Queries:[/bold] {total_queries}  [bold]Problems:[/bold] {problems_count}  [bold]Overhead:[/bold] {overhead:.1f}%"
    )
    rprint(f"[green]✓ Report saved: {output}[/green]")


@app.command("budget-check")
def budget_check(
    budgets: str = typer.Option("queryshield.yml", help="Budgets YAML"),
    report: str = typer.Option(".queryshield/queryshield_report.json", help="Report JSON path"),
    json_out: bool = typer.Option(False, help="Emit JSON line of violations"),
):
    try:
        rules = load_budgets(budgets)
    except Exception as e:
        rprint(f"[red]Invalid budgets config:[/red] {e}")
        raise typer.Exit(code=3)
    data = json.load(open(report, "r", encoding="utf-8"))
    violations = check_budgets(rules, data)
    if violations:
        table = Table(title="Budget Violations")
        table.add_column("Test")
        table.add_column("Issue")
        for v in violations:
            # Expect format "<test>: message"
            if ": " in v:
                name, msg = v.split(": ", 1)
            else:
                name, msg = "<unknown>", v
            table.add_row(name, msg)
        rprint(table)
        if json_out:
            rprint(json.dumps({"violations": violations}))
        raise typer.Exit(code=2)
    rprint("[green]Budgets OK[/green]")


@app.command("record-baseline")
def record_baseline(
    report: str = typer.Option(".queryshield/queryshield_report.json", help="Current report path"),
    output: str = typer.Option(".queryshield/baseline.json", help="Baseline output path"),
):
    data = json.load(open(report, "r", encoding="utf-8"))
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    rprint(f"[green]Baseline saved to {output}[/green]")


@app.command("verify-patch")
def verify_patch(
    baseline: str = typer.Option(".queryshield/baseline.json", help="Baseline JSON"),
    report: str = typer.Option(".queryshield/queryshield_report.json", help="Current report JSON"),
    max_queries_increase: int = typer.Option(0, help="Allowed queries increase per test"),
):
    base = json.load(open(baseline, "r", encoding="utf-8"))
    cur = json.load(open(report, "r", encoding="utf-8"))
    base_map = {t["name"]: t for t in base.get("tests", [])}
    cur_map = {t["name"]: t for t in cur.get("tests", [])}
    failures = []
    for name, ct in cur_map.items():
        bt = base_map.get(name)
        if not bt:
            continue
        if ct.get("queries_total", 0) > bt.get("queries_total", 0) + max_queries_increase:
            failures.append(
                f"{name}: queries_total {ct.get('queries_total')} > baseline {bt.get('queries_total')} + {max_queries_increase}"
            )
    if failures:
        rprint("[red]Patch verification failed:[/red]")
        for f in failures:
            rprint(f" - {f}")
        raise typer.Exit(code=2)
    rprint("[green]Patch verification OK[/green]")


# Add production monitoring subcommand
app.add_typer(production_app, name="production-monitor", help="Manage production query monitoring")


if __name__ == "__main__":  # pragma: no cover
    app()
