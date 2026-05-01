#!/usr/bin/env python3
"""Print summary of REQ-002 test results."""

import json
import sys

with open("/opt/research-toolbox/tmp/req002_result.json") as f:
    data = json.load(f)

print("=" * 80)
print("REQ-002 WORKFLOW EXECUTION SUMMARY")
print("=" * 80)
print()

print("STAGE 1: Deep Research")
s1 = data["stages"]["1_deep_research"]
print(f"  Query: {s1['query']}")
print(f"  Pages searched: {s1['pages_searched']}")
print(f"  Pages fetched: {s1['pages_fetched']}")
print(f"  Top pages found: {s1['top_pages_count']}")
print()

print("STAGE 2: Multi-Source Search")
s2 = data["stages"]["2_multi_search"]
print(f"  Query: {s2['query']}")
print(f"  Engines queried: {len(s2['engines_queried'])} ({', '.join(s2['engines_queried'])})")
print(f"  Total raw results: {s2['total_raw_results']}")
print(f"  Deduplicated results: {s2['total_deduplicated']}")
print(f"  Results by source: {s2['sources_breakdown']}")
print()

print("STAGE 3: LLM Synthesis")
s3 = data["stages"]["3_llm_synthesis"]
print(f"  Question: {s3['question']}")
status = "Yes" if s3['answer_length'] > 0 else "No (LLM providers unavailable)"
print(f"  Answer generated: {status}")
print(f"  Sources synthesized: {len(data['summary']['key_findings']['sources_cited'])}")
print()

print("SOURCES CITED:")
for i, src in enumerate(data["summary"]["key_findings"]["sources_cited"], 1):
    print(f"  {i}. {src['title']}")
    print(f"     {src['url']}")
print()

print("VALIDATION RESULTS:")
val = data["validation"]
chk1 = "✓" if val["criterion_1_strategies_and_tools"] else "✗"
chk2 = "✓" if val["criterion_2_actionable_insights"] else "✗"
chk3 = "✓" if val["criterion_3_multiple_sources"] else "✗"
print(f"  {chk1} AI strategies & tools identified")
print(f"  {chk2} Actionable insights generated")
print(f"  {chk3} Multiple sources cited")
overall = "✓ PASS" if val["all_criteria_met"] else "✗ FAIL"
print(f"  {overall} - {overall.split()[0]} acceptance criteria")
print()

print("METRICS:")
summary = data["summary"]
print(f"  Total sources searched: {summary['total_sources_searched']}")
print(f"  Total cost: ${summary['total_cost_usd']:.4f}")
print(f"  Execution time: {summary['total_time_ms']}ms")
print()

print("=" * 80)
