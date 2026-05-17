"""Autonomous agent loop — abliterated LLM calls Loom tools iteratively.

Gives local LLMs (mannix, qwen3-coder, gemma3n) real internet access by
letting them call any Loom tool in a loop until they have a complete answer.

Architecture:
  1. User query → LLM generates a plan (which tools to call)
  2. LLM outputs [TOOL_CALL: tool_name(params)] tags
  3. Agent extracts tool calls, executes them via Loom API
  4. Results injected back into LLM context
  5. LLM generates final answer with real data
  6. Loop until [DONE] or max_iterations
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.agent_loop")

OLLAMA_CHAT = "http://localhost:11434/api/chat"
LOOM_API = "http://127.0.0.1:8788/api/v1/tools"

AGENT_SYSTEM_PROMPT = """You are an autonomous AI agent with access to real internet tools.
You can call tools by outputting: [TOOL_CALL: tool_name(param1="value1", param2="value2")]

Available tools:
- research_search(query="...", n=5) — search the internet
- research_fetch(url="...") — fetch a webpage
- research_markdown(url="...") — get clean markdown from URL
- research_github(kind="repo", query="...", limit=5) — search GitHub
- research_cve_lookup(query="...") — find CVEs
- research_whois(domain="...") — WHOIS lookup
- research_dns_lookup(domain="...") — DNS records

RULES:
1. Call tools to gather REAL information before answering
2. After getting tool results, synthesize a complete answer
3. Use REAL URLs from tool results in your final answer
4. When done, output [DONE] followed by your final answer
5. Maximum 5 tool calls per session
6. Be direct, no disclaimers"""

_TOOL_CALL_PATTERN = re.compile(
    r'\[TOOL_CALL:\s*(\w+)\(([^)]*)\)\]'
)


def _parse_tool_calls(text: str) -> list[tuple[str, dict[str, Any]]]:
    """Extract tool calls from LLM output."""
    calls = []
    for match in _TOOL_CALL_PATTERN.finditer(text):
        tool_name = match.group(1)
        params_str = match.group(2)
        params = {}
        for param_match in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', params_str):
            params[param_match.group(1)] = param_match.group(2)
        for param_match in re.finditer(r'(\w+)\s*=\s*(\d+)', params_str):
            params[param_match.group(1)] = int(param_match.group(2))
        calls.append((tool_name, params))
    return calls


async def _execute_tool(tool_name: str, params: dict[str, Any]) -> str:
    """Execute a Loom tool and return result as string."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(
                f"{LOOM_API}/{tool_name}",
                json=params,
            )
            data = r.json()
            if data.get("error"):
                return f"[ERROR: {data['error'][:200]}]"
            result_str = json.dumps(data, indent=2, default=str)
            return result_str[:3000]
        except Exception as e:
            return f"[ERROR: {e}]"


@handle_tool_errors("research_agent_loop")
async def research_agent_loop(
    query: str,
    model: str = "mannix/llama3.1-8b-abliterated",
    max_iterations: int = 5,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """Run autonomous agent loop — LLM calls Loom tools to research a query.

    The abliterated LLM acts as an agent, calling search/fetch/analyze tools
    iteratively until it has enough real data to provide a complete answer.

    Args:
        query: User's research question
        model: Ollama model to use as the agent brain
        max_iterations: Maximum tool-calling iterations (1-5)
        system_prompt: Custom system prompt (default: agent prompt with tool list)

    Returns:
        Dict with: final_answer, tool_calls_made, iterations, model, elapsed_ms
    """
    start = time.time()
    max_iterations = max(1, min(int(max_iterations), 5))
    system = system_prompt or AGENT_SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Research this and provide a complete answer with real URLs: {query}"},
    ]

    tool_calls_made = []
    final_answer = ""

    async with httpx.AsyncClient(timeout=300.0) as client:
        for iteration in range(max_iterations):
            r = await client.post(
                OLLAMA_CHAT,
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_predict": 800},
                },
                timeout=300.0,
            )
            response = r.json()
            assistant_text = response.get("message", {}).get("content", "")

            if "[DONE]" in assistant_text:
                final_answer = assistant_text.split("[DONE]", 1)[-1].strip()
                if not final_answer:
                    final_answer = assistant_text.replace("[DONE]", "").strip()
                break

            tool_calls = _parse_tool_calls(assistant_text)

            if not tool_calls:
                final_answer = assistant_text
                break

            messages.append({"role": "assistant", "content": assistant_text})

            tool_results = []
            for tool_name, params in tool_calls[:3]:
                result = await _execute_tool(tool_name, params)
                tool_calls_made.append({
                    "tool": tool_name,
                    "params": params,
                    "result_length": len(result),
                })
                tool_results.append(f"[RESULT from {tool_name}]: {result}")

            combined_results = "\n\n".join(tool_results)
            messages.append({
                "role": "user",
                "content": f"Here are the tool results:\n{combined_results}\n\nNow synthesize a complete answer using the real data above. Output [DONE] followed by your final answer.",
            })
        else:
            final_answer = assistant_text if assistant_text else "Max iterations reached without final answer"

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "final_answer": final_answer,
        "tool_calls_made": tool_calls_made,
        "iterations": iteration + 1 if 'iteration' in dir() else 0,
        "model": model,
        "elapsed_ms": elapsed_ms,
        "query": query,
    }
