#!/bin/bash
# Full Project Audit — Kimi implements, Gemini reviews
# Generated: 2026-05-22
# Project: Loom (936 tools MCP server)

PROJ="/Users/aadel/projects/loom"
OUT="$PROJ/ai_actions"
mkdir -p "$OUT"
GEMINI_CALL=0

gemini_review() {
    local input_file="$1"
    local output_file="$2"
    GEMINI_CALL=$((GEMINI_CALL + 1))
    # Rotate accounts every 5 calls
    if [ $((GEMINI_CALL % 5)) -eq 1 ]; then
        ACCOUNTS=(91 21 adel 26 asu)
        IDX=$(( (GEMINI_CALL / 5) % 5 ))
        echo "[Gemini] Switching to account ${ACCOUNTS[$IDX]}"
        ~/.gemini/gemini-switch.sh "${ACCOUNTS[$IDX]}" 2>/dev/null
    fi
    local content
    content=$(head -c 50000 "$input_file")
    for attempt in 1 2 3 4 5; do
        gemini -m gemini-3.1-pro-preview --approval-mode yolo \
            "Review this Kimi implementation output for correctness. Flag any bugs, missing edge cases, or incorrect logic. Be concise — list only real issues, not style nits.

$content" > "$output_file" 2>&1
        if [ -s "$output_file" ] && ! grep -qiE 'RESOURCE_EXHAUSTED|MODEL_CAPACITY|429|IneligibleTier' "$output_file"; then
            return 0
        fi
        echo "[Gemini] Retry $attempt..."
        sleep $((attempt * 15))
    done
    echo "Gemini failed after 5 retries" > "$output_file"
}

echo "=== Loom Full Project Audit ==="
echo "Started: $(date)"
echo ""

# ============================================================
# TODO-2: Fix 52 type error bugs (list where str expected)
# Root cause: middleware passes generic params with wrong types
# Fix approach: add type coercion guards in each tool
# ============================================================
echo "[1/6] TODO-2: Fix type error bugs in 52 tools"
kimi --thinking --yolo -w "$PROJ" -p "
TASK: Fix type error bugs in Loom MCP tools.

PROBLEM: 52 tools crash with errors like 'list object has no attribute lower' because the middleware
sometimes passes list/dict params where the tool expects str. The tools should defensively handle this.

FIX PATTERN: At the start of each affected function, add type coercion:
  if isinstance(text, list): text = ' '.join(str(x) for x in text)
  if isinstance(text, dict): text = str(text)

AFFECTED TOOLS (fix ALL of these in src/loom/tools/):
- research_attack_score, research_bias_lens, research_compliance_check, research_deception_detect
- research_detect_language, research_detect_paradox, research_diff_compare, research_explain_bypass
- research_extract_actionables, research_fingerprint_model, research_genetic_fuzz
- research_grant_forensics, research_hcs_score_full, research_hcs_score_prompt, research_hcs_score_response
- research_holographic_encode, research_knowledge_extract, research_model_sentiment
- research_parameter_sweep, research_pii_scan, research_potency_score, research_psycholinguistic
- research_quality_escalate, research_refusal_detector, research_script_confusion
- research_simplify, research_stealth_detect_comparison, research_stealth_hire_scanner
- research_stealth_score_heuristic, research_stego_analyze, research_stego_encode
- research_strip_hedging, research_stylometry, research_vision_compare
- research_code_switch_attack, research_browser_fingerprint

For each tool:
1. Find the function in src/loom/tools/
2. Identify which param receives wrong type (usually 'text', 'response', 'prompt')
3. Add type coercion guard at the function start
4. Do NOT change function signatures, only add guards inside the function body

Fix at least 20 of these tools. Show each file changed and the specific fix.
" > "$OUT/kimi_type_errors.md" 2>&1
echo "  Kimi done. Running Gemini review..."
gemini_review "$OUT/kimi_type_errors.md" "$OUT/gemini_type_errors.md"

# ============================================================
# TODO-3: Fix 4 SQLite DB parameter binding errors
# ============================================================
echo "[2/6] TODO-3: Fix DB parameter binding errors"
kimi --thinking --yolo -w "$PROJ" -p "
TASK: Fix 4 SQLite parameter binding errors in Loom tools.

PROBLEM: These tools pass dict/list to SQLite which only accepts str/int/float/bytes:
1. research_backoff_dlq_list — Error binding parameter 1: type 'dict' is not supported
2. research_exploit_register — Error binding parameter 3: type 'dict' is not supported
3. research_trace_end — Error binding parameter 1: type 'dict' is not supported
4. research_webhook_system_register — Error binding parameter 2: type 'list' is not supported

FIX: Before inserting into SQLite, JSON-serialize any dict/list params:
  import json
  if isinstance(param, (dict, list)): param = json.dumps(param)

Find each tool in src/loom/tools/ and apply the fix. Show the exact code change for each.
" > "$OUT/kimi_db_errors.md" 2>&1
echo "  Kimi done. Running Gemini review..."
gemini_review "$OUT/kimi_db_errors.md" "$OUT/gemini_db_errors.md"

# ============================================================
# TODO-4: Fix 2 Playwright sync-in-async errors
# ============================================================
echo "[3/6] TODO-4: Fix Playwright sync-in-async errors"
kimi --thinking --yolo -w "$PROJ" -p "
TASK: Fix 2 Playwright sync-in-async errors in Loom tools.

