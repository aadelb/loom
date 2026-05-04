"""Comprehensive test suite for Loom MCP server.

This directory contains a full test pyramid for the 820-tool MCP server:

Test Categories:
  - Smoke tests: Basic server health and imports
  - Unit tests: Individual tool module imports and structure
  - Integration tests: Pipeline chains and component interaction
  - Functional tests: 50+ critical tools with minimal params
  - Security tests: SSRF, injection, auth, PII, rate limiting
  - Performance tests: Latency, throughput, startup time
  - Load tests: Concurrent requests, memory leaks
  - API key tests: Provider validation and connectivity
  - Regression tests: Known bugs and fixes

Running the suite:
  - All tests: pytest tests/comprehensive/
  - By category: pytest tests/comprehensive/test_smoke.py
  - By marker: pytest tests/comprehensive/ -m smoke
  - With script: bash tests/comprehensive/run_all.sh

Test markers:
  - @pytest.mark.smoke
  - @pytest.mark.unit
  - @pytest.mark.integration
  - @pytest.mark.functional
  - @pytest.mark.security
  - @pytest.mark.performance
  - @pytest.mark.load
  - @pytest.mark.regression
"""
