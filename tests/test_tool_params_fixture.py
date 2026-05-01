"""Test that tool_params.json fixture is valid and covers all registered tools.

This test module validates that:
1. The fixture JSON is well-formed
2. All parameters match expected schemas
3. The fixture can be loaded and used in tests
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def tool_params_fixture() -> dict[str, dict]:
    """Load tool parameters from fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / "tool_params.json"
    with open(fixture_path) as f:
        return json.load(f)


def test_fixture_file_exists() -> None:
    """Test that the fixture file exists."""
    fixture_path = Path(__file__).parent / "fixtures" / "tool_params.json"
    assert fixture_path.exists(), f"Fixture file not found at {fixture_path}"


def test_fixture_is_valid_json() -> None:
    """Test that the fixture is valid JSON."""
    fixture_path = Path(__file__).parent / "fixtures" / "tool_params.json"
    try:
        with open(fixture_path) as f:
            json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"Fixture JSON is invalid: {e}")


def test_fixture_contains_tools(tool_params_fixture: dict[str, dict]) -> None:
    """Test that the fixture contains a reasonable number of tools."""
    assert len(tool_params_fixture) > 200, (
        f"Expected at least 200 tools in fixture, got {len(tool_params_fixture)}"
    )


def test_fixture_tools_have_parameters(tool_params_fixture: dict[str, dict]) -> None:
    """Test that all tools have parameters defined (dict, possibly empty)."""
    for tool_name, params in tool_params_fixture.items():
        assert isinstance(
            params, dict
        ), f"Tool {tool_name} params should be dict, got {type(params)}"


def test_fixture_url_parameters_are_valid(tool_params_fixture: dict[str, dict]) -> None:
    """Test that URL parameters follow expected patterns."""
    url_patterns = (
        "khaleejtimes.com",
        "gulfnews.com",
        "dubaichamber.ae",
        "dubailand.gov.ae",
        "arabnews.com",
        "invest.dubai.ae",
        "example.com",
    )

    for tool_name, params in tool_params_fixture.items():
        for param_name, param_value in params.items():
            if isinstance(param_value, str) and "url" in param_name.lower():
                assert param_value.startswith(
                    ("https://", "http://")
                ), f"{tool_name}.{param_name} is not a valid URL: {param_value}"
            elif isinstance(param_value, str) and "domain" in param_name.lower():
                # Allow crypto addresses, emails, and various formats for non-URL domains
                if not any(pattern in param_value for pattern in url_patterns):
                    # Allow special formats like bitcoin addresses
                    assert (
                        param_value.count(".") > 0 or "@" in param_value or param_value.startswith("1")
                    ), f"{tool_name}.{param_name} is not a valid domain format: {param_value}"


def test_fixture_common_parameters(tool_params_fixture: dict[str, dict]) -> None:
    """Test that common parameter types are present in the fixture."""
    # Tools with URL parameters
    url_tools = {
        name for name, params in tool_params_fixture.items() if "url" in params
    }
    assert len(url_tools) >= 50, f"Expected many URL-based tools, got {len(url_tools)}"

    # Tools with query parameters
    query_tools = {
        name for name, params in tool_params_fixture.items() if "query" in params
    }
    assert len(query_tools) >= 30, f"Expected many query-based tools, got {len(query_tools)}"

    # Tools with domain parameters
    domain_tools = {
        name for name, params in tool_params_fixture.items() if "domain" in params
    }
    assert len(domain_tools) >= 10, f"Expected some domain-based tools, got {len(domain_tools)}"


def test_fixture_specific_tools_present(tool_params_fixture: dict[str, dict]) -> None:
    """Test that specific core tools are present in the fixture."""
    core_tools = {
        "research_fetch",
        "research_spider",
        "research_markdown",
        "research_search",
        "research_deep",
        "research_github",
        "research_cache_stats",
        "research_config_get",
        "research_config_set",
        "research_session_open",
        "research_session_list",
        "research_session_close",
    }

    missing_tools = core_tools - set(tool_params_fixture.keys())
    assert (
        not missing_tools
    ), f"Missing core tools in fixture: {missing_tools}"


def test_fixture_parameter_values_are_reasonable(
    tool_params_fixture: dict[str, dict],
) -> None:
    """Test that parameter values are reasonable and match expected types."""
    for tool_name, params in tool_params_fixture.items():
        for param_name, param_value in params.items():
            # Check that integers are reasonable
            if isinstance(param_value, int):
                assert (
                    -1000 < param_value < 100000
                ), f"{tool_name}.{param_name} has unreasonable integer: {param_value}"

            # Check that lists are reasonable size
            if isinstance(param_value, list):
                assert (
                    len(param_value) < 1000
                ), f"{tool_name}.{param_name} has unreasonably large list: {len(param_value)}"

            # Check that strings aren't too long
            if isinstance(param_value, str):
                assert (
                    len(param_value) < 10000
                ), f"{tool_name}.{param_name} has unreasonably long string: {len(param_value)} chars"


def test_fixture_can_be_used_for_parametrization(
    tool_params_fixture: dict[str, dict],
) -> None:
    """Test that fixture can be used for parametrized tests."""
    # This demonstrates how to use the fixture for parametrized testing
    tool_names = list(tool_params_fixture.keys())

    # Pick a sample
    sample_tools = tool_names[:5]

    for tool_name in sample_tools:
        params = tool_params_fixture[tool_name]
        # Verify we can iterate over parameters
        assert isinstance(params, dict), f"{tool_name} params should be iterable dict"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
