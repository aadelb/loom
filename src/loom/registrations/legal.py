"""Registration module for UAE/Dubai legal compliance tools."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.legal")


def register_legal_tools(mcp: FastMCP, wrap_tool) -> None:
    """Register UAE/Dubai legal compliance tools."""
    from loom.registrations.tracking import record_failure, record_success

    try:
        from loom.tools.legal.uae_legal import (
            research_uae_commercial_law,
            research_uae_customs,
            research_uae_food_safety,
            research_uae_labor_law,
            research_uae_rera,
            research_uae_tax_compliance,
            research_uae_trade_license,
            research_uae_visa_rules,
        )

        mcp.tool()(wrap_tool(research_uae_labor_law))
        record_success("legal", "research_uae_labor_law")

        mcp.tool()(wrap_tool(research_uae_trade_license))
        record_success("legal", "research_uae_trade_license")

        mcp.tool()(wrap_tool(research_uae_food_safety))
        record_success("legal", "research_uae_food_safety")

        mcp.tool()(wrap_tool(research_uae_visa_rules))
        record_success("legal", "research_uae_visa_rules")

        mcp.tool()(wrap_tool(research_uae_commercial_law))
        record_success("legal", "research_uae_commercial_law")

        mcp.tool()(wrap_tool(research_uae_customs))
        record_success("legal", "research_uae_customs")

        mcp.tool()(wrap_tool(research_uae_rera))
        record_success("legal", "research_uae_rera")

        mcp.tool()(wrap_tool(research_uae_tax_compliance))
        record_success("legal", "research_uae_tax_compliance")

    except Exception as e:
        log.debug("skip uae_legal: %s", e)
        record_failure("legal", "uae_legal", str(e))
