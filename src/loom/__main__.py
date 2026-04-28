"""Loom entry point for 'python -m loom' invocation.

Delegates to the Typer CLI app.
"""

from loom.cli import app

if __name__ == "__main__":
    app()
