# Loom v4 — Remaining Tasks & Next Steps

**Date:** 2026-05-02
**Server Status:** LIVE on Hetzner (128GB RAM), 641 tools, 957 strategies, 11ms avg latency
**Completion:** 127/136 tasks done (93.4%)

---

## Remaining 9 Tasks

### PRIORITY 1: Architecture (High Impact, High Risk)

#### #971 — Split server.py into modular sub-files
- **Current state:** server.py is 2860 lines with 643 tool registrations in one `_register_tools()` function
- **Risk:** HIGH — touching this file can crash the entire server
- **Scaffolding done:** `src/loom/registrations/__init__.py` exists with 8-category structure
- **Approach:** Incrementally move registrations to category files (core, llm, reframe, adversarial, infrastructure, intelligence, research, devops)
- **Each category file:** imports its modules + calls `mcp.tool()(_wrap_tool(...))` for its group
- **Backward compat:** `_register_tools(mcp)` calls `register_all_tools(mcp, _wrap_tool)` from registrations package
- **Estimated effort:** 2-3 hours of careful sequential work
- **Testing:** After each category move, run `python3 -c "from loom.server import create_app; create_app()"` to verify

#### #973 — Single-process server cannot scale
- **Current state:** One Python process handles all 641 tools
- **Issue:** CPU-bound tools block the event loop for other requests
- **Solution options:**
  1. `uvicorn --workers 4` (simplest — FastMCP may not support)
  2. `gunicorn` with uvicorn workers
  3. Process pool for CPU-heavy tools (ProcessPoolExecutor)
- **Recommended:** Try `--workers` first via systemd ExecStart modification
- **Testing:** Load test with 200+ concurrent calls after change

#### #972 — Event loop blocking (sync calls in async context)
- **Current state:** 4 tools use synchronous `def` instead of `async def` (holographic_payload, safety_predictor, predictive_ranker, persistent_memory)
- **Impact:** LOW — MCP framework handles sync functions by running them in thread pool
- **Fix:** Convert to `async def` or confirm MCP wraps them correctly
- **Priority:** P3 (not causing issues in production)

#### #974 — SQLite session storage not distributed
- **Current state:** Browser sessions stored in local SQLite, lost on restart
- **Impact:** MEDIUM — sessions are short-lived for most tools
- **Solutions:**
  1. Redis (if available) for distributed state
  2. Persist to shared filesystem
  3. Accept limitation — sessions are ephemeral by design
- **Recommended:** Document as known limitation, sessions auto-recreate

---

### PRIORITY 2: Code Quality (Low Risk, Moderate Impact)

#### #998 — params.py is 7192 lines
- **Current state:** 267 Pydantic model classes in one file
- **Impact:** Readability only — no runtime issues
- **Risk of splitting:** Every tool does `from loom.params import XxxParams` — changing module structure breaks 330+ imports
- **Safe approach:** Convert to package (`params/__init__.py` re-exports all) — Python handles this transparently
- **Alternative:** Leave as-is with section comment headers (working fine in production)
- **Recommended:** LOW PRIORITY — skip unless actively developing new params

#### #1001 — Multiple SQLite databases with no unified management
- **Current state:** 10+ .db files in ~/.loom/ (checkpoints, dlq, economy, auth, feedback, gamification, hub, marketplace, knowledge_base, hitl_eval)
- **Issues:** No unified backup schedule, no WAL checkpoint, no disk monitoring
- **Existing mitigations:** 
  - `backup_system.py` tool backs up all .db files
  - `schema_migrate.py` tool manages schemas
  - `sqlite_pool.py` handles connection pooling
- **Remaining gap:** Automated daily backup cron + WAL checkpoint
- **Fix:** Add to Hetzner crontab: `0 3 * * * cd /opt/research-toolbox && python3 -c "from loom.tools.backup_system import research_backup_create; import asyncio; asyncio.run(research_backup_create())"`

---

### PRIORITY 3: External Integrations (Need Binary Installation)

