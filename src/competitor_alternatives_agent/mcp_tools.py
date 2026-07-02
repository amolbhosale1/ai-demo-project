from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.sessions import SSEConnection, StdioConnection
from langchain_mcp_adapters.tools import load_mcp_tools


async def load_mcp_servers_from_config(
    config_path: str,
    allowed_servers: set[str] | None = None,
) -> list[Any]:
    with Path(config_path).open(encoding="utf-8") as handle:
        config = json.load(handle)
    all_tools: list[Any] = []
    mcp_servers = config.get("mcp_servers", {})
    for server_name, server_config in mcp_servers.items():
        if allowed_servers is not None and server_name not in allowed_servers:
            continue
        server_type = str(
            server_config.get("transport", server_config.get("type", "stdio"))
        ).strip().lower()
        connection = None
        if server_type == "stdio":
            connection = StdioConnection(
                transport="stdio",
                command=server_config.get("command"),
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
            )
        elif server_type == "sse":
            connection = SSEConnection(
                transport="sse",
                url=server_config.get("url"),
                headers=server_config.get("headers"),
            )
        if connection is None:
            continue
        tools = await load_mcp_tools(
            session=None,
            connection=connection,
            server_name=server_name,
            tool_name_prefix=True,
        )
        all_tools.extend(tools)
    return all_tools


def load_mcp_servers_sync(
    config_path: str,
    allowed_servers: set[str] | None = None,
) -> list[Any]:
    return asyncio.run(load_mcp_servers_from_config(config_path, allowed_servers=allowed_servers))

