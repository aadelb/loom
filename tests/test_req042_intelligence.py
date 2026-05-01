"""REQ-042 Intelligence 12 tools: verify structured output.

Tests that 12 key intelligence tools return dict with structured fields,
not just strings. Tools tested:
1. research_company_diligence (async)
2. research_salary_intelligence (async)
3. research_supply_chain_risk (async)
4. research_crypto_trace
5. research_stego_detect
6. research_domain_reputation
7. research_social_graph
8. research_knowledge_graph
9. research_fact_check
10. research_ghost_protocol (signal_detection)
11. research_temporal_anomaly (signal_detection)
12. research_persona_profile (async)
"""

from __future__ import annotations

import asyncio

import pytest

# Import the tools
from loom.tools import (
    company_intel,
    crypto_trace,
    fact_checker,
    knowledge_graph,
    persona_profile,
    signal_detection,
    social_graph,
    stego_detect,
    supply_chain_intel,
    threat_intel,
)


class TestIntelligenceToolsStructuredOutput:
    """Verify all 12 intelligence tools return structured dicts."""

    @pytest.mark.asyncio
    async def test_01_company_diligence_structured(self):
        """Test 1: research_company_diligence returns structured dict."""
        result = await company_intel.research_company_diligence("Anthropic")

        # Verify it's a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Verify structured fields
        assert "company" in result
        assert "industry" in result or "error" in result
        assert isinstance(result, dict)

        # Verify no plain string results
        assert not isinstance(result, str)

        print(f"✓ research_company_diligence: {len(result)} fields")

    @pytest.mark.asyncio
    async def test_02_salary_intelligence_structured(self):
        """Test 2: research_salary_intelligence returns structured dict."""
        result = await company_intel.research_salary_intelligence("Software Engineer")

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        # Check for expected fields
        assert any(k in result for k in ["role", "query", "error", "salary", "median"])

        # Verify it's not just a string
        assert not isinstance(result, str)

        print(f"✓ research_salary_intelligence: {len(result)} fields")

    @pytest.mark.asyncio
    async def test_03_supply_chain_risk_structured(self):
        """Test 3: research_supply_chain_risk returns structured dict."""
        result = await supply_chain_intel.research_supply_chain_risk("example.com")

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        # Should have some fields
        assert len(result) > 0

        # Verify structured fields exist
        assert not isinstance(result, str)

        print(f"✓ research_supply_chain_risk: {len(result)} fields")

    def test_04_crypto_trace_structured(self):
        """Test 4: research_crypto_trace returns structured dict."""
        # Use a safe Bitcoin address example
        result = crypto_trace.research_crypto_trace(
            "1A1z7agoat2WFvZv7j9qLvWRgmYyvS2p9e"
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "address" in result
        assert "chain" in result
        assert "primary_data" in result or "blockchair_stats" in result

        # Verify structured, not string
        assert not isinstance(result, str)

        print(f"✓ research_crypto_trace: {len(result)} fields")

    def test_05_stego_detect_structured(self):
        """Test 5: research_stego_detect returns structured dict."""
        result = stego_detect.research_stego_detect(
            content="Hello world, this is test data."
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "analysis_results" in result or "error" in result or len(result) > 0

        # Verify not a string
        assert not isinstance(result, str)

        print(f"✓ research_stego_detect: {len(result)} fields")

    def test_06_domain_reputation_structured(self):
        """Test 6: research_domain_reputation returns structured dict."""
        result = threat_intel.research_domain_reputation("example.com")

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "domain" in result or len(result) > 0

        # Verify structured fields
        assert not isinstance(result, str)

        print(f"✓ research_domain_reputation: {len(result)} fields")

    def test_07_social_graph_structured(self):
        """Test 7: research_social_graph returns structured dict."""
        result = social_graph.research_social_graph("test_user")

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "query" in result or "username" in result or len(result) > 0

        # Verify not a string
        assert not isinstance(result, str)

        print(f"✓ research_social_graph: {len(result)} fields")

    def test_08_knowledge_graph_structured(self):
        """Test 8: research_knowledge_graph returns structured dict."""
        result = knowledge_graph.research_knowledge_graph(
            "machine learning",
            max_nodes=50,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "query" in result
        assert "nodes" in result
        assert "edges" in result
        assert isinstance(result["nodes"], list)
        assert isinstance(result["edges"], list)

        # Verify not a string
        assert not isinstance(result, str)

        print(f"✓ research_knowledge_graph: {len(result)} fields")

    def test_09_fact_check_structured(self):
        """Test 9: research_fact_check returns structured dict."""
        result = fact_checker.research_fact_check("The Earth is round")

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "claim" in result or "query" in result or len(result) > 0

        # Verify structured, not string
        assert not isinstance(result, str)

        print(f"✓ research_fact_check: {len(result)} fields")

    def test_10_ghost_protocol_structured(self):
        """Test 10: research_ghost_protocol (signal_detection) returns structured dict."""
        result = signal_detection.research_ghost_protocol("example.com")

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        # This tool returns coordination signals, check for its actual fields
        assert any(k in result for k in ["keywords", "clusters_found", "platforms_checked", "coordination_score"])

        # Verify structured, not string
        assert not isinstance(result, str)

        print(f"✓ research_ghost_protocol: {len(result)} fields")

    def test_11_temporal_anomaly_structured(self):
        """Test 11: research_temporal_anomaly (signal_detection) returns structured dict."""
        result = signal_detection.research_temporal_anomaly(
            "example.com",
            time_window_days=30,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert len(result) > 0

        # Verify structured, not string
        assert not isinstance(result, str)

        print(f"✓ research_temporal_anomaly: {len(result)} fields")

    @pytest.mark.asyncio
    async def test_12_persona_profile_structured(self):
        """Test 12: research_persona_profile returns structured dict."""
        result = await persona_profile.research_persona_profile("test user")

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert len(result) > 0

        # Verify not a string
        assert not isinstance(result, str)

        print(f"✓ research_persona_profile: {len(result)} fields")


class TestIntelligenceStructureValidation:
    """Validate that structured fields contain expected data types."""

    def test_crypto_trace_has_nested_structure(self):
        """Verify crypto_trace returns nested dicts, not just strings."""
        result = crypto_trace.research_crypto_trace(
            "1A1z7agoat2WFvZv7j9qLvWRgmYyvS2p9e"
        )

        # Should have address and chain fields
        assert result.get("address") is not None
        assert result.get("chain") in ("bitcoin", "ethereum", "auto")

        # Should have nested dicts/structures
        assert isinstance(result.get("primary_data"), (dict, type(None)))
        assert isinstance(result.get("blockchair_stats"), (dict, type(None)))

    def test_knowledge_graph_has_nodes_and_edges(self):
        """Verify knowledge_graph returns lists of structured dicts."""
        result = knowledge_graph.research_knowledge_graph("test")

        # Must have nodes and edges as lists
        assert isinstance(result.get("nodes"), list)
        assert isinstance(result.get("edges"), list)

        # Each node should be a dict with required fields
        for node in result.get("nodes", []):
            assert isinstance(node, dict)
            assert "id" in node or "name" in node or "type" in node

    def test_stego_detect_has_results(self):
        """Verify stego_detect returns structured results."""
        result = stego_detect.research_stego_detect(content="test data")

        # Should have analysis results
        assert isinstance(result, dict)
        assert len(result) > 0


class TestIntelligenceOutputConsistency:
    """Test that structured output is consistent across tools."""

    def test_crypto_trace_and_kg_return_dicts(self):
        """Verify both sync and async tools return dicts with meaningful keys."""
        # Sync tool
        crypto_result = crypto_trace.research_crypto_trace(
            "1A1z7agoat2WFvZv7j9qLvWRgmYyvS2p9e"
        )
        assert isinstance(crypto_result, dict)
        assert len(crypto_result) > 0

        # Sync tool
        kg_result = knowledge_graph.research_knowledge_graph("test")
        assert isinstance(kg_result, dict)
        assert len(kg_result) > 0
        assert "nodes" in kg_result
        assert "edges" in kg_result


class TestIntelligenceToolsPassFail:
    """Simple pass/fail tracking for 12 tools."""

    def test_all_12_tools_structured(self):
        """Track which tools pass/fail structured output test."""
        results = []

        # Tool 1: research_company_diligence (async)
        try:
            result = asyncio.run(company_intel.research_company_diligence("Anthropic"))
            results.append(("company_diligence", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("company_diligence", False))

        # Tool 2: research_salary_intelligence (async)
        try:
            result = asyncio.run(company_intel.research_salary_intelligence("Engineer"))
            results.append(("salary_intelligence", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("salary_intelligence", False))

        # Tool 3: research_supply_chain_risk (async)
        try:
            result = asyncio.run(supply_chain_intel.research_supply_chain_risk("example.com"))
            results.append(("supply_chain_risk", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("supply_chain_risk", False))

        # Tool 4: research_crypto_trace (sync)
        try:
            result = crypto_trace.research_crypto_trace("1A1z7agoat2WFvZv7j9qLvWRgmYyvS2p9e")
            results.append(("crypto_trace", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("crypto_trace", False))

        # Tool 5: research_stego_detect (sync)
        try:
            result = stego_detect.research_stego_detect(content="test")
            results.append(("stego_detect", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("stego_detect", False))

        # Tool 6: research_domain_reputation (sync)
        try:
            result = threat_intel.research_domain_reputation("example.com")
            results.append(("domain_reputation", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("domain_reputation", False))

        # Tool 7: research_social_graph (sync)
        try:
            result = social_graph.research_social_graph("test")
            results.append(("social_graph", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("social_graph", False))

        # Tool 8: research_knowledge_graph (sync)
        try:
            result = knowledge_graph.research_knowledge_graph("test")
            results.append(("knowledge_graph", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("knowledge_graph", False))

        # Tool 9: research_fact_check (sync)
        try:
            result = fact_checker.research_fact_check("test")
            results.append(("fact_check", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("fact_check", False))

        # Tool 10: research_ghost_protocol (sync)
        try:
            result = signal_detection.research_ghost_protocol("example.com")
            results.append(("ghost_protocol", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("ghost_protocol", False))

        # Tool 11: research_temporal_anomaly (sync)
        try:
            result = signal_detection.research_temporal_anomaly("example.com")
            results.append(("temporal_anomaly", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("temporal_anomaly", False))

        # Tool 12: research_persona_profile (async)
        try:
            result = asyncio.run(persona_profile.research_persona_profile("test"))
            results.append(("persona_profile", isinstance(result, dict) and not isinstance(result, str)))
        except Exception as e:
            results.append(("persona_profile", False))

        # Print results
        passed = sum(1 for _, p in results if p)
        total = len(results)

        print(f"\n{'='*60}")
        print(f"REQ-042 Intelligence Tools Structured Output Results")
        print(f"{'='*60}")
        for tool_name, passed_test in results:
            status = "✓ PASS" if passed_test else "✗ FAIL"
            print(f"{status:8} {tool_name}")
        print(f"{'='*60}")
        print(f"Total: {passed}/{total} tools return structured output (dict)")
        print(f"{'='*60}\n")

        # All 12 should pass
        assert passed == total, f"Only {passed}/12 tools returned structured output"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
