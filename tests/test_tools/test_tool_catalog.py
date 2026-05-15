"""Unit tests for tool_catalog module."""

import pytest
import loom.tools.infrastructure.tool_catalog


@pytest.mark.unit
def test_tool_registry_exists():
    """Verify tool registry is populated."""
    assert len(tool_catalog.TOOL_REGISTRY) > 0
    assert "research_fetch" in tool_catalog.TOOL_REGISTRY


@pytest.mark.unit
def test_tool_metadata_structure():
    """Verify each tool has required metadata fields."""
    required_fields = {
        "category",
        "subcategory",
        "description",
        "capabilities",
        "input_types",
        "output_types",
        "dependencies",
        "connects_to",
    }

    for tool_name, metadata in tool_catalog.TOOL_REGISTRY.items():
        assert isinstance(metadata, dict), f"{tool_name} metadata is not dict"
        for field in required_fields:
            assert field in metadata, f"{tool_name} missing field: {field}"
            assert isinstance(metadata[field], (list, str, dict)), f"{tool_name}.{field} bad type"


@pytest.mark.unit
def test_categories_defined():
    """Verify all categories are defined."""
    assert len(tool_catalog.TOOL_CATEGORIES) > 0

    for category_name, category_info in tool_catalog.TOOL_CATEGORIES.items():
        assert "description" in category_info
        assert "subcategories" in category_info
        assert isinstance(category_info["subcategories"], dict)


@pytest.mark.unit
def test_tool_categories_valid():
    """Verify all tools reference valid categories."""
    valid_categories = set(tool_catalog.TOOL_CATEGORIES.keys())

    for tool_name, metadata in tool_catalog.TOOL_REGISTRY.items():
        category = metadata["category"]
        assert category in valid_categories, f"{tool_name} references unknown category: {category}"


@pytest.mark.unit
def test_capabilities_exist():
    """Verify capabilities are defined."""
    assert len(tool_catalog.CAPABILITIES) > 0
    assert "accepts_url" in tool_catalog.CAPABILITIES
    assert "returns_structured" in tool_catalog.CAPABILITIES


@pytest.mark.unit
def test_tool_capabilities_valid():
    """Verify tool capabilities reference defined capabilities."""
    valid_capabilities = set(tool_catalog.CAPABILITIES.keys())

    for tool_name, metadata in tool_catalog.TOOL_REGISTRY.items():
        capabilities = metadata["capabilities"]
        for cap in capabilities:
            assert cap in valid_capabilities, f"{tool_name} references unknown capability: {cap}"


@pytest.mark.unit
def test_tool_connections_valid():
    """Verify tool connections reference real tools."""
    valid_tools = set(tool_catalog.TOOL_REGISTRY.keys())

    for tool_name, metadata in tool_catalog.TOOL_REGISTRY.items():
        connects_to = metadata["connects_to"]
        for target in connects_to:
            assert target in valid_tools, f"{tool_name} connects to non-existent tool: {target}"


@pytest.mark.unit
async def test_research_tool_catalog():
    """Test research_tool_catalog function."""
    # Test without filters
    result = await tool_catalog.research_tool_catalog()
    assert "tools" in result
    assert "total_count" in result
    assert len(result["tools"]) > 0

    # Test with category filter
    result = await tool_catalog.research_tool_catalog(category="scraping")
    assert all(tool["category"] == "scraping" for tool in result["tools"])

    # Test with capability filter
    result = await tool_catalog.research_tool_catalog(capability="accepts_url")
    assert all("accepts_url" in tool["capabilities"] for tool in result["tools"])


@pytest.mark.unit
async def test_research_tool_graph():
    """Test research_tool_graph function."""
    result = await tool_catalog.research_tool_graph()

    assert "nodes" in result
    assert "edges" in result
    assert "clusters" in result
    assert result["node_count"] > 0
    assert "cluster_count" > 0

    # Verify edges reference real nodes
    node_ids = {node["id"] for node in result["nodes"]}
    for edge in result["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


@pytest.mark.unit
async def test_research_tool_pipeline():
    """Test research_tool_pipeline function."""
    # Test domain research goal
    result = await tool_catalog.research_tool_pipeline("find domain OSINT")
    assert "goal" in result
    assert "pipeline" in result
    assert "success" in result

    # If successful, verify pipeline has steps
    if result["success"]:
        assert len(result["pipeline"]) > 0
        for step in result["pipeline"]:
            assert "step" in step
            assert "tool" in step
            assert "description" in step


@pytest.mark.unit
async def test_research_tool_standalone():
    """Test research_tool_standalone function."""
    # Test existing tool
    result = await tool_catalog.research_tool_standalone("research_fetch")
    assert "name" in result
    assert "description" in result
    assert "category" in result
    assert "capabilities" in result

    # Test non-existent tool
    result = await tool_catalog.research_tool_standalone("nonexistent_tool")
    assert "error" in result


@pytest.mark.unit
def test_tool_examples():
    """Verify core tools have proper metadata."""
    core_tools = ["research_fetch", "research_search", "research_deep", "research_knowledge_graph"]

    for tool_name in core_tools:
        assert tool_name in tool_catalog.TOOL_REGISTRY
        tool = tool_catalog.TOOL_REGISTRY[tool_name]
        assert tool["description"]
        assert tool["capabilities"]
        assert tool["input_types"]
        assert tool["output_types"]
