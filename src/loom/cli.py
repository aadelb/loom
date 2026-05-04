"""Typer CLI for Loom MCP — command-line interface for all research tools.

Subcommand groups for:
- serve: start the FastMCP server
- fetch, spider, markdown, search, deep, github, camoufox, botasaurus
- session, config, cache, llm, journey-test, repl

All commands connect to the MCP server via streamable-http client.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal, cast

import typer
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.json import JSON

from loom.journey import run_journey
from loom.server import main as server_main

# App setup
app = typer.Typer(
    name="loom",
    help="Smart internet research MCP client — fetch, scrape, search, and analyze with LLM orchestration",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)

# Global options
ServerURL = typer.Option(
    "http://127.0.0.1:8787/mcp",
    "--server",
    help="MCP server URL",
    envvar="LOOM_SERVER",
)
OutputJSON = typer.Option(
    False,
    "--json",
    help="Output as JSON (instead of pretty-printed)",
)
OutputPretty = typer.Option(
    True,
    "--pretty",
    help="Pretty-print output with colors (default)",
)
Quiet = typer.Option(
    False,
    "--quiet",
    help="Suppress output (exit code only)",
)
Timeout = typer.Option(
    120,
    "--timeout",
    help="Request timeout in seconds",
)

# Module-level defaults to avoid B008 mutable default in function signature
_empty_list: list[str] = []
_empty_domains: list[str] = []


async def _call_mcp_tool(
    server_url: str,
    tool_name: str,
    params: dict[str, Any],
    timeout: int = 120,  # noqa: ASYNC109
) -> dict[str, Any] | None:
    """Call an MCP tool via the streamable-http client.

    Args:
        server_url: MCP server URL
        tool_name: name of tool to invoke
        params: tool parameters
        timeout: request timeout in seconds

    Returns:
        Tool result dict or None on error

    Raises:
        typer.Exit: with code 1 on tool error, 3 on connection failure
    """
    try:
        async with (
            streamablehttp_client(server_url, timeout=timeout) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            result = await session.call_tool(tool_name, params)
            # Extract text from MCP TextContent
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, "text"):
                    try:
                        return cast(dict[str, Any] | None, json.loads(content.text))
                    except json.JSONDecodeError:
                        return {"text": content.text}
                return {"text": str(content)}
            return {}
    except ConnectionError as e:
        err_console.print(f"[red]Error: Server unreachable at {server_url}[/red]")
        err_console.print(f"[red]Details: {e}[/red]")
        raise typer.Exit(code=3) from None
    except Exception as e:
        err_console.print(f"[red]Error calling tool {tool_name}: {e}[/red]")
        raise typer.Exit(code=1) from None


def _print_result(
    result: dict[str, Any] | None,
    json_mode: bool = False,
    quiet: bool = False,
) -> None:
    """Print tool result with optional JSON formatting.

    Args:
        result: tool result dict
        json_mode: if True, output as JSON; else pretty-print
        quiet: if True, suppress output entirely
    """
    if quiet or result is None:
        return

    if json_mode:
        console.print_json(data=result)
    else:
        if isinstance(result, dict):
            if "text" in result and len(result) == 1:
                console.print(result["text"])
            else:
                console.print(JSON(json.dumps(result)))
        else:
            console.print(result)


def _safe_asyncio_run(coro: Any) -> Any:
    """Safely run asyncio coroutine, handling event loop issues.

    If an event loop is already running (e.g., in tests), use it.
    Otherwise, create a new one.
    """
    try:
        loop = asyncio.get_running_loop()
        # We're already in an event loop, can't use asyncio.run()
        # This shouldn't happen in normal CLI usage but helps in tests
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(coro)


# ─── SERVE subcommand ────────────────────────────────────────────────────────


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Server host"),
    port: int = typer.Option(8787, "--port", help="Server port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes"),
) -> None:
    """Start the Loom MCP server.

    By default listens on 127.0.0.1:8787 with streamable-http transport.
    """
    import os

    os.environ["LOOM_HOST"] = host
    os.environ["LOOM_PORT"] = str(port)

    console.print(f"[cyan]Starting Loom MCP server on {host}:{port}[/cyan]")
    server_main()


# ─── INSTALL-BROWSERS subcommand ────────────────────────────────────────────


@app.command("install-browsers")
def install_browsers() -> None:
    """Install Playwright Chromium+Firefox and fetch Camoufox browser binaries.

    Runs `playwright install chromium firefox` and `python -m camoufox fetch`
    in sequence. Required once after `pip install loom-mcp[stealth]` before
    the stealth / dynamic scraping modes will work.
    """
    import subprocess
    import sys as _sys

    console.print("[cyan]Installing Playwright browsers (chromium + firefox)...[/cyan]")
    rc = subprocess.call([_sys.executable, "-m", "playwright", "install", "chromium", "firefox"])
    if rc != 0:
        err_console.print("[red]playwright install failed[/red]")
        raise typer.Exit(code=rc)

    console.print("[cyan]Fetching Camoufox Firefox binary...[/cyan]")
    try:
        rc = subprocess.call([_sys.executable, "-m", "camoufox", "fetch"])
    except FileNotFoundError:
        console.print(
            "[yellow]Camoufox not installed. "
            "Run `pip install loom-mcp[stealth]` to enable stealth mode.[/yellow]"
        )
        rc = 0
    if rc != 0:
        err_console.print("[red]camoufox fetch failed[/red]")
        raise typer.Exit(code=rc)

    console.print("[green]✓ Browser runtimes installed[/green]")


# ─── FETCH subcommand ────────────────────────────────────────────────────────


@app.command()
def fetch(
    url: str = typer.Argument(..., help="URL to fetch"),
    mode: str = typer.Option("stealthy", "--mode", help="http | stealthy | dynamic"),
    headers: list[str] = typer.Option(_empty_list, "--header", help="Custom headers (K:V format)"),  # noqa: B008
    user_agent: str | None = typer.Option(None, "--user-agent", help="Custom User-Agent"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    cookie: list[str] = typer.Option(_empty_list, "--cookie", help="Cookies (K=V format)"),  # noqa: B008
    accept_language: str = typer.Option(
        "en-US,en;q=0.9", "--accept-language", help="Language preference"
    ),
    wait_for: str | None = typer.Option(None, "--wait-for", help="CSS selector to wait for"),
    return_format: str = typer.Option(
        "text", "--return-format", help="text | html | json | screenshot"
    ),
    session: str | None = typer.Option(None, "--session", help="Session name to reuse"),
    save: Path | None = typer.Option(None, "--save", help="Save response to file"),  # noqa: B008
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Fetch a URL with adaptive anti-bot strategy."""
    # Parse headers and cookies
    header_dict = {}
    for h in headers:
        k, v = h.split(":", 1)
        header_dict[k.strip()] = v.strip()

    cookie_dict = {}
    for c in cookie:
        k, v = c.split("=", 1)
        cookie_dict[k.strip()] = v.strip()

    params = {
        "url": url,
        "mode": mode,
        "timeout": timeout,
        "return_format": return_format,
    }
    if headers:
        params["headers"] = header_dict
    if user_agent:
        params["user_agent"] = user_agent
    if proxy:
        params["proxy"] = proxy
    if cookie_dict:
        params["cookies"] = cookie_dict
    if accept_language:
        params["accept_language"] = accept_language
    if wait_for:
        params["wait_for"] = wait_for
    if session:
        params["session"] = session

    result = asyncio.run(_call_mcp_tool(server_url, "research_fetch", params, timeout))

    if save and result:
        Path(save).write_text(json.dumps(result, indent=2))
        console.print(f"[green]✓ Saved to {save}[/green]")

    _print_result(result, json_mode, quiet)


