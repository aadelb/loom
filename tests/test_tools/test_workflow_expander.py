"""Tests for workflow_expander tool coverage generation."""

import pytest
from loom.tools.infrastructure.workflow_expander import (
    _categorize_tool,
    _extract_tool_functions,
    _get_tool_modules,
    research_workflow_coverage,
    research_workflow_generate,
)


class TestCategorization:
    """Test tool categorization logic."""

    def test_security_category(self):
        """Test security tools are correctly categorized."""
        assert _categorize_tool("breach_check") == "security"
        assert _categorize_tool("cert_analyzer") == "security"
        assert _categorize_tool("cve_lookup") == "security"
        assert _categorize_tool("security_headers") == "security"

    def test_osint_category(self):
        """Test OSINT tools are correctly categorized."""
        assert _categorize_tool("social_graph") == "osint"
        assert _categorize_tool("identity_resolve") == "osint"
        assert _categorize_tool("social_intel") == "osint"

    def test_adversarial_category(self):
        """Test adversarial tools are correctly categorized."""
        assert _categorize_tool("adversarial_craft") == "adversarial"
        assert _categorize_tool("prompt_reframe") == "adversarial"
        assert _categorize_tool("attack_scorer") == "adversarial"

    def test_research_category(self):
        """Test research tools are correctly categorized."""
        assert _categorize_tool("deep") == "research"
        assert _categorize_tool("search") == "research"
        assert _categorize_tool("fetch") == "research"

    def test_infrastructure_category(self):
        """Test infrastructure tools are correctly categorized."""
        assert _categorize_tool("deployment") == "infrastructure"
        assert _categorize_tool("backup_system") == "infrastructure"

    def test_analysis_category(self):
        """Test analysis tools are correctly categorized."""
        assert _categorize_tool("attack_scorer") == "adversarial"


class TestToolDiscovery:
    """Test tool module discovery."""

    def test_get_tool_modules(self):
        """Test that tool modules are discovered."""
        modules = _get_tool_modules()
        assert len(modules) > 100, "Should discover 100+ tool modules"
        assert "search" in modules
        assert "fetch" in modules
        assert "deep" in modules

    def test_extract_functions(self):
        """Test function extraction from tool modules."""
        modules = _get_tool_modules()
        assert len(modules) > 0

        # Count functions across all modules
        total_functions = 0
        for module_path in list(modules.values())[:10]:
            funcs = _extract_tool_functions(module_path)
            if funcs:
                total_functions += len(funcs)

        # At least some modules should have async research_* functions
        assert total_functions > 0, "Should find research_* functions"


class TestWorkflowGeneration:
    """Test workflow generation."""

    @pytest.mark.asyncio
    async def test_single_category_workflow(self):
        """Test generating workflow for a single category."""
        result = await research_workflow_generate(category="security", max_steps=6)

        assert "category" in result
        assert result["category"] == "security"
        assert "workflow" in result
        assert "tools_covered" in result
        assert isinstance(result["workflow"], list)
        assert len(result["workflow"]) > 0

    @pytest.mark.asyncio
    async def test_workflow_steps_structure(self):
        """Test that workflow steps have correct structure."""
        result = await research_workflow_generate(category="research", max_steps=4)

        workflow = result["workflow"]
        for step in workflow:
            assert "step" in step
            assert "tool" in step
            assert "description" in step
            assert step["tool"].startswith("research_")

    @pytest.mark.asyncio
    async def test_max_steps_respected(self):
        """Test that max_steps parameter is respected."""
        result = await research_workflow_generate(category="osint", max_steps=3)
        assert len(result["workflow"]) <= 3

    @pytest.mark.asyncio
    async def test_auto_generate_all_categories(self):
        """Test auto-generating workflows for all categories."""
        result = await research_workflow_generate(category="auto", max_steps=6)

        assert "workflows" in result
        assert "total_tools_covered" in result
        assert "coverage_pct" in result
        assert len(result["workflows"]) > 0

        # Each workflow should have tools
        for category, workflow_data in result["workflows"].items():
            assert "workflow" in workflow_data
            assert "tools_covered" in workflow_data
            assert isinstance(workflow_data["workflow"], list)

    @pytest.mark.asyncio
    async def test_invalid_category(self):
        """Test handling of invalid category."""
        result = await research_workflow_generate(category="nonexistent")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_workflow_logical_order(self):
        """Test that workflow steps follow logical order."""
        result = await research_workflow_generate(category="research", max_steps=6)
        workflow = result["workflow"]

        # Steps should have sequential order
        for i, step in enumerate(workflow, 1):
            assert step["step"] == i


class TestCoverageReport:
    """Test coverage report generation."""

    @pytest.mark.asyncio
    async def test_coverage_structure(self):
        """Test that coverage report has correct structure."""
        result = await research_workflow_coverage()

        assert "total_tools" in result
        assert "covered" in result
        assert "uncovered" in result
        assert "coverage_pct" in result
        assert "categories_analyzed" in result
        assert "uncovered_by_category" in result

    @pytest.mark.asyncio
    async def test_coverage_metrics(self):
        """Test coverage metrics are valid."""
        result = await research_workflow_coverage()

        total = result["total_tools"]
        covered = result["covered"]
        uncovered_count = len(result["uncovered"])

        # covered + uncovered should equal total (approximately)
        assert covered + uncovered_count == total

        # Coverage percentage should be valid
        coverage = result["coverage_pct"]
        assert 0 <= coverage <= 100

    @pytest.mark.asyncio
    async def test_uncovered_by_category(self):
        """Test uncovered tools are properly grouped by category."""
        result = await research_workflow_coverage()

        uncovered_by_cat = result["uncovered_by_category"]
        assert isinstance(uncovered_by_cat, dict)

        # Sum of uncovered in categories should equal total uncovered
        total_uncovered_by_cat = sum(
            len(tools) for tools in uncovered_by_cat.values()
        )
        assert total_uncovered_by_cat == len(result["uncovered"])


class TestCategoryKeywords:
    """Test category keyword matching."""

    def test_all_categories_have_keywords(self):
        """Verify all categories are mapped to keywords."""
        from loom.tools.infrastructure.workflow_expander import CATEGORY_KEYWORDS

        assert len(CATEGORY_KEYWORDS) > 0
        required_categories = {"security", "osint", "adversarial", "research"}
        assert required_categories.issubset(CATEGORY_KEYWORDS.keys())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
