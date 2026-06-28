import os
os.environ["TQDM_DISABLE"] = "1"

import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.")

import typer
import asyncio
import uuid
from pathlib import Path
from datetime import datetime, timezone

from bughunter.core.safety.scope_validator import ScopeValidator
from bughunter.core.safety.engine import SafetyPolicyEngine
from bughunter.core.events.bus import AsyncEventBus
from bughunter.core.events.emitter import AgentEventEmitter
from bughunter.models.event import EventType
from bughunter.models.run import Run, RunStatus
from bughunter.storage.run_store import RunStore
from bughunter.tui.rich_app import RichTui
from bughunter.scanners.static.semgrep import SemgrepScanner
from bughunter.scanners.static.semgrep_rules import SemgrepRuleManager
from bughunter.scanners.dynamic.headers import HeadersScanner
from bughunter.reports.markdown import MarkdownExporter
from bughunter.models.finding import Finding, Severity, Confidence
import aiosqlite

CLI_HELP = """
Bug Hunter CLI — Agentic Vulnerability Scanner

Bug Hunter is an autonomous application security engineer powered by LangGraph.
It performs SAST and DAST analysis by reading your codebase, searching for bugs,
and executing dynamic HTTP payloads to prove vulnerability exploitability.

GETTING STARTED:
  1. Run `bughunter` with no arguments to enter interactive mode.
  2. In interactive mode, type `/scan bughunter-scope.yml` to start scanning.
  
THE SCOPE FILE (bughunter-scope.yml):
  This YAML file dictates the scan parameters and URLs. It controls the SCAN MODE:
    * passive: Completely offline code analysis. No network requests are made.
    * safe-active: The agent will send benign, non-destructive validation payloads.
    * lab-validation: Aggressive mode. The agent is authorized to send destructive 
      exploit payloads (SQLi drops, XSS alerts) to validate vulnerabilities.

LOCAL DATABASES:
  Bug Hunter stores its state locally so your code never leaves your machine 
  (except for the snippets sent to your configured LLM API):
    * .bughunter/runs/bughunter.db (SQLite database tracking all findings and costs)
    * .bughunter/vector_store/ (ChromaDB vector embeddings for code retrieval)
    * .bughunter/reports/ (Final generated Markdown and SARIF reports)
"""

app = typer.Typer(name="bughunter", help=CLI_HELP, rich_markup_mode="markdown")

DB_PATH = Path(".bughunter/bughunter.db")

