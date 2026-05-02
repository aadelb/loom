# Strategy Feedback Loop Usage

The strategy feedback system learns which strategies work best by tracking attempt results and recommending proven approaches.

## Tools

### 1. research_strategy_log

Logs a strategy attempt result to SQLite at `~/.loom/feedback/strategy_log.db`.

**Parameters:**
- `topic` (str): Research topic (e.g., "prompt_injection", "jailbreak")
- `strategy` (str): Strategy name used
- `model` (str): LLM model identifier (e.g., "gpt-4", "claude-3")
- `hcs_score` (float): HCS effectiveness score (0-100)
- `success` (bool): Whether the attack succeeded

**Returns:**
```json
{
  "logged": true,
  "total_entries": 42,
  "db_path": "/Users/user/.loom/feedback/strategy_log.db"
}
```

**Example:**
```
POST research_strategy_log
- topic: "prompt_injection"
- strategy: "token_smuggling"
- model: "gpt-4-turbo"
- hcs_score: 92.5
- success: true
```

---

### 2. research_strategy_recommend

Query the log for the best strategy for a topic+model combination.

**Parameters:**
- `topic` (str): Research topic
- `model` (str, default="auto"): LLM model or "auto" for best across all models

**Returns:**
```json
{
  "recommended_strategy": "token_smuggling",
  "avg_hcs": 89.3,
  "success_rate": 0.875,
  "total_attempts": 8,
  "model": "gpt-4-turbo",
  "topic": "prompt_injection"
}
```

**Use Cases:**
- Get best strategy for a specific topic before planning an attack
- Filter by model to find model-specific best practices
- Use "auto" to find the universally best strategy

---

### 3. research_strategy_stats

Get overall statistics across all logged attempts.

**Returns:**
```json
{
  "total_logs": 147,
  "topic_count": 8,
  "top_strategies": [
    {
      "strategy": "token_smuggling",
      "avg_hcs": 89.3,
      "successes": 7,
      "total_attempts": 8,
      "success_rate": 0.875
    }
  ],
  "worst_strategies": [
    {
      "strategy": "simple_jailbreak",
      "avg_hcs": 25.1,
      "successes": 0,
      "total_attempts": 12,
      "success_rate": 0.0
    }
  ],
  "model_performance": [
    {
      "model": "gpt-4-turbo",
      "attempts": 45,
      "successes": 38,
      "avg_hcs": 82.1,
      "success_rate": 0.844
    }
  ],
  "db_path": "/Users/user/.loom/feedback/strategy_log.db"
}
```

**Insights:**
- Top 5 strategies ranked by success rate and average HCS
- Worst 3 strategies (min 3 attempts to qualify)
- Model performance ranking (attempts, successes, avg HCS, success rate)
- Topic count for monitoring coverage

---

## Database Schema

```sql
CREATE TABLE strategy_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    strategy TEXT NOT NULL,
    model TEXT NOT NULL,
    hcs_score REAL NOT NULL,
    success INTEGER NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX idx_topic_model ON strategy_log(topic, model);
```

---

## Workflow Example

```
1. Plan attack against "prompt_injection" on gpt-4
   → Call research_strategy_recommend(topic="prompt_injection", model="gpt-4")
   → Returns best strategy: "token_smuggling" (success_rate: 0.875)

2. Execute attack using token_smuggling
   → Run actual attack

3. Log result
   → Call research_strategy_log(
       topic="prompt_injection",
       strategy="token_smuggling",
       model="gpt-4",
       hcs_score=89.5,
       success=true
     )

4. Review performance
   → Call research_strategy_stats()
   → See token_smuggling ranked in top_strategies
```

---

## Key Features

- **Persistent Storage**: SQLite database at `~/.loom/feedback/strategy_log.db`
- **Fast Lookups**: Indexed on (topic, model) for quick recommendations
- **Success Rate Ranking**: Strategies ranked by both success rate and average HCS
- **Model-Aware**: Track effectiveness per model
- **No API Keys**: Pure local SQLite, no external dependencies
- **Error Resilience**: All functions return graceful error dicts on failure

---

## Tips

1. **Consistent Topic Names**: Use lowercase, underscore-separated names (e.g., "prompt_injection", "context_poisoning")
2. **Model Identifiers**: Use full model names (e.g., "gpt-4-turbo", "claude-3-opus", "gemini-1.5-pro")
3. **HCS Scores**: Normalize to 0-100 scale for consistent comparison
4. **Auto Recommendations**: Use model="auto" to find universally effective strategies
5. **Minimum Attempts**: Worst strategies filter requires 3+ attempts to avoid noise
