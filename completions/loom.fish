# Fish completion script for loom CLI
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
