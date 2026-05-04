# Loom CLI Shell Completions

Shell completion scripts for the Loom MCP command-line interface, supporting Bash, Zsh, and Fish shells.

## Quick Install

```bash
# Auto-detect shell and install
loom completions install

# Or manually:
bash completions/install.sh [bash|zsh|fish]
```

## Manual Installation

### Bash

```bash
# Copy to bash completion directory
sudo cp completions/loom.bash /etc/bash_completion.d/loom

# Or user-local
mkdir -p ~/.bash_completion.d
cp completions/loom.bash ~/.bash_completion.d/loom

# Enable by sourcing
source ~/.bash_completion.d/loom
```

**For macOS with Homebrew:**
```bash
# Bash may not have completions enabled by default. First:
brew install bash-completion

# Then copy to Homebrew location:
cp completions/loom.bash $(brew --prefix)/etc/bash_completion.d/loom
```

### Zsh

```bash
# Add to function path
mkdir -p ~/.zsh/completions
cp completions/loom.zsh ~/.zsh/completions/_loom

# Add to ~/.zshrc:
fpath=(~/.zsh/completions $fpath)
autoload -Uz compinit && compinit
```

**Or for system-wide (Linux):**
```bash
sudo cp completions/loom.zsh /usr/share/zsh/site-functions/_loom
```

### Fish

```bash
# Fish looks in ~/.config/fish/completions by default
mkdir -p ~/.config/fish/completions
cp completions/loom.fish ~/.config/fish/completions/loom.fish

# Completions are active immediately on next shell session
```

## Features

### Bash
- Main command completion (serve, fetch, spider, search, etc.)
- Subcommand arguments (open/list/close for session, get/set/list for config)
- Option completion (--mode, --provider, --format, etc.)
- Case-insensitive matching

### Zsh
- Full command descriptions in completion menu
- Subcommand suggestions with help text
- Option completion with parameter suggestions
- Intelligent filtering by subcommand

### Fish
- Colored output with command descriptions
- Subcommand completion for complex commands
- Option auto-completion
- Interactive menu selection

## Completion Examples

### Bash
```bash
loom <TAB>                          # Shows all commands
loom fetch <TAB>                    # Shows --option completions
loom fetch --mode <TAB>             # Shows: http stealthy dynamic
loom session <TAB>                  # Shows: open list close
loom cache <TAB>                    # Shows: stats clear
```

### Zsh
```zsh
loom <TAB>                          # Interactive menu with descriptions
loom search --provider <TAB>        # Shows: exa tavily firecrawl brave
loom config <TAB>                   # Shows: get set list
```

### Fish
```fish
loom <TAB>                          # Fish menu with descriptions
loom llm <TAB>                      # Shows: summarize extract classify...
loom deep --depth <TAB>             # Suggests values
```

## Generating Completions

To regenerate completion scripts after CLI changes:

```bash
python scripts/generate_completions.py

# This generates:
# - completions/loom.bash
# - completions/loom.zsh
# - completions/loom.fish
```

## Troubleshooting

### Completions not appearing

**Bash:**
- Reload shell: `source ~/.bashrc`
- Check location: `complete -p loom`

**Zsh:**
- Reload shell: `exec zsh`
- Check fpath: `echo $fpath`
- Rebuild completion cache: `compinit -U`

**Fish:**
- Reload shell: `fish`
- Check: `complete -c loom`
- Clear cache: `rm ~/.cache/fish/fish_history`

### Wrong completions

Ensure only one completion file is loaded. Check:

```bash
# Bash
grep -r "loom" ~/.bash_completion.d/ /etc/bash_completion.d/

# Zsh
grep -r "_loom" ~/.zsh/completions/ /usr/share/zsh/site-functions/

# Fish
ls ~/.config/fish/completions/loom*
```

Remove duplicates if found.

## Updating Completions

When CLI commands change, regenerate and reinstall:

```bash
# Regenerate
python scripts/generate_completions.py

# Reinstall
loom completions install

# Or manually for your shell
bash completions/install.sh bash  # or zsh, fish
```

## Reference

- **Typer Documentation:** https://typer.tiangolo.com/
- **Bash Completion Guide:** https://www.gnu.org/software/bash/manual/html_node/Programmable-Completion.html
- **Zsh Completion:** http://zsh.sourceforge.net/Doc/Release/Completion-System.html
- **Fish Completions:** https://fishshell.com/docs/current/completions.html
