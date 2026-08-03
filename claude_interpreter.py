import asyncio
import json
import logging
import os

from config import PROJECT_ROOT
from prompts import build_system_prompt
from schemas import INTERPRETATION_SCHEMA

logger = logging.getLogger(__name__)

INTERPRET_TIMEOUT_S = 120


async def interpret_query(user_query: str) -> dict:
    # Lazy import so module import (and anything that only touches other
    # symbols here) never requires the SDK to be installed.
    from claude_agent_sdk import ClaudeAgentOptions, query

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    options = ClaudeAgentOptions(
        tools=[],  # no built-ins: pure NL->JSON interpretation
        setting_sources=[],  # hermetic: no CLAUDE.md/skills/hooks leak in
        permission_mode="dontAsk",
        system_prompt=build_system_prompt(),
        model="sonnet",
        max_turns=10,  # headroom for structured-output retries
        max_budget_usd=None,  # no cost ceiling: never abort mid-interpretation
        output_format={"type": "json_schema", "schema": INTERPRETATION_SCHEMA},
        cwd=str(PROJECT_ROOT),
        env={"ANTHROPIC_API_KEY": api_key} if api_key else {},
        stderr=lambda line: logger.debug("[claude-cli] %s", line),
    )

    prompt = f"User query: {user_query}"
    try:
        out = await asyncio.wait_for(_consume(query, prompt, options), INTERPRET_TIMEOUT_S)
    except asyncio.TimeoutError:
        raise RuntimeError(f"Claude interpretation timed out after {INTERPRET_TIMEOUT_S}s")
    return _extract(out)


async def _consume(query_fn, prompt: str, options) -> dict:
    """Drain the query() stream into a plain dict, never raising mid-stream.

    query() raises after yielding the error ResultMessage, so whatever
    arrived first wins; don't break on the result — trailing system
    events can follow it.
    """
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

    out: dict = {
        "subtype": None,
        "is_error": False,
        "result": None,
        "structured_output": None,
        "last_text": None,
        "error": None,
    }
    try:
        async for msg in query_fn(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        out["last_text"] = block.text
            elif isinstance(msg, ResultMessage):
                out["subtype"] = msg.subtype
                out["is_error"] = msg.is_error
                out["result"] = msg.result
                out["structured_output"] = getattr(msg, "structured_output", None)
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def _extract(out: dict) -> dict:
    structured = out.get("structured_output")
    if isinstance(structured, dict):
        return structured

    if out.get("subtype") == "success" and not out.get("is_error"):
        for candidate in (out.get("result"), out.get("last_text")):
            if isinstance(candidate, dict):
                return candidate
            if isinstance(candidate, str):
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

    if out.get("subtype") == "error_max_structured_output_retries":
        raise RuntimeError("Claude could not produce output matching the interpretation schema")
    if out.get("subtype") is None:
        raise RuntimeError(f"Claude agent failed to start: {out.get('error') or 'no result received'}")
    detail = out.get("result") or out.get("error") or out.get("last_text") or "unknown error"
    raise RuntimeError(f"Claude agent error ({out.get('subtype')}): {str(detail)[:500]}")
