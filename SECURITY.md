# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
| < 0.1.0 | No        |

During the 0.1.x alpha phase, only the latest minor release receives security updates.

## Reporting a Vulnerability

Report security vulnerabilities via a GitHub security advisory:

- Open a new advisory at https://github.com/aadelb/loom/security/advisories/new
  (private by default — only project maintainers see it)
- Do not open public GitHub issues for security vulnerabilities

We aim to acknowledge vulnerability reports within 48 hours and provide a fix or mitigation for critical issues within 14 days. Public disclosure follows a 90-day embargo by default.

## In-Scope

The following security issues are Loom's responsibility:

- **SSRF protection in URL validator** — Blocks private, loopback, link-local, multicast, reserved, and metadata IP ranges before any network request
- **Path traversal in session profile directories** — Session names validated with strict regex; profile directories locked to 0700 permissions
- **Command injection in `research_github` query handling** — Queries use argument lists with `--` separator to prevent flag injection
- **API key leakage in error messages and logs** — Pattern-based redaction of `sk-*`, `nvapi-*`, and other provider key formats
- **Prompt injection through scraped content passed to LLM tools** — Scraped content wrapped in explicit "untrusted input" prefix
- **Cache file corruption from concurrent writers** — Atomic writes via UUID temp file and `os.replace()`

## Out-of-Scope

These security issues belong to upstream projects:

- Vulnerabilities in upstream libraries (Scrapling, Crawl4AI, OpenAI SDK, etc.) — report to respective projects
- Issues in external services (Exa, Tavily, Firecrawl, OpenAI API, NVIDIA NIM) — report to service providers
- Denial of service via unrestricted outbound fetches — mitigate with your own rate limiting and network policies

## Built-in Protections

Loom includes these hardened controls by default:

1. **URL validator** — Blocks private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), loopback (127.0.0.0/8, ::1), link-local (169.254.0.0/16), multicast (224.0.0.0/4, ff00::/8), reserved, and metadata IPs
2. **GitHub query allow-list** — `research_github` restricts to `repo:`, `user:`, `language:`, `created:` filters
3. **Argument separator** — Bash/spider tools use `--` to prevent flag injection
4. **Atomic cache writes** — UUID temp file + `os.replace()` prevents partial or corrupted entries
5. **Error message sanitization** — API keys stripped from logs and error outputs
6. **LLM input wrapping** — Scraped content prefixed with safety marker before LLM processing
7. **Session name validation** — Regex `^[a-z0-9_-]{1,32}$` restricts session identifiers
8. **File permissions** — `.env` files ignored by git; manual 0600 permissions recommended

## Hardening Recommendations

- **Bind the server to 127.0.0.1** and reach it via SSH local forward or Tailscale instead of exposing over the network
- **Run under a non-root user** using systemd `User=` directive or Docker `USER` instruction
- **Enable systemd hardening**: `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=yes`
- **Rotate API keys periodically** for search providers and LLM services
- **Monitor cache statistics** with `loom cache stats` and set `CACHE_TTL_DAYS` to a reasonable retention window
- **Cap LLM spend** with `LLM_DAILY_COST_CAP_USD` environment variable to prevent runaway billing

