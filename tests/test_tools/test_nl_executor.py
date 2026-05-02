"""Tests for Natural Language Tool Executor (nl_executor)."""

from __future__ import annotations

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from loom.tools import nl_executor


class TestNLExecutor:
    """Test Natural Language Tool Executor."""

    def test_extract_action_security(self):
        """Test action extraction for security category."""
        action = nl_executor._extract_action("scan example.com for headers")
        assert action == "security"

    def test_extract_action_search(self):
        """Test action extraction for search category."""
        action = nl_executor._extract_action("search for python async patterns")
        assert action == "search"

    def test_extract_action_analysis(self):
        """Test action extraction for analysis category."""
        action = nl_executor._extract_action("analyze the security of this domain")
        assert action == "analysis"

    def test_extract_action_monitoring(self):
        """Test action extraction for monitoring category."""
        action = nl_executor._extract_action("monitor changes on github")
        assert action == "monitoring"

    def test_extract_action_none(self):
        """Test action extraction with no recognized action."""
        action = nl_executor._extract_action("hello world")
        assert action is None

    def test_extract_url_with_https(self):
        """Test URL extraction with https."""
        url = nl_executor._extract_url("scan https://example.com for headers")
        assert url == "https://example.com"

    def test_extract_url_domain_only(self):
        """Test URL extraction with domain only."""
        url = nl_executor._extract_url("check example.com for vulnerabilities")
        assert url == "example.com"

    def test_extract_url_none(self):
        """Test URL extraction when no URL present."""
        url = nl_executor._extract_url("search for python documentation")
        assert url is None

    def test_extract_query(self):
        """Test query extraction."""
        query = nl_executor._extract_query(
            "search for async python patterns",
            "search"
        )
        assert "async python patterns" in query

    def test_extract_number_default(self):
        """Test number extraction with default."""
        num = nl_executor._extract_number("search for results")
        assert num == 10

    def test_extract_number_explicit(self):
        """Test number extraction with explicit number."""
        num = nl_executor._extract_number("search and get 25 results")
        assert num == 25

    def test_extract_model_name_gpt(self):
        """Test model name extraction for GPT."""
        model = nl_executor._extract_model_name("analyze using gpt-4")
        assert model == "gpt-4"

    def test_extract_model_name_claude(self):
        """Test model name extraction for Claude."""
        model = nl_executor._extract_model_name("reframe using claude")
        assert model == "claude"

    def test_extract_model_name_none(self):
        """Test model name extraction when no model specified."""
        model = nl_executor._extract_model_name("search the web")
        assert model is None

    def test_select_tool_security(self):
        """Test tool selection for security category."""
        tool = nl_executor._select_tool("security", "check headers", None)
        assert "security" in tool or "headers" in tool

    def test_select_tool_search(self):
        """Test tool selection for search category."""
        tool = nl_executor._select_tool("search", "search for results", None)
        assert tool in nl_executor.TOOL_CATEGORIES.get("search", [])

    def test_tool_categories_structure(self):
        """Test TOOL_CATEGORIES has required structure."""
        assert "security" in nl_executor.TOOL_CATEGORIES
        assert "search" in nl_executor.TOOL_CATEGORIES
        assert "analysis" in nl_executor.TOOL_CATEGORIES
        assert "monitoring" in nl_executor.TOOL_CATEGORIES
        assert "reframing" in nl_executor.TOOL_CATEGORIES
        assert "export" in nl_executor.TOOL_CATEGORIES

    def test_action_to_category_coverage(self):
        """Test ACTION_TO_CATEGORY has reasonable coverage."""
        assert len(nl_executor.ACTION_TO_CATEGORY) >= 6

    @pytest.mark.asyncio
    async def test_research_do_invalid_instruction(self):
        """Test research_do with invalid instruction."""
        result = await nl_executor.research_do("xyz abc 123 invalid")
        assert result["success"] is False
        assert "instruction" in result
        assert "error" in result["result"].lower() or "not found" in result["result"].lower()

    @pytest.mark.asyncio
    async def test_research_do_response_structure(self):
        """Test research_do returns proper response structure."""
        result = await nl_executor.research_do("search github")
        assert isinstance(result, dict)
        assert "instruction" in result
        assert "tool_selected" in result
        assert "params_used" in result
        assert "success" in result
        assert isinstance(result["success"], bool)
        assert "result" in result
        assert "execution_ms" in result
        assert isinstance(result["execution_ms"], int)
        assert "alternatives" in result
        assert isinstance(result["alternatives"], list)