async def run_scan_async(scope_path: str, ci_mode: bool = False, json_events: bool = False, auto_approve: bool = False):
    import sys
    run_id = str(uuid.uuid4())
    
    # Check if we should force CI mode
    if not sys.stdout.isatty():
        ci_mode = True
        
    event_bus = AsyncEventBus()
    event_bus.start()
    
    if ci_mode:
        import json
        async def event_logger(event):
            if json_events:
                print(json.dumps({"topic": event.type.value, "payload": event.message, "metadata": event.metadata}))
            else:
                print(f"[{event.type.value}][{event.agent}] {event.message}")
        event_bus.subscribe_all(event_logger)
    else:
        from rich.console import Console
        from rich.live import Live
        c = Console()
        
        status = c.status("[bold green]Initializing...[/bold green]")
        
        async def ui_logger(event):
            color = "cyan"
            if "error" in event.type: color = "red"
            elif "finding" in event.type: color = "magenta"
            c.print(f"[{color}][{event.agent}][/] {event.message}")
            status.update(f"[bold green]Working: {event.message}[/bold green]")
            
        event_bus.subscribe_all(ui_logger)
        
        from rich.prompt import Confirm
        import os
        is_trusted = Confirm.ask(f"[bold yellow]Do you trust the folder '{os.path.abspath(scope_path)}' and its contents? (Required to run scans securely)[/bold yellow]")
        if not is_trusted:
            c.print("[bold red]Scan aborted: Folder not trusted.[/bold red]")
            await event_bus.stop()
            return 1
            
        c.print("[yellow]Scan starting... Press Ctrl+C at any time to abort the scan.[/yellow]")
        status.start()
        
    emitter = AgentEventEmitter("Orchestrator", event_bus)
    
    try:
        await emitter.emit(run_id, EventType.phase_started, "Loading Scope")
        
        try:
            scope = ScopeValidator.load_and_validate(scope_path)
        except Exception as e:
            await emitter.emit(run_id, EventType.error, f"Scope error: {e}")
            if ci_mode: return 2
            await asyncio.sleep(0.5)
            return
            
        run_store = RunStore(str(DB_PATH))
        
        run = Run(
            id=run_id,
            scope_path=scope_path,
            token_budget=scope.cost.max_tokens_per_run,
            cost_budget_usd=scope.cost.max_cost_usd
        )
        
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(DB_PATH)) as conn:
            from bughunter.storage.schema import INITIAL_SCHEMA
            await conn.executescript(INITIAL_SCHEMA)
            await conn.commit()
            
        await run_store.create_run(run)
        
        from bughunter.graph.workflow import WorkflowGraph, BugHunterState
        
        graph_runner = WorkflowGraph(run_id, emitter, str(DB_PATH))
        app_graph = graph_runner.build_graph()
        
        initial_state: BugHunterState = {
            "run_id": run_id,
            "scope_path": scope_path,
            "scope": None,
            "manifest": None,
            "test_plans": [],
            "findings": [],
            "evidence_list": [],
            "scored_findings": [],
            "fix_guidance": {},
            "report_path": "",
            "phase": "init",
            "errors": []
        }
        
        graph_task = asyncio.create_task(app_graph.ainvoke(initial_state))
        if not ci_mode:
            try:
                while not graph_task.done():
                    await asyncio.sleep(0.1)
                final_state = graph_task.result()
            except (KeyboardInterrupt, asyncio.CancelledError):
                c.print("\\n[bold red]Scan aborted by user (Ctrl+C)! Stopping agents...[/bold red]")
                graph_task.cancel()
                await emitter.emit(run_id, EventType.error, "Scan aborted by user.")
                try:
                    await graph_task
                except asyncio.CancelledError:
                    pass
                final_state = {"errors": ["Scan aborted by user."]}
            finally:
                status.stop()
        else:
            final_state = await graph_task
        
        if final_state.get("errors"):
            for error in final_state["errors"]:
                await emitter.emit(run_id, EventType.error, error)
            if ci_mode: return 2
            
        if not final_state.get("errors"):
            await run_store.update_run_status(run_id, RunStatus.completed, datetime.now(timezone.utc).isoformat())
        
        # Check CI fail criteria
        if ci_mode:
            findings = final_state.get("findings", [])
            for f in findings:
                if f.severity.value.lower() in scope.ci.fail_on_tier.lower():
                    return 1
                if hasattr(f, 'vuln_score') and f.vuln_score >= scope.ci.fail_on_score:
                    return 1
            return 0
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
    finally:
        await event_bus.stop()
        await asyncio.sleep(0.25) # Allow background async transports (e.g., Langchain's httpx client) to close cleanly
        
        # Post-scan details (only if not running as a raw subcommand where we don't want stdout clutter)
        if not ci_mode and 'final_state' in locals() and not final_state.get('errors'):
            import typer
            from bughunter.storage.finding_store import FindingStore
            from bughunter.reports.markdown import MarkdownExporter
            from rich.console import Console
            from rich.panel import Panel
            
            c = Console()
            c.print("\n[bold green]Scan Completed Successfully![/bold green]")
            
            # Generate markdown report
            store = FindingStore(str(DB_PATH))
            final_findings = await store.get_run_findings(run_id)
            
            report_dir = Path(".bughunter/reports")
            out_path = MarkdownExporter.export(run_id, final_findings, [], str(report_dir))
            
            abs_path = Path(out_path).resolve()
            # Clickable link in terminal using OSC 8
            clickable = f"[link=file://{abs_path}]{abs_path}[/link]"
            
            c.print(Panel.fit(
                f"Detailed Report Generated:\n{clickable}", 
                title="Report", 
                border_style="green"
            ))

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Bug Hunter CLI — Agentic Vulnerability Scanner
    
    If no command is provided, launches the interactive prompt (like agy/codex).
    """
    if ctx.invoked_subcommand is None:
        from bughunter.interactive import start_interactive_session
        start_interactive_session()

@app.command()
def scan(
    scope: str = typer.Option("bughunter-scope.yml", "--scope", "-s", help="Path to scope file"),
    ci_mode: bool = typer.Option(False, "--ci", help="Force CI mode (no TUI)"),
    json_events: bool = typer.Option(False, "--json-events", help="Emit JSON events in CI mode"),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Auto-approve all actions")
):
    """Start a vulnerability scan using the configured scope."""
    import sys
    ret = asyncio.run(run_scan_async(scope, ci_mode, json_events, auto_approve))
    if ret is not None and ret != 0:
        sys.exit(ret)

@app.command("config")
def config_cmd():
    """Configure providers, API keys, and settings interactively."""
    from bughunter.config_manager import ConfigManager
    import questionary
    import typer
    
    while True:
        config = ConfigManager.load()
        active_prof = config.active_profile if config.active_profile else "None"
        
        choices = [
            f"Active Profile: {active_prof}",
            "Add New Profile",
            "Change Active Profile",
            "Delete Profile",
            "Exit"
        ]
        
        action = questionary.select(
            "Configuration Menu:",
            choices=choices
        ).ask()
        
        if not action or action == "Exit":
            break
            
        elif action.startswith("Active Profile"):
            if config.active_profile and config.active_profile in config.profiles:
                p = config.profiles[config.active_profile]
                
                sub_action = questionary.select(
                    f"Active Profile ({config.active_profile}) Options:",
                    choices=["View Details", "Change Model", "Back"]
                ).ask()
                
                if sub_action == "View Details":
                    typer.echo(f"\nActive Profile: {config.active_profile}")
                    typer.echo(f"Provider: {p.provider}")
                    typer.echo(f"Model: {p.model}\n")
                elif sub_action == "Change Model":
                    provider = p.provider
                    model_choices = []
                    if provider == "groq":
                        model_choices = [
                            "llama-3.3-70b-versatile",
                            "llama-3.1-8b-instant",
                            "meta-llama/llama-4-scout-17b-16e-instruct",
                            "qwen/qwen3-32b",
                            "qwen/qwen3.6-27b",
                            "openai/gpt-oss-120b",
                            "openai/gpt-oss-20b",
                            "groq/compound",
                            "groq/compound-mini",
                            "allam-2-7b"
                        ]
                    elif provider == "gemini":
                        model_choices = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]
                    elif provider == "openai":
                        model_choices = ["gpt-4o", "gpt-4o-mini", "o1-mini"]
                        
                    new_model = questionary.select(
                        "Select New Model:",
                        choices=model_choices
                    ).ask()
                    
                    if new_model:
                        p.model = new_model
                        ConfigManager.save(config)
                        typer.echo(f"\n✅ Model updated to '{new_model}' for profile '{config.active_profile}'.\n")
            else:
                typer.echo("\nNo active profile set.\n")
                
        elif action == "Add New Profile":
            name = questionary.text("Enter a name for this profile (e.g. my-groq):").ask()
            if not name: continue
            
            provider = questionary.select(
                "Select AI Provider:",
                choices=["groq", "gemini", "openai"]
            ).ask()
            if not provider: continue

            model_choices = []
            if provider == "groq":
                model_choices = [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                    "meta-llama/llama-4-scout-17b-16e-instruct",
                    "qwen/qwen3-32b",
                    "qwen/qwen3.6-27b",
                    "openai/gpt-oss-120b",
                    "openai/gpt-oss-20b",
                    "groq/compound",
                    "groq/compound-mini",
                    "allam-2-7b"
                ]
            elif provider == "gemini":
                model_choices = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]
            elif provider == "openai":
                model_choices = ["gpt-4o", "gpt-4o-mini", "o1-mini"]
                
            model = questionary.select(
                "Select Model:",
                choices=model_choices
            ).ask()
            if not model: continue

            api_key = questionary.text(f"Enter {provider.capitalize()} API Key (visible):").ask()
            if not api_key: continue

            ConfigManager.add_profile(name, provider, model, api_key)
            ConfigManager.set_active(name)
            typer.echo(f"\n✅ Profile '{name}' added successfully and set as active.\n")
            
        elif action == "Change Active Profile":
            profiles = ConfigManager.get_profiles()
            if not profiles:
                typer.echo("\nNo profiles found. Add a new profile first.\n")
                continue
                
            choices = [k for k in profiles.keys()]
            name = questionary.select("Select profile to activate:", choices=choices).ask()
            if not name: continue
            
            if ConfigManager.set_active(name):
                typer.echo(f"\n✅ Active profile set to '{name}'.\n")
            else:
                typer.echo(f"\n❌ Profile '{name}' not found.\n")
                
        elif action == "Delete Profile":
            profiles = ConfigManager.get_profiles()
            if not profiles:
                typer.echo("\nNo profiles to delete.\n")
                continue
                
            choices = [k for k in profiles.keys()]
            name = questionary.select("Select profile to delete:", choices=choices).ask()
            if not name: continue
            
            if ConfigManager.delete_profile(name):
                typer.echo(f"\n✅ Profile '{name}' deleted.\n")
            else:
                typer.echo(f"\n❌ Profile '{name}' not found.\n")

@app.command()
def retest(
    run_id: str = typer.Option(..., "--run", "-r", help="Original Run ID to retest"),
    finding_id: str = typer.Option(None, "--finding", "-f", help="Specific finding ID to retest")
):
    """Retest findings from a previous run."""
    async def _retest_async():
        retest_run_id = str(uuid.uuid4())
        event_bus = AsyncEventBus()
        event_bus.start()
        
        from bughunter.tui.app import BugHunterApp
        tui = BugHunterApp(event_bus)
        emitter = AgentEventEmitter("Orchestrator", event_bus)
        
        tui_task = asyncio.create_task(tui.run_async())
        
        try:
            from bughunter.agents.retest.agent import RetestAgent
            retest_agent = RetestAgent(retest_run_id, emitter)
            await retest_agent.execute_retest(run_id, finding_id)
            await asyncio.sleep(2) # Give TUI time to render
        finally:
            try:
                tui.exit()
            except:
                pass
            await tui_task
            await event_bus.stop()
            
    asyncio.run(_retest_async())

@app.command()
def export(
    run_id: str = typer.Option(..., "--run", "-r", help="Run ID to export"),
    format: str = typer.Option("sarif", "--format", "-f", help="Format to export (sarif/json)")
):
    """Export findings in SARIF or JSON format."""
    async def _export_async():
        from bughunter.storage.finding_store import FindingStore
        finding_store = FindingStore(str(DB_PATH))
        findings = await finding_store.get_run_findings(run_id)
        
        report_dir = Path(".bughunter/reports")
        if format.lower() == "sarif":
            from bughunter.reports.sarif import SarifExporter
            out_path = SarifExporter.export(run_id, findings, str(report_dir))
        elif format.lower() == "json":
            from bughunter.reports.json_exporter import JsonExporter
            out_path = JsonExporter.export(run_id, findings, str(report_dir))
        else:
            typer.echo(f"Unsupported format: {format}")
            return
            
        typer.echo(f"Exported to {out_path}")
        
    asyncio.run(_export_async())

@app.command()
def github_issue(
    run_id: str = typer.Option(..., "--run", "-r", help="Run ID"),
    finding_id: str = typer.Option(None, "--finding", "-f", help="Finding ID"),
    tier: list[str] = typer.Option(None, "--tier", "-t", help="Severity tiers (e.g. critical high)")
):
    """Export findings as GitHub issues."""
    import os
    if not os.environ.get("GITHUB_TOKEN"):
        typer.echo("Error: GITHUB_TOKEN environment variable required.")
        raise typer.Exit(code=1)
        
    async def _github_issue_async():
        from bughunter.storage.finding_store import FindingStore
        finding_store = FindingStore(str(DB_PATH))
        findings = await finding_store.get_run_findings(run_id)
        
        filtered = []
        if finding_id:
            filtered = [f for f in findings if f.id == finding_id]
        elif tier:
            tiers = [t.lower() for t in tier]
            filtered = [f for f in findings if f.severity.value.lower() in tiers]
            
        for f in filtered:
            typer.echo(f"Would create GitHub Issue for: {f.title} ({f.severity.value})")
            
    asyncio.run(_github_issue_async())

if __name__ == "__main__":
    app()
