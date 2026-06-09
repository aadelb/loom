# Loom Code-Quality Scan (T25)

**Run:** 2026-06-09 on Hetzner, `src/loom/` (~95K LOC)
**Approach:** lightweight static analyzers in an isolated venv (`~/qa-venv`) — **no SonarQube
container** (see "Deeper-quality alternative" at the bottom for when to escalate).
**Tools:** vulture, radon, bandit, flake8, pylint, xenon, pyflakes, mccabe.

## Summary

| Dimension | Tool | Result | Verdict |
|-----------|------|--------|---------|
| **Maintainability** | radon MI | **791 A** · 6 B · 13 C | ✅ 97.7% A-grade — excellent |
| **Cyclomatic complexity** | radon CC | 785 functions grade C+ (of thousands); 12 at D/E | ⚠️ a few hotspots |
| **Security** | bandit | 14 high-sev · 31 med · 916 low | 🟡 mostly noise; 12 genuine |
| **Style/lint** | flake8 | 19,716 (mostly at default 79-col) | 🟡 cosmetic + real tab/space mix |
| **Dead code** | vulture | 55 findings (≥80% confidence) | 🟡 worth a pass |

## Complexity hotspots (radon CC, grade D/E — refactor candidates)

| Grade | Function | File context |
|-------|----------|--------------|
| **E (37)** | `_call_with_cascade` | tools/llm/llm.py — the core LLM router |
| **E (33)** | `ReportGenerator._compute_summary_stats` | report_gen |
| **D (30)** | `research_deep_url_analysis` | tools/core/deep_url_analysis.py |
| **D (28)** | `validate_url` | validators.py (SSRF-critical — test well before touching) |
| **D (24)** | `DockerSandbox.run_with_files` · `research_nodriver_fetch` | sandbox / nodriver |
| **D (22-23)** | `research_semantic_sitemap`, `run_journey`, `_calculate_hcs_score`, 3× nodriver | — |

These are the next `research_hcs_max`-style behavior-preserving splits (that one was already
done: CC 24→<8). `_call_with_cascade` (E/37) is the highest-leverage candidate but also the
riskiest (everything routes through it) — refactor under heavy test coverage only.

## Security (bandit) — signal vs noise

The "14 high-severity / 916 low" headline is dominated by **known-safe patterns**, not real holes:
- **704 `try_except_pass`** + 17 `try_except_continue` — broad except/continue (style, not vuln)
- **156 blacklist** — flags `import subprocess`/`pickle` existence (we use them legitimately)
- **20 `subprocess_without_shell_equals_true`** — this is the *correct* (safe) way to call subprocess → false positive

**Genuinely worth review (small, actionable):**
- **1× `request_with_no_cert_validation`** — a `verify=False` somewhere → find & justify or fix
- **11× `start_process_with_partial_path`** — subprocess invoked by bare name (PATH-dependent) → pin absolute paths where it matters
- **8× hashlib (MD5/SHA1)** — confirm these are cache keys / non-crypto (they are, e.g. cache.py) → annotate `# nosec` or switch to sha256

## Style (flake8) — mostly cosmetic, two real items

- **14,715 E501** at flake8's *default* 79-col — but the project standard is **100** (ruff line-length=100), so the real over-100 count is a small fraction. Not actionable against our own standard.
- **3,013 W191 (tabs) + 606 E101 (mixed tabs/spaces)** — ⚠️ **real**: some modules (e.g. `knowledge_graph.py`) indent with tabs while the codebase is spaces. Normalize with `ruff format`.
- **182 F401 unused imports + 86 F841 unused vars** — ⚠️ **real, auto-fixable**: `ruff check --fix --select F401,F841 src tests`.

## Recommended cleanup (low-risk, high-signal — not yet applied)
1. `ruff check --fix --select F401,F841 src` → drop unused imports/vars (182+86).
2. `ruff format src` → normalize the tab/space inconsistency (3,619 issues).
3. Fix the 1 `verify=False` + pin the 11 partial-path subprocess calls.
4. `vulture src --min-confidence 90` → review the 55 dead-code findings, delete confirmed.
5. Refactor 1–2 D/E hotspots per PR (behavior-preserving, like hcs_max), starting with the
   safe ones (`_compute_summary_stats`, `research_deep_url_analysis`) — leave `_call_with_cascade`
   and `validate_url` until they have dedicated tests.

## Deeper-quality alternative — SonarQube (when to escalate)

These lightweight analyzers give point-in-time findings but no **trend tracking, PR gates, or a
dashboard**. If we want continuous quality enforcement, stand up **SonarQube** (Docker is installed,
v29.2.1; RAM headroom is ~60 GB available):

```bash
sudo sysctl -w vm.max_map_count=262144           # Elasticsearch requirement
docker run -d --name sonarqube --restart unless-stopped \
  --memory=4g -p 9002:9000 sonarqube:community
# then: sonar-scanner with sonar.python.* + coverage from pytest-cov
```

**Trade-off:** SonarQube embeds Elasticsearch (~2-4 GB RAM + a persistent container) on a box that
already runs Ollama + Qdrant + loom-v3 and shows swap pressure (55/79 GB). Use it when we want a
quality *gate in CI* / historical trends; the lightweight tools above are sufficient for ad-hoc audits
and cost no standing memory. **Recommended:** stay on the lightweight tools; only adopt SonarQube if
we add a CI quality gate or want the dashboard for a review cadence.
