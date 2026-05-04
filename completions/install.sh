#!/bin/bash
# Install shell completions for loom CLI
# Usage: ./completions/install.sh [bash|zsh|fish|auto]

set -e

SHELL_TYPE="${1:-auto}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect shell if not specified
if [ "$SHELL_TYPE" = "auto" ]; then
    SHELL_BASENAME=$(basename "$SHELL" | sed 's/-$//')
    case "$SHELL_BASENAME" in
        bash)
            SHELL_TYPE="bash"
            ;;
        zsh)
            SHELL_TYPE="zsh"
            ;;
        fish)
            SHELL_TYPE="fish"
            ;;
        *)
            echo "Error: Could not detect shell. Please specify bash, zsh, or fish"
            exit 1
            ;;
    esac
    echo "Detected shell: $SHELL_TYPE"
fi

case "$SHELL_TYPE" in
    bash)
        COMPLETION_FILE="$SCRIPT_DIR/loom.bash"
        if [ -n "$BASH_COMPLETION_USER_DIR" ]; then
            INSTALL_DIR="$BASH_COMPLETION_USER_DIR"
        elif [ -d ~/.bash_completion.d ]; then
            INSTALL_DIR="$HOME/.bash_completion.d"
        elif [ -d /etc/bash_completion.d ]; then
            INSTALL_DIR="/etc/bash_completion.d"
            NEEDS_SUDO=true
        else
            INSTALL_DIR="$HOME/.bash_completion.d"
            mkdir -p "$INSTALL_DIR"
        fi
        INSTALL_TARGET="$INSTALL_DIR/loom"
        ;;
    zsh)
        COMPLETION_FILE="$SCRIPT_DIR/loom.zsh"
        if [ -n "$fpath" ]; then
            INSTALL_DIR="${fpath[1]}"
        elif [ -d /usr/share/zsh/site-functions ]; then
            INSTALL_DIR="/usr/share/zsh/site-functions"
            NEEDS_SUDO=true
        else
            INSTALL_DIR="$HOME/.zsh/completions"
            mkdir -p "$INSTALL_DIR"
        fi
        INSTALL_TARGET="$INSTALL_DIR/_loom"
        ;;
    fish)
        COMPLETION_FILE="$SCRIPT_DIR/loom.fish"
        INSTALL_DIR="$HOME/.config/fish/completions"
        INSTALL_TARGET="$INSTALL_DIR/loom.fish"
        mkdir -p "$INSTALL_DIR"
        NEEDS_SUDO=false
        ;;
    *)
        echo "Error: Unknown shell '$SHELL_TYPE'. Use bash, zsh, or fish"
        exit 1
        ;;
esac

if [ ! -f "$COMPLETION_FILE" ]; then
    echo "Error: Completion file not found: $COMPLETION_FILE"
    echo "Run 'python scripts/generate_completions.py' first"
    exit 1
fi

# Check if we need sudo
if [ "$NEEDS_SUDO" = true ]; then
    if ! sudo -n true 2>/dev/null; then
        echo "Installation requires sudo. Please enter your password:"
        sudo cp "$COMPLETION_FILE" "$INSTALL_TARGET"
    else
        sudo cp "$COMPLETION_FILE" "$INSTALL_TARGET"
    fi
else
    cp "$COMPLETION_FILE" "$INSTALL_TARGET"
fi

chmod 644 "$INSTALL_TARGET"

echo "✓ Installed $SHELL_TYPE completions to: $INSTALL_TARGET"

# Print next steps
case "$SHELL_TYPE" in
    bash)
        echo ""
        echo "To enable completions, reload your shell:"
        echo "  source ~/.bashrc"
        echo "or open a new terminal"
        ;;
    zsh)
        echo ""
        echo "To enable completions, reload your shell:"
        echo "  exec zsh"
        echo "or add this to your ~/.zshrc if not already there:"
        echo "  autoload -Uz compinit && compinit"
        ;;
    fish)
        echo ""
        echo "Completions are active immediately!"
        ;;
esac
