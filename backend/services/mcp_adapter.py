"""MCP adapter — wraps external MCP tools into the ToolRegistry.

Reads a YAML config mapping external tool servers to roles, then registers
proxy tools that forward calls to MCP servers.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "mcp_tools.yaml"


def load_mcp_config() -> dict:
    """Load MCP tools configuration."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        from backend.services.yaml_util import safe_load_yaml_dict
        return safe_load_yaml_dict(f.read())


def register_mcp_tools(registry, config: Optional[dict] = None) -> int:
    """Register MCP tools from config into a ToolRegistry.

    Config format:
        servers:
          github:
            command: "npx @modelcontextprotocol/server-github"
            tools:
              - name: create_issue
                roles: [program_coordinator, executive_director]
              - name: list_issues
                roles: [drum_major, program_coordinator]

    Returns number of tools registered.
    """
    if config is None:
        config = load_mcp_config()

    registered = 0
    servers = config.get("servers", {})

    for server_name, server_config in servers.items():
        tools = server_config.get("tools", [])
        for tool_def in tools:
            tool_name = f"{server_name}.{tool_def['name']}"
            roles = tool_def.get("roles", [])

            # Create a proxy function that logs the call
            # Actual MCP execution would happen via subprocess/stdio
            def make_proxy(sname, tname):
                def proxy(db, **kwargs):
                    logger.info("MCP call: %s.%s with args %s", sname, tname, kwargs)
                    return {
                        "status": "mcp_proxy",
                        "server": sname,
                        "tool": tname,
                        "args": kwargs,
                        "message": f"MCP tool {sname}.{tname} called (proxy mode)",
                    }
                return proxy

            schema = {
                "name": tool_name,
                "description": f"MCP tool: {server_name}/{tool_def['name']}. {tool_def.get('description', '')}",
                "input_schema": tool_def.get("schema", {
                    "type": "object",
                    "properties": {},
                }),
            }

            registry.register(tool_name, make_proxy(server_name, tool_def["name"]), schema)
            registered += 1
            logger.info("Registered MCP tool %s for roles %s", tool_name, roles)

    return registered
