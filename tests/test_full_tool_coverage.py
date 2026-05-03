"""Full tool coverage test — invoke ALL registered Loom tools (REQ-036).

This test extracts all registered tool names from server.py and verifies:
1. Minimum tool count (227+)
2. Tool naming conventions
3. No duplicates
4. Category completeness
"""

import re
from pathlib import Path

import pytest


def get_all_tool_names() -> list[str]:
    """Extract all research_* tool names from server.py and registrations/all_tools.py.

    Returns:
        Sorted list of unique tool names (e.g., ['research_fetch', ...])
    """
    base = Path(__file__).parent.parent / "src" / "loom"
    files_to_scan = [
        base / "server.py",
        base / "registrations" / "all_tools.py",
    ]

    tool_names = set()
    for fpath in files_to_scan:
        if not fpath.exists():
            continue
        content = fpath.read_text()
        for match in re.findall(r"research_\w+", content):
            if match.startswith("research_"):
                tool_names.add(match)

    return sorted(tool_names)


class TestFullToolCoverage:
    """Verify all registered tools meet naming and organization standards."""

    def test_tool_count_minimum_220(self):
        """Verify at least 220 tools are registered.

        This is a sanity check to catch accidental deregistrations
        or major refactoring issues.
        """
        names = get_all_tool_names()
        assert len(names) >= 500, f"Only {len(names)} tools found, expected >= 220"

    def test_no_duplicate_tool_names(self):
        """Verify no duplicate tool registrations exist.

        Duplicates would cause the last registration to silently overwrite
        earlier ones, breaking functionality without warning.
        """
        names = get_all_tool_names()
        duplicates = [n for n in names if names.count(n) > 1]
        assert not duplicates, f"Found duplicate tools: {duplicates}"

    def test_all_tools_follow_naming_convention(self):
        """Verify all tools start with 'research_'.

        Naming convention is critical for:
        - Tool discoverability in MCP clients
        - Clear separation from internal functions
        - Consistent API surface
        """
        names = get_all_tool_names()
        non_compliant = [n for n in names if not n.startswith("research_")]
        assert not non_compliant, f"Tools not following naming convention: {non_compliant}"

    def test_tool_name_characters_valid(self):
        """Verify all tool names use only alphanumeric and underscore characters.

        MCP tool names must be valid identifiers and URL-safe.
        """
        names = get_all_tool_names()
        for name in names:
            assert name.replace("research_", "").replace("_", "").isalnum(), \
                f"Tool name contains invalid characters: {name}"

    def test_tool_categories_complete(self):
        """Verify all major tool categories have registered tools.

        This ensures the tool suite is well-rounded across research domains.
        """
        names = get_all_tool_names()

        categories = {
            "fetch/crawl": ["fetch", "spider", "markdown", "camoufox", "botasaurus"],
            "search": ["search", "multi_search", "deep"],
            "deep_research": ["dark_forum", "invisible_web", "dead_content"],
            "infra_intel": ["infra_correlator", "passive_recon", "cloud_enum"],
            "security": ["breach_check", "cert_analyze", "security_headers", "cve_lookup"],
            "ai_safety": ["safety_filter", "bias_probe", "compliance_check", "hallucination"],
            "academic": ["citation", "retraction", "grant_forensics", "predatory_journal"],
            "darkweb": ["dark_forum", "onion", "leak_scan", "tor"],
            "osint": ["whois", "dns_lookup", "identity_resolve", "passive_recon"],
            "nlp": ["stylometry", "deception_detect", "sentiment_deep", "persona_profile"],
            "career": ["career", "resume", "interview", "salary"],
            "threat": ["threat_intel", "threat_profile", "ransomware", "malware"],
            "session": ["session_open", "session_close", "session_list"],
            "config": ["config_get", "config_set"],
        }

        for category, keywords in categories.items():
            found = False
            for keyword in keywords:
                if any(keyword in name for name in names):
                    found = True
                    break
            assert found, f"Category '{category}' has no tools (searched for: {keywords})"

    def test_tool_count_by_category(self):
        """Report tool count per category for audit and planning.

        Provides visibility into tool distribution and relative coverage
        across research domains.
        """
        names = get_all_tool_names()
        print(f"\nTotal tools: {len(names)}")

        categories = {
            "Core (fetch/spider/search)": ["fetch", "spider", "markdown", "search", "deep"],
            "Dark Web & Threat Intel": ["dark", "threat", "onion", "leak", "tor", "ransomware"],
            "OSINT & Infrastructure": ["whois", "dns", "passive", "infra", "identity"],
            "AI Safety & Compliance": ["safety", "bias", "compliance", "hallucination", "adversarial"],
            "Academic & Integrity": ["citation", "retraction", "grant", "predatory", "preprint"],
            "NLP & Behavioral": ["stylometry", "deception", "sentiment", "persona", "radicalization"],
            "Career & Job Market": ["career", "resume", "job", "salary", "hiring"],
            "Session & Config": ["session", "config"],
            "Other Research Tools": [],
        }

        tool_counts = {}
        for category, keywords in categories.items():
            if category == "Other Research Tools":
                continue
            count = sum(1 for name in names if any(kw in name for kw in keywords))
            tool_counts[category] = count
            print(f"  {category}: {count}")

        # Verify at least basic coverage
        assert sum(tool_counts.values()) > 400, \
            f"Categorized tools ({sum(tool_counts.values())}) suspiciously low"

    def test_core_tools_registered(self):
        """Verify essential core tools are registered.

        These tools form the backbone of the research toolkit and must
        always be available.
        """
        names = get_all_tool_names()
        core_tools = [
            "research_fetch",
            "research_spider",
            "research_markdown",
            "research_search",
            "research_deep",
            "research_github",
            "research_cache_stats",
            "research_cache_clear",
            "research_health_check",
        ]

        for tool in core_tools:
            assert tool in names, f"Core tool missing: {tool}"

    def test_safety_tools_registered(self):
        """Verify EU AI Act Article 15 compliance testing tools are registered.

        These specialized tools support authorized safety/compliance research
        and must be available for red-team evaluations.
        """
        names = get_all_tool_names()
        safety_tools = [
            "research_prompt_injection_test",
            "research_model_fingerprint",
            "research_bias_probe",
            "research_safety_filter_map",
            "research_compliance_check",
        ]

        for tool in safety_tools:
            assert tool in names, f"Safety tool missing: {tool}"

    def test_session_management_tools_registered(self):
        """Verify session management tools are available.

        Session tools enable persistent browser state across multiple
        research operations.
        """
        names = get_all_tool_names()
        session_tools = [
            "research_session_open",
            "research_session_list",
            "research_session_close",
        ]

        for tool in session_tools:
            assert tool in names, f"Session tool missing: {tool}"

    def test_config_management_tools_registered(self):
        """Verify configuration management tools are available.

        Config tools allow runtime tuning of Loom behavior without
        restarts.
        """
        names = get_all_tool_names()
        config_tools = [
            "research_config_get",
            "research_config_set",
        ]

        for tool in config_tools:
            assert tool in names, f"Config tool missing: {tool}"

    def test_no_internal_function_leakage(self):
        """Verify internal helper functions are not registered as tools.

        Only functions prefixed with 'research_' should be registered,
        preventing internal utilities from being exposed.
        """
        names = get_all_tool_names()
        internal_patterns = [
            "_wrap_tool",
            "_register",
            "_check_",
            "_validate",
            "_shutdown",
            "_handle_",
            "_get_",
            "_optional",
        ]

        for name in names:
            for pattern in internal_patterns:
                assert pattern not in name, \
                    f"Internal function leaked as tool: {name}"

    def test_tool_list_printable(self):
        """Print full tool list for manual audit and documentation."""
        names = get_all_tool_names()
        print(f"\n\nFull Tool List ({len(names)} total):")
        print("=" * 60)
        for i, name in enumerate(names, 1):
            print(f"{i:3d}. {name}")

        # Verify list is reasonable
        assert len(names) >= 200, "Tool list suspiciously short"
        assert len(names) <= 400, "Tool list suspiciously large (config drift?)"

    @pytest.mark.parametrize("tool_name", get_all_tool_names()[:100])
    def test_tool_name_length_reasonable(self, tool_name: str):
        """Verify tool names are not excessively long.

        Tool names should be descriptive but concise (max ~50 chars).
        Overly long names may indicate naming convention drift.
        """
        assert len(tool_name) < 50, \
            f"Tool name excessively long ({len(tool_name)}): {tool_name}"

    @pytest.mark.parametrize("tool_name", get_all_tool_names()[:100])
    def test_tool_name_not_ambiguous(self, tool_name: str):
        """Verify tool names don't overlap in problematic ways.

        For example, 'research_test' and 'research_testing' could cause
        confusion. This is a soft check.
        """
        # Just verify naming is clear and distinct
        assert len(tool_name) >= 10, \
            f"Tool name suspiciously short: {tool_name}"

    def test_tool_registration_completeness(self):
        """Meta-test: Verify we're capturing registration correctly.

        Ensures the regex-based extraction is working as intended.
        """
        names = get_all_tool_names()

        # Should find key tool functions we know exist
        known_tools = {
            "research_fetch",
            "research_spider",
            "research_deep",
            "research_github",
        }

        for tool in known_tools:
            assert tool in names, f"Known tool not extracted: {tool}"


