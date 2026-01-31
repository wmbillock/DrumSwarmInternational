"""MCP Instrument Pattern — consume external MCP servers as tools.

Adapter wraps external MCP tools into the ToolRegistry with namespace prefixes.
Configuration via YAML maps tools to roles.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import yaml

from backend.services.tool_executor import ToolRegistry

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "mcp_instruments.yaml"


def load_instrument_config(path: Optional[str] = None) -> dict:
    """Load MCP instrument configuration from YAML."""
    config_path = Path(path) if path else CONFIG_PATH
    if not config_path.exists():
        return {"instruments": []}
    with open(config_path) as f:
        return yaml.safe_load(f) or {"instruments": []}


def _create_mcp_tool_wrapper(server_name: str, tool_name: str, server_config: dict):
    """Create a callable wrapper that invokes an external MCP tool."""
    def mcp_tool_call(**kwargs):
        # Placeholder: real implementation would use MCP client protocol
        # to call the external server's tool
        return {
            "server": server_name,
            "tool": tool_name,
            "args": kwargs,
            "status": "mcp_call_placeholder",
            "note": "Real MCP client integration would execute this tool via the MCP protocol.",
        }
    return mcp_tool_call


def register_mcp_instruments(registry: ToolRegistry, config: Optional[dict] = None) -> list[str]:
    """Register external MCP tools into the ToolRegistry.

    Tools are namespaced: e.g. github.create_issue, sentry.list_errors.

    Returns list of registered tool names.
    """
    if config is None:
        config = load_instrument_config()

    registered = []
    for instrument in config.get("instruments", []):
        server_name = instrument.get("name", "unknown")
        server_config = instrument.get("config", {})
        tools = instrument.get("tools", [])
        allowed_roles = instrument.get("roles", [])

        for tool_def in tools:
            tool_name = tool_def.get("name", "")
            namespaced_name = f"{server_name}.{tool_name}"
            description = tool_def.get("description", f"MCP tool: {namespaced_name}")
            input_schema = tool_def.get("input_schema", {"type": "object", "properties": {}})

            wrapper = _create_mcp_tool_wrapper(server_name, tool_name, server_config)
            schema = {
                "name": namespaced_name,
                "description": description,
                "input_schema": input_schema,
            }
            registry.register(namespaced_name, wrapper, schema)
            registered.append(namespaced_name)
            logger.info("Registered MCP instrument: %s (roles: %s)", namespaced_name, allowed_roles)

    return registered
