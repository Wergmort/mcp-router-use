"""
Configuration loader for MCP session.

This module provides functionality to load MCP configuration from JSON files
and create appropriate connectors for MCP Router.
"""

import json
from typing import Any, Dict

from .connectors import BaseConnector, HttpConnector, StdioConnector, WebSocketConnector
from .logging import logger


def load_config_file(filepath: str) -> Dict[str, Any]:
    """Load a configuration file.

    Args:
        filepath: Path to the configuration file

    Returns:
        The parsed configuration
    """
    with open(filepath) as f:
        return json.load(f)


def create_connector_from_config(config: Dict[str, Any]) -> BaseConnector:
    """Create a connector based on server configuration.

    Note: For production use, only the HTTP connector for MCP Router is supported.
          Other connectors are maintained for testing purposes.

    Args:
        config: The server configuration section

    Returns:
        A configured connector instance
    """
    # HTTP connector for MCP Router connection (primary supported connector)
    if "url" in config:
        return HttpConnector(
            base_url=config["url"],
            headers=config.get("headers", None),
            auth_token=config.get("auth_token", None),
        )

    # Legacy connectors - maintained for testing
    # Standard stdio connector (command-based)
    elif "command" in config and "args" in config:
        logger.warning(
            "StdioConnector is not recommended for production use. "
            "Please use MCP Router connection instead."
        )
        return StdioConnector(
            command=config["command"],
            args=config["args"],
            env=config.get("env", None),
        )

    # WebSocket connector
    elif "ws_url" in config:
        logger.warning(
            "WebSocketConnector is not recommended for production use. "
            "Please use MCP Router connection instead."
        )
        return WebSocketConnector(
            url=config["ws_url"],
            headers=config.get("headers", None),
            auth_token=config.get("auth_token", None),
        )
        
    raise ValueError("Cannot determine connector type from config. For production use, specify 'url' for MCP Router connection.")