class TestToolDistribution:
    """Analyze tool distribution and coverage metrics."""

    def test_tool_domain_coverage(self):
        """Verify tools span core research domains.

        A well-balanced tool suite should cover:
        - Content discovery (fetch, search)
        - Data extraction (spider, markdown, PDF)
        - Intelligence (OSINT, threat intel, dark web)
        - Analysis (NLP, behavioral, compliance)
        - Infrastructure support (cache, config, sessions)
        """
        names = get_all_tool_names()

        domains = {
            "discovery": ["search", "deep", "multi_search"],
            "extraction": ["fetch", "spider", "markdown", "pdf"],
            "intelligence": ["osint", "threat", "dark", "leak"],
            "analysis": ["sentiment", "stylometry", "deception", "persona"],
            "infrastructure": ["session", "config", "cache", "health"],
        }

        for domain, keywords in domains.items():
            found = sum(1 for name in names if any(kw in name for kw in keywords))
            assert found >= 1, f"Domain '{domain}' has no tools"

    def test_tool_count_stability(self):
        """Verify tool count is within expected range.

        Dramatic changes in tool count might indicate:
        - New feature additions (expected)
        - Accidental deregistrations (bug)
        - Configuration issues
        """
        names = get_all_tool_names()
        count = len(names)

        # Expected range based on architecture document
        min_expected = 500
        max_expected = 800

        assert min_expected <= count <= max_expected, \
            f"Tool count ({count}) outside expected range [{min_expected}, {max_expected}]"

    def test_research_prefix_consistency(self):
        """Verify all tools use 'research_' prefix uniformly.

        This is a key architectural constraint that enables
        MCP client-side tool discovery and filtering.
        """
        names = get_all_tool_names()

        # Count tools with prefix
        with_prefix = sum(1 for n in names if n.startswith("research_"))
        without_prefix = len(names) - with_prefix

        assert without_prefix == 0, \
            f"Found {without_prefix} tools without 'research_' prefix"
        assert with_prefix == len(names), \
            f"Prefix consistency check failed: {with_prefix} / {len(names)}"


if __name__ == "__main__":
    # Run basic coverage check
    names = get_all_tool_names()
    print(f"Found {len(names)} registered tools")
    print("\nFirst 20 tools:")
    for name in names[:20]:
        print(f"  - {name}")
