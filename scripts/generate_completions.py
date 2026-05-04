#!/usr/bin/env python3
"""Generate shell completion scripts for loom CLI using Typer.

Generates completion scripts for bash, zsh, and fish shells.
Output files are written to the completions/ directory.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def generate_completions() -> None:
    """Generate shell completion scripts for all supported shells."""
    # Get project root (parent of scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    completions_dir = project_root / "completions"

    # Create completions directory if it doesn't exist
    completions_dir.mkdir(exist_ok=True)

    # Use typer CLI to generate completions
    # Typer uses env var LOOM_COMPLETE to generate completions
    shells = [
        ("bash", "loom.bash"),
        ("zsh", "loom.zsh"),
        ("fish", "loom.fish"),
    ]

    for shell_name, output_file in shells:
        output_path = completions_dir / output_file
        print(f"Generating {shell_name} completions -> {output_path}")

        try:
            # Use typer CLI completion generation
            # This works by setting LOOM_COMPLETE environment variable
            env_var = f"_LOOM_COMPLETE={shell_name}_source"
            result = subprocess.run(
                [sys.executable, "-m", "typer", "loom.cli", "run", "--extra-completion", shell_name],
                capture_output=True,
                text=True,
                cwd=str(project_root),
                env={**dict(subprocess.os.environ), "PYTHONPATH": str(project_root / "src")},
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                output_path.write_text(result.stdout)
                output_path.chmod(0o644)
                print(f"  ✓ Generated {len(result.stdout)} bytes")
            else:
                # Fallback: generate completion script manually
                print(f"  ! Typer CLI failed, generating manual script for {shell_name}")
                completion_content = _generate_manual_completion(shell_name)
                output_path.write_text(completion_content)
                output_path.chmod(0o644)
                print(f"  ✓ Generated {len(completion_content)} bytes (manual)")

        except Exception as e:
            print(f"  ✗ Error generating {shell_name}: {e}")
            # Still generate a basic manual script as fallback
            completion_content = _generate_manual_completion(shell_name)
            output_path.write_text(completion_content)
            output_path.chmod(0o644)
            print(f"  ✓ Generated fallback {shell_name} script")

    print(f"\n✓ Completion scripts generated in {completions_dir}")


def _generate_manual_completion(shell: str) -> str:
    """Generate a basic completion script for the given shell."""
    commands = [
        "serve",
        "install-browsers",
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
        "journey-test",
        "tools",
        "repl",
        "completions",
        "version",
        "help",
    ]

    if shell == "bash":
        return _bash_completion(commands)
    elif shell == "zsh":
        return _zsh_completion(commands)
    elif shell == "fish":
        return _fish_completion(commands)
    else:
        raise ValueError(f"Unknown shell: {shell}")


def _bash_completion(commands: list[str]) -> str:
    """Generate bash completion script."""
    script = """# Bash completion script for loom CLI
# Install with: source completions/loom.bash
# Or: sudo cp completions/loom.bash /etc/bash_completion.d/loom

_loom_completion() {
    local cur prev words cword
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local commands="serve install-browsers fetch spider markdown search deep github camoufox botasaurus session config cache llm journey-test tools repl completions version help"

    # Complete main commands
    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
        return
    fi

    # Subcommand-specific completions
    case "${COMP_WORDS[1]}" in
        fetch|markdown|camoufox|botasaurus)
            case "${prev}" in
                --mode)
                    COMPREPLY=( $(compgen -W "http stealthy dynamic" -- ${cur}) )
                    return
                    ;;
                --return-format)
                    COMPREPLY=( $(compgen -W "text html json screenshot" -- ${cur}) )
                    return
                    ;;
                --session|--save)
                    COMPREPLY=( $(compgen -f -- ${cur}) )
                    return
                    ;;
            esac
            ;;
        search)
            case "${prev}" in
                --provider)
                    COMPREPLY=( $(compgen -W "exa tavily firecrawl brave" -- ${cur}) )
                    return
                    ;;
            esac
            ;;
        session)
            case "${prev}" in
                *)
                    COMPREPLY=( $(compgen -W "open list close" -- ${cur}) )
                    return
                    ;;
            esac
            ;;
        config|cache)
            case "${prev}" in
                *)
                    COMPREPLY=( $(compgen -W "get set list stats clear" -- ${cur}) )
                    return
                    ;;
            esac
            ;;
        llm)
            case "${prev}" in
                *)
                    COMPREPLY=( $(compgen -W "summarize extract classify translate expand answer embed chat" -- ${cur}) )
                    return
                    ;;
            esac
            ;;
        completions)
            case "${prev}" in
                *)
                    COMPREPLY=( $(compgen -W "install" -- ${cur}) )
                    return
                    ;;
            esac
            ;;
    esac

    # Global options
    if [[ ${cur} == -* ]]; then
        local options="--help --json --quiet --timeout --server"
        COMPREPLY=( $(compgen -W "${options}" -- ${cur}) )
    fi
}

