# Verification Checklist — Run After EVERY Task Completion

After completing any REQ task, find its row below and verify ALL criteria.

| REQ | Acceptance Criteria to Verify | Test Command |
|-----|------------------------------|-------------|
| REQ-001 | 5+ sources, insights[], citations[], HCS >= 7 | Live: research_deep + hcs_score |
| REQ-002 | AI-specific strategies, tool recommendations | Live: multi-provider search |
| REQ-003 | dark_forum + onion_discover invoked, no raw .onion URLs | Live: dark tools |
| REQ-004 | Salary data (AED), job titles, UAE-specific, sources | Live: multi_search + career |
| REQ-005 | >= 10 ideas, UAE keywords, feasibility | Live: search + competitive_intel |
| REQ-006 | 20+ varied prompts, unique results each | Live: 20 queries |
| REQ-007 | 8 providers respond | Live: ask_all_llms |
| REQ-008 | >= 5 unique search providers | Live: multi_search |
| REQ-009 | 5-turn context accumulates | Live: session lifecycle |
| REQ-010 | Report sections, citations, narrative | Live: generate_report |
| REQ-011 | 240 measurements (30×8) stored | Live: baseline test |
| REQ-012 | 826 strategies invoked, templates render | pytest test_prompt_reframe |
| REQ-013 | Succeeds within 5 attempts on 10 prompts | Live: auto_reframe |
| REQ-014 | precision>=0.90, recall>=0.85 on 100 samples | pytest test_prompt_reframe |
| REQ-015 | stacked > individual for 22 pairs | pytest test_reframe_tools |
| REQ-020 | detected_model, refusal_type populated | Live: adaptive_reframe |
| REQ-021 | Pearson r >= 0.7 | Live: 100 attempts per strategy |
| REQ-022 | 400 measurements, heatmap | Live: 50×8 matrix |
| REQ-023 | gap_report with failure analysis | Live: 30 hard prompts |
| REQ-024 | 72 test cases (12×3×2) | pytest test_reframe_tools |
| REQ-025 | compliance_with > compliance_without | Live: A/B 20 prompts |
| REQ-027 | Cohen's kappa >= 0.8 | Manual: 3 raters |
| REQ-028 | Pearson r >= 0.85 vs human | Manual: 100 ratings |
| REQ-029 | hcs_score in all results | pytest test_hcs_scorer |
| REQ-030 | per_model_hcs, per_strategy_hcs | Live: 100+ scored |
| REQ-031 | 70%+ score >= 8 | Live: 50 queries |
| REQ-032 | Alert on delta > 1.0 | pytest test_hcs_scorer |
| REQ-033 | 5 dimensions sum == total | pytest test_hcs_scorer |
| REQ-034 | empty→0, short→<=2, Arabic ok | pytest test_hcs_scorer |
| REQ-035 | Trend data with timestamps | Integration test |
| REQ-036 | 220 unique tools in logs | Live: coverage script |
| REQ-037 | 7 core tools return content | Live: parametrized |
| REQ-038 | ask_all_models>=5, ask_all_llms=8 | Live: query |
| REQ-039 | 8 ops correct output types | Live: parametrized |
| REQ-040 | 20 tools invoked, >=15 data | Live: parametrized |
| REQ-041 | 5 dark tools or graceful error | Live: tor check |
| REQ-042 | 12 intel tools structured output | Live: parametrized |
| REQ-043 | 7 safety tools return scores | Live: parametrized |
| REQ-044 | 11 academic tools data | Live: query |
| REQ-045 | 6 career tools UAE-specific | Live: query |
| REQ-046 | 8 NLP tools analysis fields | Live: text input |
| REQ-047 | 11 domain+security results | Live: domain scan |
| REQ-048 | 12 infra tools no exceptions | Live: invoke |
| REQ-058 | Session present after restart | Live: restart test |
| REQ-060 | RSS < 2x after 1000 calls | Perf: memory test |
| REQ-061 | p50<2s, p50<10s, p95<30s | Perf: 100 calls |
| REQ-062 | parallel <= 0.6 × sequential | Perf: comparison |
| REQ-063 | peak_memory < 2GB | Perf: ask_all_models |
| REQ-067 | No cross-request state bleed | Live: 2 dark calls |
| REQ-068 | >= 3 SSE events | Live: deep research |
| REQ-070 | Suggests relevant tools | Integration test |
| REQ-072 | SIGTERM → complete → exit 0 | Live: signal test |
| REQ-079 | Stripe test: sub + charge + invoice | Integration: Stripe |
