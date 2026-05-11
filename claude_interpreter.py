import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from config import PROJECT_ROOT
from prompts import build_system_prompt
from schemas import INTERPRETATION_SCHEMA


def _find_claude():
    found = shutil.which("claude")
    if found:
        return found
    candidates = [
        "/opt/homebrew/bin/claude",
        "/usr/local/bin/claude",
        os.path.expanduser("~/.npm-global/bin/claude"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


CLAUDE_PATH = _find_claude()


def _resolve_claude_cmd():
    if not CLAUDE_PATH:
        return None

    if sys.platform != "win32" or not CLAUDE_PATH.lower().endswith((".cmd", ".ps1")):
        return [CLAUDE_PATH]

    cmd_dir = os.path.dirname(CLAUDE_PATH)
    pkg_dir = os.path.join(cmd_dir, "node_modules", "@anthropic-ai", "claude-code")
    pkg_json_path = os.path.join(pkg_dir, "package.json")

    if os.path.exists(pkg_json_path):
        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                pkg = json.load(f)

            bin_field = pkg.get("bin", {})
            if isinstance(bin_field, str):
                entry = bin_field
            elif isinstance(bin_field, dict):
                entry = bin_field.get("claude", "")
            else:
                entry = ""

            if entry:
                entry_path = os.path.normpath(os.path.join(pkg_dir, entry))
                if os.path.exists(entry_path):
                    if entry_path.lower().endswith(".exe"):
                        return [entry_path]
                    node = shutil.which("node")
                    if node:
                        return [node, entry_path]
        except Exception:
            pass

    return [CLAUDE_PATH]


CLAUDE_CMD = _resolve_claude_cmd()


def interpret_query(user_query: str) -> dict:
    if not CLAUDE_CMD:
        raise RuntimeError("Claude CLI not found in PATH")

    system_prompt = build_system_prompt()
    prompt = f"{system_prompt}\n\n---\n\nUser query: {user_query}"
    schema_str = json.dumps(INTERPRETATION_SCHEMA)

    result = subprocess.run(
        [*CLAUDE_CMD, "-p", "--model", "sonnet", "--output-format", "json",
         "--json-schema", schema_str],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI failed: {result.stderr[:500]}")

    response = json.loads(result.stdout)
    structured_output = response.get("structured_output")
    if structured_output is None:
        structured_output = response.get("result", response)
        if isinstance(structured_output, str):
            structured_output = json.loads(structured_output)

    return structured_output