complete -o default -F _loom_completion loom
"""
    return script


def _zsh_completion(commands: list[str]) -> str:
    """Generate zsh completion script."""
    script = """# Zsh completion script for loom CLI
# Install with: echo 'source completions/loom.zsh' >> ~/.zshrc
# Or: cp completions/loom.zsh /usr/share/zsh/site-functions/_loom

#compdef loom

_loom() {
    local -a commands=(
        'serve:Start the Loom MCP server'
        'install-browsers:Install Playwright browsers and Camoufox'
        'fetch:Fetch a URL with adaptive anti-bot strategy'
        'spider:Bulk fetch multiple URLs with concurrency control'
        'markdown:Convert a URL to clean markdown'
        'search:Search across multiple providers'
        'deep:Chained research pipeline'
        'github:Search GitHub repositories and code'
        'camoufox:Scrape with Camoufox stealth browser'
        'botasaurus:Scrape with Botasaurus framework'
        'session:Manage persistent browser sessions'
        'config:Get, set, or list configuration'
        'cache:View or manage response cache'
        'llm:Call LLM tools for text processing'
        'journey-test:Run end-to-end journey test'
        'tools:List all available MCP tools'
        'repl:Interactive REPL shell'
        'completions:Shell completion management'
        'version:Show version and tool count'
        'help:Show help information'
    )

    local -a global_options=(
        '--help[Show help information]'
        '--json[Output as JSON]'
        '--quiet[Suppress output]'
        '--timeout[Request timeout in seconds]'
        '--server[MCP server URL]'
    )

    _arguments "1: :(${commands[@]})" \\
              "${global_options[@]}" && return 0

    case $words[2] in
        fetch|markdown|camoufox|botasaurus)
            _arguments \\
                '1:URL:' \\
                '--mode[http|stealthy|dynamic]' \\
                '--return-format[text|html|json|screenshot]' \\
                '--session[Session name]' \\
                '--save[Save response to file]' \\
                "${global_options[@]}"
            ;;
        search)
            _arguments \\
                '1:Query:' \\
                '--provider[exa|tavily|firecrawl|brave]' \\
                '--n[Number of results]' \\
                "${global_options[@]}"
            ;;
        session)
            _arguments \\
                '1:(open list close)' \\
                '--browser[Browser type]' \\
                '--login-url[Auto-login URL]' \\
                "${global_options[@]}"
            ;;
        config)
            _arguments \\
                '1:(get set list)' \\
                '2:Key:' \\
                '3:Value:' \\
                "${global_options[@]}"
            ;;
        cache)
            _arguments \\
                '1:(stats clear)' \\
                '--older-than-days[Age threshold]' \\
                "${global_options[@]}"
            ;;
        llm)
            _arguments \\
                '1:(summarize extract classify translate expand answer embed chat)' \\
                '--file[Input file]' \\
                '--schema[JSON schema]' \\
                '--max-tokens[Max output tokens]' \\
                "${global_options[@]}"
            ;;
        completions)
            _arguments \\
                '1:(install)' \\
                "${global_options[@]}"
            ;;
    esac
}

_loom
"""
    return script


def _fish_completion(commands: list[str]) -> str:
    """Generate fish completion script."""
    script = """# Fish completion script for loom CLI
# Install with: cp completions/loom.fish ~/.config/fish/completions/
# Or: ln -s (pwd)/completions/loom.fish ~/.config/fish/completions/

set -l commands serve install-browsers fetch spider markdown search deep github camoufox botasaurus session config cache llm journey-test tools repl completions version help

