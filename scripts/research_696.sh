#!/bin/bash
# Research Task 696: Multilingual Code-Switching Attack Vectors
# Calls loom MCP research_multi_search via curl and aggregates results

OUTPUT_FILE="/opt/research-toolbox/tmp/research_696_multilingual.json"
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Start JSON output
cat > "$OUTPUT_FILE" <<EOF
{
  "task_id": "RESEARCH_696",
  "title": "Multilingual Code-Switching Attack Vectors",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "findings": {
EOF

QUERIES=(
    "multilingual jailbreak code switching attack LLM 2025"
    "code switching prompt injection safety bypass"
    "mixed language jailbreak confusion safety filter"
    "Arabic English mixed prompt bypass safety"
    "low resource language LLM safety filter bypass"
    "underrepresented language safety vulnerability"
    "Arabic RTL injection attack LLM safety"
    "diacritics manipulation Arabic prompt attack"
    "Arabic safety filter evasion technique"
    "homoglyph Unicode confusables multilingual LLM"
    "Unicode normalization bypass attack"
    "script mixing attack prompt injection"
    "PINT benchmark multilingual inputs safety"
    "multilingual LLM safety evaluation 2024 2025"
    "low-resource language jailbreak benchmark"
    "Romanization Arabic phonetic bypass attack"
    "transliteration attack safety filter"
    "phonetic code-switching jailbreak"
)

TOTAL=${#QUERIES[@]}
SUCCESS=0
FAILED=0

echo "[RESEARCH_696] Starting research with ${TOTAL} queries"
echo "[RESEARCH_696] MCP Server: http://127.0.0.1:8787"

for i in "${!QUERIES[@]}"; do
    QUERY="${QUERIES[$i]}"
    IDX=$((i+1))

    echo "[${IDX}/${TOTAL}] Searching: ${QUERY:0:70}"

    # Call MCP tool via HTTP
    RESULT=$(curl -s -X POST http://127.0.0.1:8787/call \
        -H "Content-Type: application/json" \
        -d "{\"method\": \"tools/call\", \"params\": {\"name\": \"research_multi_search\", \"arguments\": {\"query\": \"$(echo "$QUERY" | sed 's/"/\\"/g')\", \"providers\": [\"exa\", \"tavily\", \"duckduckgo\"], \"max_results_per_provider\": 4, \"include_academic\": true}}}" \
        2>/dev/null)

    if [ -z "$RESULT" ]; then
        echo "  ✗ No response from MCP server"
        ((FAILED++))
    else
        # Check if result contains an error field
        if echo "$RESULT" | grep -q '"error"'; then
            echo "  ✗ Error response"
            ((FAILED++))
        else
            # Count results
            COUNT=$(echo "$RESULT" | grep -o '"results":\[' | wc -l)
            echo "  ✓ Retrieved results"
            ((SUCCESS++))
        fi
    fi

    # Add to JSON (escape quotes in query)
    ESCAPED_QUERY=$(echo "$QUERY" | sed 's/"/\\"/g')
    echo "    \"$ESCAPED_QUERY\": {\"status\": \"$([ $COUNT -gt 0 ] && echo 'success' || echo 'error')\", \"result_count\": $COUNT}," >> "$OUTPUT_FILE"

    sleep 1
done

# Close JSON
cat >> "$OUTPUT_FILE" <<EOF
    "_final": {"success": ${SUCCESS}, "failed": ${FAILED}, "total": ${TOTAL}}
  },
  "metadata": {
    "total_queries": ${TOTAL},
    "providers": ["exa", "tavily", "duckduckgo"],
    "execution_mode": "live"
  }
}
EOF

echo ""
echo "[RESEARCH_696] Results saved to: $OUTPUT_FILE"
echo "[RESEARCH_696] Success: ${SUCCESS}, Failed: ${FAILED}"
echo "[RESEARCH_696] Research complete."