PROBLEM: These tools use Playwright Sync API inside an asyncio event loop:
1. research_cloak_session — CloakBrowser session error: Playwright Sync API inside asyncio loop
2. research_fingerprint_audit — same error

FIX: Wrap sync Playwright calls in asyncio.to_thread() or convert to Playwright async API.

Example fix pattern:
  # Before (broken):
  with sync_playwright() as p:
      browser = p.chromium.launch()

  # After (fixed):
  async def _run_playwright():
      async with async_playwright() as p:
          browser = await p.chromium.launch()

  # OR simpler:
  result = await asyncio.to_thread(_sync_playwright_function)

Find these tools in src/loom/tools/ and fix them. Show exact code changes.
" > "$OUT/kimi_playwright_errors.md" 2>&1
echo "  Kimi done. Running Gemini review..."
gemini_review "$OUT/kimi_playwright_errors.md" "$OUT/gemini_playwright_errors.md"

# ============================================================
# TODO-5: Investigate HTTP 400/500 tools
# ============================================================
echo "[4/6] TODO-5: Investigate HTTP 400/500 tools"
kimi --thinking --yolo -w "$PROJ" -p "
TASK: Investigate why these 14 tools return HTTP 400/500 errors.

TOOLS:
- research_cicd_run, research_consensus_build, research_consensus_pressure
- research_crescendo_loop, research_danger_prescore, research_debate_podium
- research_deep, research_drift_analyze, research_drift_report
- research_evidence_chain, research_multi_hop, research_orchestrate_chain
- research_pressure_test, research_semantic_route

For each tool:
1. Find its implementation in src/loom/tools/
2. Check what params it expects (look at function signature and Pydantic model)
3. Identify why generic params would cause HTTP 400 (missing required params? wrong types?)
4. Report: tool name, actual required params, and whether the error is a real bug or just wrong test params.

Only report tools that have REAL code bugs (not just param issues).
" > "$OUT/kimi_http_errors.md" 2>&1
echo "  Kimi done. Running Gemini review..."
gemini_review "$OUT/kimi_http_errors.md" "$OUT/gemini_http_errors.md"

# ============================================================
# AUDIT-1: Deep audit of completed LLM cascade fix
# ============================================================
echo "[5/6] AUDIT-1: Deep audit LLM cascade"
kimi --thinking --yolo -w "$PROJ" -p "
TASK: Deep audit the LLM cascade system to verify it works correctly.

CONTEXT: We fixed 'import time' missing in 7 modules. Verify ALL LLM-related files have correct imports.

CHECK:
1. src/loom/tools/llm/llm.py — verify import time is present, check all time.time() uses
2. src/loom/tools/llm/composer.py — verify import time
3. src/loom/tools/llm/query_builder.py — verify import time
4. src/loom/providers/llm_openai_compat.py — verify import time
5. src/loom/provider_router.py — check for any missing imports
6. src/loom/llm_client.py — verify import time
7. src/loom/daisy_chain.py — verify import time
8. src/loom/model_evidence.py — verify import time

For each file:
1. Read the imports section
2. Grep for time.time(), time.sleep(), time.monotonic()
3. Verify the import is present
4. Check for any OTHER missing imports (asyncio, json, os, re, math, etc.)

Report: file, import status, any other issues found.
" > "$OUT/kimi_llm_audit.md" 2>&1
echo "  Kimi done. Running Gemini review..."
gemini_review "$OUT/kimi_llm_audit.md" "$OUT/gemini_llm_audit.md"

# ============================================================
# AUDIT-5: Deep audit Facebook tools
# ============================================================
echo "[6/6] AUDIT-5: Deep audit Facebook tools"
kimi --thinking --yolo -w "$PROJ" -p "
TASK: Deep audit the 6 Facebook research tools for correctness.

FILES:
1. src/loom/tools/intelligence/facebook_research.py — 6 tool functions
2. src/loom/tools/intelligence/fb_graphql_helpers.py — GraphQL extraction helpers
3. src/loom/registrations/intelligence.py — tool registration

CHECK FOR EACH TOOL:
1. research_facebook_search — Does it correctly parse search results?
2. research_facebook_page — Does it extract page info, posts, reactions?
3. research_facebook_profile — Does it handle both public and private profiles?
4. research_facebook_group — Does it handle group access restrictions?
5. research_facebook_marketplace — Does it search marketplace listings?
6. research_facebook_page_insights — Does it return engagement metrics?

For each:
- Read the function code
- Check error handling (what if Camoufox returns empty HTML?)
- Check regex patterns (will they break on Arabic/RTL content?)
- Check SharedModels fallback logic
- Report any bugs or improvements needed
" > "$OUT/kimi_facebook_audit.md" 2>&1
echo "  Kimi done. Running Gemini review..."
gemini_review "$OUT/kimi_facebook_audit.md" "$OUT/gemini_facebook_audit.md"

# ============================================================
# Summary
# ============================================================
echo ""
echo "=== All agents completed ==="
echo "Finished: $(date)"
echo ""
echo "Results:"
ls -la "$OUT"/kimi_*.md "$OUT"/gemini_*.md 2>/dev/null
echo ""
echo "Next: Review Gemini flags, fix issues, commit, sync to Hetzner"
echo "  rsync -az ai_actions/ hetzner:/opt/loom-v3/ai_actions/"