# Main commands
complete -c loom -f -n "__fish_use_subcommand_from_list $commands" -n "not __fish_seen_subcommand_from $commands"
for cmd in $commands
    complete -c loom -f -n "__fish_seen_subcommand_from $cmd" -n "not __fish_seen_subcommand_from $commands"
end

# Command descriptions
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a serve -d "Start the MCP server"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a install-browsers -d "Install Playwright and Camoufox"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a fetch -d "Fetch a URL"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a spider -d "Bulk fetch URLs"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a markdown -d "Convert URL to markdown"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a search -d "Search across providers"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a deep -d "Deep research pipeline"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a github -d "Search GitHub"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a camoufox -d "Stealth scrape"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a botasaurus -d "Bot scrape"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a session -d "Manage sessions"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a config -d "Configuration"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a cache -d "Cache management"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a llm -d "LLM tools"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a journey-test -d "Journey test"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a tools -d "List tools"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a repl -d "Interactive REPL"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a completions -d "Shell completions"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a version -d "Version info"
complete -c loom -n "__fish_use_subcommand_from_list $commands" -a help -d "Show help"

# Global options
complete -c loom -f -s h -l help -d "Show help"
complete -c loom -f -l json -d "Output as JSON"
complete -c loom -f -l quiet -d "Suppress output"
complete -c loom -l timeout -d "Request timeout (seconds)"
complete -c loom -l server -d "MCP server URL"

# fetch command options
complete -c loom -n "__fish_seen_subcommand_from fetch" -l mode -d "http|stealthy|dynamic"
complete -c loom -n "__fish_seen_subcommand_from fetch" -l return-format -d "text|html|json|screenshot"
complete -c loom -n "__fish_seen_subcommand_from fetch" -l session -d "Session name"
complete -c loom -n "__fish_seen_subcommand_from fetch" -l header -d "Custom header (K:V)"
complete -c loom -n "__fish_seen_subcommand_from fetch" -l cookie -d "Cookie (K=V)"

# search command options
complete -c loom -n "__fish_seen_subcommand_from search" -l provider -d "exa|tavily|firecrawl|brave"
complete -c loom -n "__fish_seen_subcommand_from search" -l n -d "Number of results"
complete -c loom -n "__fish_seen_subcommand_from search" -l include-domain -d "Include domain"
complete -c loom -n "__fish_seen_subcommand_from search" -l exclude-domain -d "Exclude domain"

# session command subcommands
complete -c loom -n "__fish_seen_subcommand_from session" -f -a open -d "Open session"
complete -c loom -n "__fish_seen_subcommand_from session" -f -a list -d "List sessions"
complete -c loom -n "__fish_seen_subcommand_from session" -f -a close -d "Close session"

# config command subcommands
complete -c loom -n "__fish_seen_subcommand_from config" -f -a get -d "Get config"
complete -c loom -n "__fish_seen_subcommand_from config" -f -a set -d "Set config"
complete -c loom -n "__fish_seen_subcommand_from config" -f -a list -d "List config"

# cache command subcommands
complete -c loom -n "__fish_seen_subcommand_from cache" -f -a stats -d "Cache stats"
complete -c loom -n "__fish_seen_subcommand_from cache" -f -a clear -d "Clear cache"

# llm command subcommands
complete -c loom -n "__fish_seen_subcommand_from llm" -f -a summarize -d "Summarize text"
complete -c loom -n "__fish_seen_subcommand_from llm" -f -a extract -d "Extract data"
complete -c loom -n "__fish_seen_subcommand_from llm" -f -a classify -d "Classify text"
complete -c loom -n "__fish_seen_subcommand_from llm" -f -a translate -d "Translate text"
complete -c loom -n "__fish_seen_subcommand_from llm" -f -a expand -d "Expand query"
complete -c loom -n "__fish_seen_subcommand_from llm" -f -a answer -d "Answer question"
complete -c loom -n "__fish_seen_subcommand_from llm" -f -a embed -d "Embed text"
complete -c loom -n "__fish_seen_subcommand_from llm" -f -a chat -d "Chat with LLM"

# completions command subcommands
complete -c loom -n "__fish_seen_subcommand_from completions" -f -a install -d "Install completions"
"""
    return script


if __name__ == "__main__":
    generate_completions()