# ─── SPIDER subcommand ───────────────────────────────────────────────────────


@app.command()
def spider(
    urls_file: Path = typer.Argument(..., help="File with URLs (one per line)"),  # noqa: B008
    concurrency: int = typer.Option(5, "--concurrency", help="Max parallel fetches"),
    mode: str = typer.Option("stealthy", "--mode", help="http | stealthy | dynamic"),
    out: Path | None = typer.Option(None, "--out", help="Output directory"),  # noqa: B008
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Stop on first error"),
    dedupe: bool = typer.Option(True, "--dedupe/--no-dedupe", help="Deduplicate URLs"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Bulk fetch multiple URLs with concurrency control."""
    if not urls_file.exists():
        err_console.print(f"[red]Error: File not found: {urls_file}[/red]")
        raise typer.Exit(code=2)

    urls = [line.strip() for line in urls_file.read_text().splitlines() if line.strip()]

    params = {
        "urls": urls,
        "mode": mode,
        "concurrency": concurrency,
        "timeout": timeout,
    }
    if fail_fast:
        params["fail_fast"] = fail_fast
    if not dedupe:
        params["dedupe"] = False

    result = asyncio.run(_call_mcp_tool(server_url, "research_spider", params, timeout))
    _print_result(result, json_mode, quiet)


# ─── MARKDOWN subcommand ─────────────────────────────────────────────────────


@app.command()
def markdown(
    url: str = typer.Argument(..., help="URL to convert to markdown"),
    css: str | None = typer.Option(None, "--css", help="CSS selector to extract"),
    screenshot: bool = typer.Option(False, "--screenshot", help="Include screenshot"),
    session: str | None = typer.Option(None, "--session", help="Session to reuse"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Convert a URL to clean markdown with citations."""
    params = {
        "url": url,
        "timeout": timeout,
    }
    if css:
        params["css_selector"] = css
    if screenshot:
        params["screenshot"] = True
    if session:
        params["session"] = session

    result = asyncio.run(_call_mcp_tool(server_url, "research_markdown", params, timeout))
    _print_result(result, json_mode, quiet)


# ─── SEARCH subcommand ───────────────────────────────────────────────────────


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    provider: str = typer.Option("exa", "--provider", help="exa | tavily | firecrawl | brave"),
    n: int = typer.Option(10, "--n", help="Number of results"),
    include_domain: list[str] = typer.Option(  # noqa: B008
        _empty_domains, "--include-domain", help="Domain filter (include)"
    ),
    exclude_domain: list[str] = typer.Option(  # noqa: B008
        _empty_domains, "--exclude-domain", help="Domain filter (exclude)"
    ),
    start_date: str | None = typer.Option(None, "--start-date", help="YYYY-MM-DD"),
    end_date: str | None = typer.Option(None, "--end-date", help="YYYY-MM-DD"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Search across multiple providers (Exa, Tavily, Firecrawl, Brave)."""
    params = {
        "query": query,
        "provider": provider,
        "n": n,
    }
    if include_domain:
        params["include_domains"] = include_domain
    if exclude_domain:
        params["exclude_domains"] = exclude_domain
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    result = asyncio.run(_call_mcp_tool(server_url, "research_search", params, timeout))
    _print_result(result, json_mode, quiet)


# ─── DEEP subcommand ─────────────────────────────────────────────────────────


@app.command()
def deep(
    query: str = typer.Argument(..., help="Research question"),
    depth: int = typer.Option(2, "--depth", help="Search depth (1-3)"),
    provider: str = typer.Option("exa", "--provider", help="Search provider"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """One-shot chained research: search → fetch → markdown → extract."""
    params = {
        "query": query,
        "depth": depth,
        "provider": provider,
    }

    result = asyncio.run(_call_mcp_tool(server_url, "research_deep", params, timeout))
    _print_result(result, json_mode, quiet)


# ─── GITHUB subcommand ───────────────────────────────────────────────────────


@app.command()
def github(
    kind: Literal["repo", "code", "issues"] = typer.Argument(..., help="Search type"),
    query: str = typer.Argument(..., help="Search query"),
    sort: str = typer.Option("stars", "--sort", help="Sort order"),
    order: str = typer.Option("desc", "--order", help="asc | desc"),
    language: str | None = typer.Option(None, "--language", help="Programming language"),
    owner: str | None = typer.Option(None, "--owner", help="Repository owner"),
    repo: str | None = typer.Option(None, "--repo", help="Repository name"),
    limit: int = typer.Option(20, "--limit", help="Max results"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Search GitHub repositories, code, or issues."""
    params = {
        "kind": kind,
        "query": query,
        "sort": sort,
        "order": order,
        "limit": limit,
    }
    if language:
        params["language"] = language
    if owner:
        params["owner"] = owner
    if repo:
        params["repo"] = repo

    result = asyncio.run(_call_mcp_tool(server_url, "research_github", params, timeout))
    _print_result(result, json_mode, quiet)


# ─── CAMOUFOX subcommand ─────────────────────────────────────────────────────


@app.command()
def camoufox(
    url: str = typer.Argument(..., help="URL to scrape"),
    session: str | None = typer.Option(None, "--session", help="Session to reuse"),
    screenshot: bool = typer.Option(False, "--screenshot", help="Include screenshot"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Scrape a URL using Camoufox stealth browser."""
    params = {
        "url": url,
        "timeout": timeout,
    }
    if session:
        params["session"] = session
    if screenshot:
        params["screenshot"] = True

    result = asyncio.run(_call_mcp_tool(server_url, "research_camoufox", params, timeout))
    _print_result(result, json_mode, quiet)


# ─── BOTASAURUS subcommand ──────────────────────────────────────────────────


@app.command()
def botasaurus(
    url: str = typer.Argument(..., help="URL to scrape"),
    session: str | None = typer.Option(None, "--session", help="Session to reuse"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Scrape a URL using Botasaurus anti-bot framework."""
    params = {
        "url": url,
        "timeout": timeout,
    }
    if session:
        params["session"] = session

    result = asyncio.run(_call_mcp_tool(server_url, "research_botasaurus", params, timeout))
    _print_result(result, json_mode, quiet)


# ─── SESSION subcommand ──────────────────────────────────────────────────────


@app.command()
def session(
    action: Literal["open", "list", "close"] = typer.Argument(..., help="Action"),
    name: str | None = typer.Argument(None, help="Session name"),
    browser: str = typer.Option("camoufox", "--browser", help="camoufox | chromium | firefox"),
    login_url: str | None = typer.Option(None, "--login-url", help="Auto-login URL"),
    login_script: Path | None = typer.Option(None, "--login-script", help="Login script file"),  # noqa: B008
    ttl: int = typer.Option(3600, "--ttl", help="Session TTL in seconds"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Manage persistent browser sessions."""
    if action == "open":
        if not name:
            err_console.print("[red]Error: --name required for session open[/red]")
            raise typer.Exit(code=2)

        params: dict[str, Any] = {
            "name": name,
            "browser": browser,
            "ttl_seconds": ttl,
        }
        if login_url:
            params["login_url"] = login_url
        if login_script:
            params["login_script"] = login_script.read_text()

        result = asyncio.run(_call_mcp_tool(server_url, "research_session_open", params, timeout))

    elif action == "list":
        result = asyncio.run(_call_mcp_tool(server_url, "research_session_list", {}, timeout))

    elif action == "close":
        if not name:
            err_console.print("[red]Error: --name required for session close[/red]")
            raise typer.Exit(code=2)

        result = asyncio.run(
            _call_mcp_tool(server_url, "research_session_close", {"name": name}, timeout)
        )

    else:
        err_console.print(f"[red]Unknown action: {action}[/red]")
        raise typer.Exit(code=2)

    _print_result(result, json_mode, quiet)


# ─── CONFIG subcommand ───────────────────────────────────────────────────────


@app.command()
def config(
    action: Literal["get", "set", "list"] = typer.Argument(..., help="Action"),
    key: str | None = typer.Argument(None, help="Config key"),
    value: str | None = typer.Argument(None, help="Config value"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Get, set, or list configuration values."""
    if action == "get":
        params = {"key": key} if key else {}
        result = asyncio.run(_call_mcp_tool(server_url, "research_config_get", params, timeout))

    elif action == "set":
        if not key or not value:
            err_console.print("[red]Error: key and value required[/red]")
            raise typer.Exit(code=2)

        result = asyncio.run(
            _call_mcp_tool(
                server_url,
                "research_config_set",
                {"key": key, "value": value},
                timeout,
            )
        )

    elif action == "list":
        result = asyncio.run(_call_mcp_tool(server_url, "research_config_get", {}, timeout))

    else:
        err_console.print(f"[red]Unknown action: {action}[/red]")
        raise typer.Exit(code=2)

    _print_result(result, json_mode, quiet)


# ─── CACHE subcommand ────────────────────────────────────────────────────────


@app.command()
def cache(
    action: Literal["stats", "clear"] = typer.Argument(..., help="Action"),
    older_than_days: int = typer.Option(30, "--older-than-days", help="Age threshold in days"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """View or manage the response cache."""
    if action == "stats":
        result = asyncio.run(_call_mcp_tool(server_url, "research_cache_stats", {}, timeout))

    elif action == "clear":
        result = asyncio.run(
            _call_mcp_tool(
                server_url,
                "research_cache_clear",
                {"older_than_days": older_than_days},
                timeout,
            )
        )

    else:
        err_console.print(f"[red]Unknown action: {action}[/red]")
        raise typer.Exit(code=2)

    _print_result(result, json_mode, quiet)


# ─── LLM subcommand ──────────────────────────────────────────────────────────


@app.command()
def llm(
    action: Literal[
        "summarize", "extract", "classify", "translate", "expand", "answer", "embed", "chat"
    ] = typer.Argument(..., help="LLM action"),
    text: str | None = typer.Argument(None, help="Input text (or stdin)"),
    file: Path | None = typer.Option(None, "--file", help="Read input from file"),  # noqa: B008
    schema: str | None = typer.Option(None, "--schema", help="JSON schema (extract)"),
    labels: str | None = typer.Option(None, "--labels", help="Comma-separated labels (classify)"),
    target_lang: str = typer.Option("en", "--target-lang", help="Target language code (translate)"),
    n: int = typer.Option(5, "--n", help="Number of queries to expand (expand)"),
    max_tokens: int = typer.Option(200, "--max-tokens", help="Max output tokens"),
    timeout: int = Timeout,
    server_url: str = ServerURL,
    json_mode: bool = OutputJSON,
    quiet: bool = Quiet,
) -> None:
    """Call LLM tools for text processing, extraction, and generation."""
    # Read input text
    if file:
        input_text = file.read_text()
    elif text:
        input_text = text
    else:
        input_text = sys.stdin.read()

    if not input_text:
        err_console.print("[red]Error: No input text provided[/red]")
        raise typer.Exit(code=2)

    params: dict[str, Any] = {}

    if action == "summarize":
        params = {"text": input_text, "max_tokens": max_tokens}

    elif action == "extract":
        if not schema:
            err_console.print("[red]Error: --schema required for extract[/red]")
            raise typer.Exit(code=2)
        params = {"text": input_text, "schema": json.loads(schema)}

    elif action == "classify":
        if not labels:
            err_console.print("[red]Error: --labels required for classify[/red]")
            raise typer.Exit(code=2)
        params = {"text": input_text, "labels": labels.split(",")}

    elif action == "translate":
        params = {"text": input_text, "target_lang": target_lang}

    elif action == "expand":
        params = {"query": input_text, "n": n}

    elif action == "answer":
        # `sources` is required by research_llm_answer. If no sources
        # provided, pass an empty list — the tool will return an error-ish
        # message rather than a TypeError.
        params = {"question": input_text, "sources": []}

    elif action == "embed":
        params = {"texts": [input_text]}

    elif action == "chat":
        params = {"messages": [{"role": "user", "content": input_text}]}

    else:
        err_console.print(f"[red]Unknown action: {action}[/red]")
        raise typer.Exit(code=2)

    result = asyncio.run(_call_mcp_tool(server_url, f"research_llm_{action}", params, timeout))
    _print_result(result, json_mode, quiet)


# ─── JOURNEY-TEST subcommand ─────────────────────────────────────────────────


@app.command()
def journey_test(
    topic: str = typer.Option("llama model family", "--topic", help="Research topic"),
    live: bool = typer.Option(False, "--live", help="Run against real network"),
    record: bool = typer.Option(False, "--record", help="Record screenshots"),
    fixtures: Path | None = typer.Option(  # noqa: B008
        None, "--fixtures", help="Fixtures directory for mocked mode"
    ),
    out: Path = typer.Option(  # noqa: B008
        Path("./journey-out"), "--out", help="Output directory"
    ),
    server_url: str = ServerURL,
) -> None:
    """Run smart end-to-end journey test exercising all 23 tools."""
    console.print("[cyan]Starting journey test[/cyan]")
    console.print(f"  Topic: {topic}")
    console.print(f"  Mode: {'live' if live else 'mocked'}")
    console.print(f"  Server: {server_url}")

    report = asyncio.run(
        run_journey(
            topic=topic,
            server_url=server_url,
            live=live,
            record_screenshots=record,
            fixtures_dir=fixtures,
            out_dir=out,
        )
    )

    # Print summary
    console.print("\n[bold]Journey Report[/bold]")
    console.print(f"  Duration: {report.ended_at or 'incomplete'}")
    console.print(f"  Steps OK: {report.ok_count}")
    console.print(f"  Steps FAIL: {report.fail_count}")

    # Print markdown report to console
    console.print("\n" + report.as_markdown())

    # Exit with non-zero if failures
    if report.fail_count > 0:
        raise typer.Exit(code=1)


# ─── TOOLS subcommand ────────────────────────────────────────────────────────


def _get_tool_cost(tool_name: str) -> int:
    """Get cost for a tool by looking up in TOOL_COSTS.

    Args:
        tool_name: Tool name (with or without research_ prefix)

    Returns:
        Credit cost (int >= 0)
    """
    from loom.billing.token_economy import get_tool_cost

    return get_tool_cost(tool_name)


def _format_cost_label(cost: int) -> str:
    """Format cost as a human-readable label with color.

    Args:
        cost: Credit cost

    Returns:
        Formatted string with color codes for Rich
    """
    if cost == 0:
        return "[green]free[/green]"
    elif cost == 1:
        return "[blue]1 credit[/blue]"
    elif cost <= 5:
        return f"[yellow]{cost} credits[/yellow]"
    elif cost <= 10:
        return f"[orange1]{cost} credits[/orange1]"
    else:
        return f"[red]{cost} credits[/red]"


@app.command()
def tools(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show parameter details"),
    json_mode: bool = OutputJSON,
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
) -> None:
    """List all available MCP tools with costs.

    By default displays tool names, costs, and descriptions in a formatted table.
    Use --verbose to show parameter details for each tool.
    Use --category to filter tools by prefix (e.g., 'llm', 'search', 'fetch').
    Use --json to output full catalog as JSON with cost breakdown.
    """
    from rich.table import Table

    from loom.server import create_app

    # Create app and load tools
    app_instance = create_app()
    tool_list = asyncio.run(app_instance.list_tools())

    # Build category map and collect cost statistics
    tool_map: dict[str, list[Any]] = {}
    cost_counts: dict[int, int] = {}  # cost -> count
    total_cost = 0

    for tool in tool_list:
        # Extract category
        parts = tool.name.split("_")
        if len(parts) >= 3:
            cat = parts[1]  # "research_<category>_..."
        elif len(parts) >= 2:
            cat = parts[1]  # "research_<category>"
        else:
            cat = "other"

        if cat not in tool_map:
            tool_map[cat] = []
        tool_map[cat].append(tool)

        # Track costs
        cost = _get_tool_cost(tool.name)
        cost_counts[cost] = cost_counts.get(cost, 0) + 1
        total_cost += cost

    # Filter by category if specified
    if category:
        if category not in tool_map:
            err_console.print(f"[yellow]No tools found in category '{category}'[/yellow]")
            raise typer.Exit(code=0)
        filtered_tools = tool_map[category]
        category_display = f" (category: {category})"
    else:
        filtered_tools = tool_list
        category_display = ""

    # Output as JSON if requested
    if json_mode:
        tools_data = []
        for tool in sorted(filtered_tools, key=lambda t: t.name):
            cost = _get_tool_cost(tool.name)
            tool_dict = {
                "name": tool.name,
                "description": tool.description or "No description",
                "title": tool.title or tool.name,
                "cost": cost,
            }
            if verbose and hasattr(tool, "inputSchema"):
                tool_dict["parameters"] = tool.inputSchema.get("properties", {})
            tools_data.append(tool_dict)

        # Build cost summary
        summary = {
            "total_tools": len(filtered_tools),
            "cost_summary": {
                "free": cost_counts.get(0, 0),
                "basic_1": cost_counts.get(1, 0),
                "medium_5": cost_counts.get(5, 0),
                "heavy_10": cost_counts.get(10, 0),
                "premium_20": cost_counts.get(20, 0),
                "total_cost": total_cost,
                "average_cost": round(total_cost / len(tool_list), 2) if tool_list else 0,
            },
        }

        console.print_json(
            data={
                "tools": tools_data,
                "count": len(tools_data),
                "summary": summary,
            }
        )
        return

    # Display as formatted table with costs
    table = Table(title=f"Loom MCP Tools{category_display}")
    table.add_column("Tool Name", style="cyan", no_wrap=False)
    table.add_column("Cost", style="white", width=15)
    table.add_column("Description", style="white")
    if verbose:
        table.add_column("Parameters", style="dim")

    for tool in sorted(filtered_tools, key=lambda t: t.name):
        cost = _get_tool_cost(tool.name)
        cost_label = _format_cost_label(cost)
        desc = (tool.description or "No description")[:60]
        if len(tool.description or "") > 60:
            desc += "..."

        if verbose:
            params = ""
            if hasattr(tool, "inputSchema"):
                props = tool.inputSchema.get("properties", {})
                if props:
                    params = ", ".join(props.keys())[:40]
            table.add_row(tool.name, cost_label, desc, params)
        else:
            table.add_row(tool.name, cost_label, desc)

    console.print(table)

    # Print summary statistics
    console.print(f"\n[bold]Cost Summary[/bold]")
    console.print(f"  Total: [cyan]{len(filtered_tools)}[/cyan] tools")
    console.print(f"  Free: [green]{cost_counts.get(0, 0)}[/green]")
    console.print(f"  Basic (1): [blue]{cost_counts.get(1, 0)}[/blue]")
    console.print(f"  Medium (5): [yellow]{cost_counts.get(5, 0)}[/yellow]")
    console.print(f"  Heavy (10): [orange1]{cost_counts.get(10, 0)}[/orange1]")
    console.print(f"  Premium (20): [red]{cost_counts.get(20, 0)}[/red]")
    if len(filtered_tools) == len(tool_list):
        avg_cost = round(total_cost / len(tool_list), 2) if tool_list else 0
        console.print(f"  [dim]Average cost per tool: {avg_cost} credits[/dim]")

    # Show category summary if not filtered
    if not category:
        console.print("\n[dim]Categories:[/dim]")
        for cat in sorted(tool_map.keys()):
            count = len(tool_map[cat])
            console.print(f"  {cat:<15} {count:>3} tools")


# ─── REPL subcommand ─────────────────────────────────────────────────────────


class LoopCompleter(Completer):
    """Simple completer for Loom commands."""

    def get_completions(self, document: Document, complete_event: Any) -> Any:
        """Generate command completions."""
        from prompt_toolkit.completion import Completion

        word = document.get_word_before_cursor()
        if word.startswith("-"):
            return

        # Basic tool names
        tools = [
            "fetch",
            "spider",
            "markdown",
            "search",
            "deep",
            "github",
            "camoufox",
            "botasaurus",
            "session",
            "config",
            "cache",
            "llm",
            "tools",
            "journey-test",
            "exit",
            "help",
        ]
        for tool in tools:
            if tool.startswith(word):
                yield Completion(tool, -len(word))


@app.command()
def repl(server_url: str = ServerURL) -> None:
    """Interactive REPL shell for Loom commands."""
    console.print("[cyan]Loom REPL — type 'help' for commands, 'exit' to quit[/cyan]\n")

    history_file = Path.home() / ".loom_history"
    session: PromptSession[Any] = PromptSession(history=FileHistory(str(history_file)))

    while True:
        try:
            line = session.prompt("loom> ", completer=LoopCompleter())
            if not line.strip():
                continue

            if line.lower() in ["exit", "quit"]:
                console.print("[cyan]Goodbye![/cyan]")
                break

            if line.lower() == "help":
                console.print(
                    """
[bold]Loom Commands[/bold]
  fetch <url>              Fetch a URL
  spider <file>            Bulk fetch URLs
  markdown <url>           Convert to markdown
  search <query>           Search
  deep <query>             Deep research
  github [repo|code] <q>   Search GitHub
  camoufox <url>           Stealth scrape
  botasaurus <url>         Bot scrape
  session [open|list|close] Manage sessions
  config [get|set]         View/set config
  cache [stats|clear]      Cache management
  llm [action]             LLM tools
  tools                    List available tools
  journey-test             Run journey test
  exit                     Exit REPL
"""
                )
                continue

            # Try to parse as a command and execute it
            parts = line.split()
            if len(parts) == 0:
                continue

            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []

            # Route to tool_* wrappers for quick REPL execution
            try:
                if cmd == "fetch" and args:
                    from loom.tools.fetch import tool_fetch

                    result = tool_fetch(url=args[0])
                    console.print(result[0].text if result else "No result")
                elif cmd == "search" and args:
                    from loom.tools.search import tool_search

                    result = tool_search(query=" ".join(args))
                    console.print(result[0].text if result else "No result")
                elif cmd == "github" and len(args) >= 2:
                    from loom.tools.github import tool_github

                    result = tool_github(kind=args[0], query=" ".join(args[1:]))
                    console.print(result[0].text if result else "No result")
                elif cmd == "cache" and args:
                    if args[0] == "stats":
                        from loom.tools.cache_mgmt import tool_cache_stats

                        result = tool_cache_stats()
                        console.print(result[0].text if result else "No result")
                    elif args[0] == "clear":
                        from loom.tools.cache_mgmt import tool_cache_clear

                        result = tool_cache_clear()
                        console.print(result[0].text if result else "No result")
                elif cmd == "session" and args:
                    if args[0] == "list":
                        from loom.sessions import tool_session_list

                        result = tool_session_list()
                        console.print(result[0].text if result else "No result")
                    elif args[0] == "close" and len(args) > 1:
                        from loom.sessions import tool_session_close

                        result = tool_session_close(args[1])
                        console.print(result[0].text if result else "No result")
                elif cmd == "camoufox" and args:
                    from loom.tools.stealth import tool_camoufox

                    result = tool_camoufox(url=args[0])
                    console.print(result[0].text if result else "No result")
                else:
                    console.print(f"[yellow]Command: {cmd} {' '.join(args)}[/yellow]")
                    console.print("[dim]Use CLI directly for full features: loom {cmd} ...[/dim]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        except KeyboardInterrupt:
            console.print("\n[cyan]Goodbye![/cyan]")
            break
        except EOFError:
            console.print("\n[cyan]Goodbye![/cyan]")
            break


# ─── COMPLETIONS subcommand ──────────────────────────────────────────────────


@app.command()
def completions(
    action: Literal["install"] = typer.Argument(..., help="Action"),
) -> None:
    """Manage shell completion installation.

    Generates and installs shell completion scripts for bash, zsh, and fish.
    Auto-detects the current shell unless explicitly specified.
    """
    if action == "install":
        # Find the install.sh script
        script_dir = Path(__file__).parent.parent.parent / "completions"
        install_script = script_dir / "install.sh"

        if not install_script.exists():
            err_console.print(f"[red]Error: install.sh not found at {install_script}[/red]")
            err_console.print("[yellow]Run: python scripts/generate_completions.py first[/yellow]")
            raise typer.Exit(code=2)

        try:
            result = subprocess.run(
                ["bash", str(install_script)],
                check=False,
                cwd=str(script_dir.parent),
            )
            raise typer.Exit(code=result.returncode)
        except FileNotFoundError:
            err_console.print("[red]Error: bash not found[/red]")
            raise typer.Exit(code=1)
    else:
        err_console.print(f"[red]Unknown action: {action}[/red]")
        raise typer.Exit(code=2)


# ─── VERSION subcommand ──────────────────────────────────────────────────────


@app.command()
def version() -> None:
    """Show version information and available tools count."""
    try:
        from loom.server import create_app

        app_instance = create_app()
        tool_list = asyncio.run(app_instance.list_tools())
        tool_count = len(tool_list)
    except Exception:
        tool_count = 220  # Fallback to approximate count

    console.print(f"[cyan]loom[/cyan] version [green]0.1.0a1[/green]")
    console.print(f"[dim]220+ tools available ({tool_count} loaded)[/dim]")


if __name__ == "__main__":
    app()
