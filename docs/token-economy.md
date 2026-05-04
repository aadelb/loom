# Token Economy Middleware

The token economy system provides a credit-based cost model for tool execution in Loom. Users have a credit balance, and each tool call deducts credits based on the tool's complexity and resource requirements.

## Overview

The token economy middleware is **opt-in** and disabled by default. It wraps all tool executions and:

1. **Before execution**: Checks if the user has sufficient credits for the tool
2. **If insufficient**: Returns an error with required credits, available credits, and shortfall
3. **If sufficient**: Allows execution to proceed
4. **After execution**: Deducts credits from the user's balance
5. **Response metadata**: Adds cost information to the response

## Enabling Token Economy

Set the environment variable `LOOM_TOKEN_ECONOMY=true` to enable:

```bash
export LOOM_TOKEN_ECONOMY=true
export LOOM_USER_ID=user123
export LOOM_USER_BALANCE=100
loom serve
```

Required environment variables:
- `LOOM_TOKEN_ECONOMY`: Set to `"true"` to enable (case-insensitive)
- `LOOM_USER_ID`: User identifier (default: "anonymous")
- `LOOM_USER_BALANCE`: Current credit balance as integer (default: "0")

## Credit Cost Tiers

Tools are organized into four cost tiers:

### Free Tools (0 credits)
Perfect for configuration and system queries that don't consume external resources:
- `cache_stats`, `cache_clear` — Cache management
- `health_check` — Server status
- `config_get`, `config_set` — Configuration
- `session_list` — Session enumeration

### Basic Tools (1 credit)
Lightweight analysis and processing:
- `search` — Semantic search
- `text_analyze`, `detect_language` — Text processing
- `llm_classify`, `llm_embed`, `llm_extract` — LLM-based operations
- `sentiment_deep`, `stylometry` — Analysis tools
- `fact_checker`, `wayback` — Verification tools

### Medium Tools (5 credits)
Moderate I/O and processing, including network fetches:
- `fetch`, `spider`, `markdown` — Web scraping/fetching
- `github` — GitHub API calls
- `whois`, `dns_lookup` — DNS/network lookups
- `screenshot` — Page rendering
- `cert_analyze`, `security_headers` — Security analysis
- `breach_check`, `pdf_extract` — Data extraction
- `metadata_forensics`, `passive_recon` — Reconnaissance
- `image_intel`, `video_intel` — Media intelligence

### Heavy Tools (10 credits)
Intensive processing or multi-stage operations:
- `deep` — 12-stage deep research pipeline
- `ask_all_models` — Multi-LLM queries
- `prompt_reframe`, `auto_reframe`, `adaptive_reframe` — Strategy application
- `camoufox`, `botasaurus` — Stealth scrapers
- `multi_search` — Parallel search across providers
- `infra_correlator` — Infrastructure correlation
- `knowledge_graph` — Entity extraction
- `model_profile`, `consensus_build` — Analysis tools
- `crescendo_loop`, `reid_pipeline` — Orchestration

### Premium Tools (20 credits)
Dangerous, specialized, or highly resource-intensive operations:
- `dark_forum` — Darkweb forum access
- `onion_discover` — Tor network crawling
- `sandbox_run` — Code execution
- `full_pipeline`, `orchestrate_smart` — Complex multi-tool orchestration

## API

### `get_tool_cost(tool_name: str) -> int`

Returns the credit cost for a tool. The tool name can include or exclude the `research_` prefix.

```python
from loom.billing.token_economy import get_tool_cost

cost = get_tool_cost("fetch")          # Returns 5
cost = get_tool_cost("research_fetch") # Also returns 5 (prefix stripped)
cost = get_tool_cost("unknown_tool")   # Returns DEFAULT_COST (2)
```

### `check_balance(user_id: str, current_balance: int, tool_name: str) -> dict`

Checks if a user has sufficient credits before tool execution.

```python
from loom.billing.token_economy import check_balance

result = check_balance("user1", 100, "fetch")
# Returns:
# {
#   "sufficient": True,
#   "required": 5,
#   "balance": 100,
#   "shortfall": 0
# }

result = check_balance("user1", 3, "fetch")
# Returns:
# {
#   "sufficient": False,
#   "required": 5,
#   "balance": 3,
#   "shortfall": 2
# }
```

### `deduct_credits(user_id: str, current_balance: int, tool_name: str) -> dict`

Deducts credits after successful tool execution. Balance never goes negative.

```python
from loom.billing.token_economy import deduct_credits

result = deduct_credits("user1", 100, "fetch")
# Returns:
# {
#   "success": True,
#   "balance_before": 100,
#   "cost_charged": 5,
#   "balance_after": 95,
#   "tool_name": "fetch"
# }
```

### `get_balance(user_id: str, current_balance: int) -> dict`

Returns the current balance for a user.

```python
from loom.billing.token_economy import get_balance

result = get_balance("user1", 75)
# Returns:
# {
#   "user_id": "user1",
#   "balance": 75
# }
```