#### #981 — fingerprint-suite evasion validator
- **What:** Browser fingerprint randomization testing
- **Requires:** `npm install fingerprint-suite` on Hetzner
- **Tool file:** Would call Node.js subprocess
- **Effort:** 2 hours (install + write wrapper)

#### #982 — silk-guardian Linux anti-forensics
- **What:** Linux kernel module for anti-forensic monitoring
- **Requires:** Kernel module compilation on Hetzner (risky on production server)
- **Recommendation:** SKIP — too dangerous for production. Document as "lab-only" capability
- **Alternative:** Keep as documentation/reference only

#### #984 — 10 remaining privacy/anti-forensics tools
- **What:** 10 GitHub repos needing installation (flock-detection, chameleon, stegma, BrowserBlackBox, PII-Recon, swiftGuard, steganography-python, ulexecve, saruman, browser-fingerprinting)
- **Requires:** Mix of pip install + apt install + build from source
- **Effort:** 1 day (install all, write subprocess wrappers)
- **Recommended approach:**
  1. `pip install` the Python ones (PII-Recon, steganography-python)
  2. `apt install` or clone the binary ones
  3. Create subprocess wrapper tools for each
  4. Register in server.py

---

### PRIORITY 4: Testing (Needs Live Credentials)

#### #881 — Fix remaining functional test failures
- **Context:** Originally 35 test failures — all were parameter validation issues (wrong test params, not real bugs)
- **Current state:** With 641 tools now registered (up from 346), test count has changed
- **Approach:**
  1. Run `pytest tests/ --timeout=300 --maxfail=20 -x` on Hetzner
  2. Identify which tests fail
  3. Update test params to match current tool signatures
- **Note:** Most "failures" are test infrastructure issues, not tool bugs
- **Effort:** 2-3 hours of test fixing on Hetzner

---

## Summary Table

| # | Task | Priority | Risk | Effort | Blocker |
|---|------|----------|------|--------|---------|
| #971 | Split server.py | P1 | HIGH | 3h | None (careful work) |
| #973 | Multi-process | P1 | MEDIUM | 1h | Test with load |
| #972 | Event loop sync | P3 | LOW | 30min | None |
| #974 | Distributed sessions | P2 | LOW | 1h | Design decision |
| #998 | Split params.py | P4 | MEDIUM | 2h | Risk vs benefit |
| #1001 | SQLite management | P3 | LOW | 30min | Cron access |
| #981 | fingerprint-suite | P3 | LOW | 2h | npm on Hetzner |
| #982 | silk-guardian | P5 | HIGH | Skip | Kernel module |
| #984 | 10 privacy tools | P3 | LOW | 8h | Binary installs |
| #881 | Test fixes | P2 | LOW | 3h | Live credentials |

---

## What's Working NOW (Production Ready)

- **641 MCP tools** registered and responding
- **957 reframing strategies** across 32 modules
- **8 LLM providers** + CLI fallback (gemini/kimi/codex)
- **Health endpoint:** `curl http://server:8787/health` → JSON
- **Load tested:** 150 concurrent calls, 0% errors, 11ms avg
- **Smoke tested:** 330/330 modules import successfully
- **Pre-deploy script:** `python3 scripts/pre_deploy.py` validates before rsync
- **CI/CD:** GitHub Actions runs lint + test + pre-deploy on every push
- **Intelligent orchestration:** `research_do("instruction")` → auto-selects + executes tools
- **60s timeout:** All tools have automatic timeout protection
- **Audit logging:** Every tool call recorded with SHA-256 param hash
- **Moonshot API key:** Updated and working

---

## Deployment Command

```bash
# Verify locally first
python3 scripts/pre_deploy.py

# Deploy
rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='.claude' src/ hetzner:/opt/research-toolbox/src/

# Restart
ssh hetzner "sudo systemctl restart research-toolbox"

# Verify
ssh hetzner "sleep 12 && curl -s http://127.0.0.1:8787/health"
```

---

*Author: Ahmed Adel Bakr Alderai*
*Last updated: 2026-05-02*
