# Zsh completion script for loom CLI
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

    _arguments "1: :(${commands[@]})" \
              "${global_options[@]}" && return 0

    case $words[2] in
        fetch|markdown|camoufox|botasaurus)
            _arguments \
                '1:URL:' \
                '--mode[http|stealthy|dynamic]' \
                '--return-format[text|html|json|screenshot]' \
                '--session[Session name]' \
                '--save[Save response to file]' \
                "${global_options[@]}"
            ;;
        search)
            _arguments \
                '1:Query:' \
                '--provider[exa|tavily|firecrawl|brave]' \
                '--n[Number of results]' \
                "${global_options[@]}"
            ;;
        session)
            _arguments \
                '1:(open list close)' \
                '--browser[Browser type]' \
                '--login-url[Auto-login URL]' \
                "${global_options[@]}"
            ;;
        config)
            _arguments \
                '1:(get set list)' \
                '2:Key:' \
                '3:Value:' \
                "${global_options[@]}"
            ;;
        cache)
            _arguments \
                '1:(stats clear)' \
                '--older-than-days[Age threshold]' \
                "${global_options[@]}"
            ;;
        llm)
            _arguments \
                '1:(summarize extract classify translate expand answer embed chat)' \
                '--file[Input file]' \
                '--schema[JSON schema]' \
                '--max-tokens[Max output tokens]' \
                "${global_options[@]}"
            ;;
        completions)
            _arguments \
                '1:(install)' \
                "${global_options[@]}"
            ;;
    esac
}

_loom
