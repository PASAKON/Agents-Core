"""CTO orchestrator. Reads CEO request, breaks into tasks, delegates, reviews, merges."""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    SdkMcpTool,
    TextBlock,
    create_sdk_mcp_server,
    tool,
)

from lib import org_tools_registry as registry
from lib.config import role as get_role, cxo_provider_overrides
from lib.db import register_cxo_session
from lib.logger import get_logger
from lib.notify import info, success

ROOT = Path(__file__).resolve().parent.parent
ROLE = "cto"
log = get_logger(ROLE)


# --- Tool definitions (Claude SDK MCP) ---
#
# One generic wrapper per lib/org_tools_registry.py spec — arg parsing,
# response formatting, the cross-CTO ownership gate and error handling all
# live once in registry.dispatch(). This only bridges claude_agent_sdk's
# dict-in/dict-out @tool() protocol to it; unlike FastMCP (see
# runners/cto_mcp_server.py), @tool()'s input_schema is an explicit dict
# passed at decoration time, not introspected from a function signature,
# so no per-tool function body is needed at all.

def _build_tool(spec: registry.ToolSpec) -> "SdkMcpTool[Any]":
    input_schema = {p.name: p.type for p in spec.params}

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        kwargs = {p.name: args[p.name] for p in spec.params if p.name in args}
        text = await registry.dispatch(spec.name, **kwargs)
        result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
        if text.startswith("ERROR:"):
            result["isError"] = True
        return result

    handler.__name__ = f"t_{spec.name}"
    return tool(spec.name, spec.description, input_schema)(handler)


ALL_TOOLS: dict[str, "SdkMcpTool[Any]"] = {
    spec.name: _build_tool(spec) for spec in registry.REGISTRY
}

# scripts/test_owner_cto_routing.py drives the ownership gate directly
# through these three tools by their historical attribute names — kept as
# aliases into ALL_TOOLS (same objects, no separate logic).
t_delegate = ALL_TOOLS["delegate_task"]
t_merge = ALL_TOOLS["merge_task"]
t_reopen = ALL_TOOLS["reopen_task"]


# --- CTO entrypoint ---

def _system_prompt() -> str:
    return (ROOT / "roles" / "cto.md").read_text()


def _cleanup_zombies() -> None:
    script = ROOT / "scripts" / "cleanup-zombies.sh"
    try:
        r = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, timeout=10
        )
        log.info(r.stdout.strip() or "cleanup-zombies: no output")
    except Exception as exc:
        log.debug(f"cleanup-zombies skipped: {exc}")


async def run(ceo_request: str) -> str:
    log.info(f"CEO request: {ceo_request[:200]}")
    info(f"CTO received CEO request")
    _cleanup_zombies()
    _sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID", "")
    if _sid:
        try:
            register_cxo_session("cto", _sid)
        except Exception:
            pass

    server = create_sdk_mcp_server(
        name="org-cto",
        version="1.0.0",
        tools=list(ALL_TOOLS.values()),
    )

    # Flag-gated GLM offload (CXO_MODEL_PROVIDER). Default OFF -> Claude path.
    # When set, inject the provider env + swap model; drop the Claude-only
    # fallback id + --effort (the GLM endpoint rejects both).
    _ov = cxo_provider_overrides("cto")
    _model = get_role("cto")["model"]
    _fallback = get_role("cto").get("fallback_model")
    _effort: str | None = "max"
    if _ov:
        os.environ.update(_ov["env"])
        _model = _ov["model"]
        _fallback = None
        _effort = _ov["effort"]

    opts = dict(
        model=_model,
        system_prompt=_system_prompt(),
        permission_mode="acceptEdits",
        mcp_servers={"org": server},
        allowed_tools=[f"mcp__org__{name}" for name in ALL_TOOLS] + ["Read", "Grep", "Glob"],
        cwd=str(ROOT),
    )
    if _fallback:
        opts["fallback_model"] = _fallback
    if _effort:
        opts["effort"] = _effort
    options = ClaudeAgentOptions(**opts)

    final = []
    async with ClaudeSDKClient(options=options) as client:
        await client.query(ceo_request)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        log.info(f"CTO: {block.text[:500]}")
                        final.append(block.text)

    result = "\n".join(final)
    success("CTO done")
    return result


if __name__ == "__main__":
    import sys
    request = " ".join(sys.argv[1:]) or "list known projects and their git remotes"
    print(asyncio.run(run(request)))
