# Bash completion script for loom CLI
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
