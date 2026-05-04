"""Gateway launcher - creates and exports FastMCP app for uvicorn."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

from gateway.server import create_gateway_app

app = create_gateway_app()