## Server Integration

The token economy is integrated into `server.py`'s `_wrap_tool()` function, which wraps all tool executions. When enabled:

### Before Execution

```python
if token_economy_enabled:
    tool_name = func.__name__
    balance_check = check_balance(user_id, current_balance, tool_name)
    
    if not balance_check["sufficient"]:
        return {
            "error": "insufficient_credits",
            "message": "...",
            "required_credits": ...,
            "available_credits": ...,
            "shortfall": ...
        }
```

### After Successful Execution

If the tool returns a dict, cost metadata is added:

```python
result["_token_economy"] = {
    "cost": 5,
    "balance_before": 100,
    "balance_after": 95
}
```

## Usage Scenarios

### Free Tier User
A user with 0 credits can still call free tools:

```python
check_balance("free_user", 0, "cache_stats")
# Returns: {"sufficient": True, "required": 0, "balance": 0, "shortfall": 0}
```

### Balance Exhaustion
A user runs tools until balance is insufficient:

```python
balance = 20

# Tool 1: search (1 credit) — OK
check = check_balance("user", balance, "search")
assert check["sufficient"]
balance = 19

# Tool 2: fetch (5 credits) — OK
check = check_balance("user", balance, "fetch")
assert check["sufficient"]
balance = 14

# Tool 3: deep (10 credits) — OK
check = check_balance("user", balance, "deep")
assert check["sufficient"]
balance = 4

# Tool 4: fetch again (5 credits) — INSUFFICIENT
check = check_balance("user", balance, "fetch")
assert not check["sufficient"]  # Need 5, have 4
assert check["shortfall"] == 1
```

### Credit Tier Alignment

Tool costs align with customer tiers:
- **Free tier**: 500 credits/month → only free tools
- **Pro tier**: 10,000 credits/month → ~2000 fetch calls or equivalent
- **Team tier**: 50,000 credits/month → ~10,000 fetch calls
- **Enterprise**: 200,000 credits/month → ~40,000 fetch calls

## Response Format

When token economy is enabled, successful tool responses include cost metadata:

```json
{
  "result": "...",
  "_token_economy": {
    "cost": 5,
    "balance_before": 100,
    "balance_after": 95
  }
}
```

Insufficient credit errors return:

```json
{
  "error": "insufficient_credits",
  "message": "Tool 'fetch' requires 5 credits, but you have 3. Need 2 more credits.",
  "tool": "fetch",
  "required_credits": 5,
  "available_credits": 3,
  "shortfall": 2
}
```

## Logging

Credit deductions and checks are logged with structured logging:

```python
log.info(
    "token_economy_deduction",
    user_id="user1",
    tool_name="fetch",
    cost=5,
    balance_before=100,
    balance_after=95
)

log.warning(
    "insufficient_credits",
    user_id="user1",
    tool_name="fetch",
    required=5,
    balance=3,
    shortfall=2
)
```

## Cost Model Philosophy

The token economy uses a **progressive cost model**:

1. **Free tools** (0 credits) — No resource consumption, always available
2. **Basic tools** (1 credit) — Pure computation, minimal I/O
3. **Medium tools** (5 credits) — Network I/O, external API calls, page rendering
4. **Heavy tools** (10 credits) — Multi-stage pipelines, intensive processing
5. **Premium tools** (20 credits) — Dangerous operations, specialized access

This model allows:
- Free tier users to access core functionality
- Pro/Team users to run comprehensive research workflows
- Enterprise customers to run resource-intensive orchestrations

## Testing

The token economy is thoroughly tested in `tests/test_billing/test_token_economy.py`:

```bash
pytest tests/test_billing/test_token_economy.py -v

# 24 tests covering:
# - Tool cost lookup (including prefix handling)
# - Balance checking (sufficient/insufficient)
# - Credit deduction (including boundary cases)
# - Cost tier consistency
# - Integration scenarios
```

All tests pass with 100% coverage of the token economy module.

## Implementation Notes

### Thread Safety

Balance reads and deductions are not atomic in this implementation. For production use with concurrent users, wrap `check_balance()` and `deduct_credits()` in a database transaction or use optimistic locking.

### Persistence

This module assumes the calling code manages balance persistence. In the current implementation:
- Balance is read from `LOOM_USER_BALANCE` environment variable
- Balance must be persisted by the caller (likely in a database)
- The middleware provides the deduction amount; persistence is external

### Future Enhancements

1. **Idempotent deductions** — Use idempotency keys to prevent double-charging on retries
2. **Rate limiting per tool** — Combine with `rate_limiter.py` for comprehensive control
3. **Time-based refunds** — Refund credits if tool execution fails
4. **Batch operations** — Discounted rates for bulk operations
5. **Premium pools** — Shared credit pools for team members

## See Also

- `src/loom/billing/` — Full billing system (cost tracking, tiers, Stripe integration)
- `src/loom/server.py` — Integration point with `_wrap_tool()` function
- `src/loom/rate_limiter.py` — Rate limiting (complements token economy)
