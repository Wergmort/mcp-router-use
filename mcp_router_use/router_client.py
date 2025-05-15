"""
Client for managing MCP servers and sessions.

This module provides a high-level client that manages MCP servers, connectors,
and sessions from configuration.
"""

import json
from typing import Any, Dict, List, Optional, Union

from .config import create_connector_from_config, load_config_file
from .connectors import MCPRouterConnector
from .logging import logger
from .session import MCPSession


class MCPRouterClient:
    """Client for managing MCP Router servers and sessions.

    This class provides a unified interface for working with MCP Router,
    handling configuration, connector creation, server registration, and session management.
    """

    def __init__(
        self,
        config: Union[str, Dict[str, Any], None] = None,
    ) -> None:
        """Initialize a new MCP Router client.

        Args:
            config: Either a dict containing configuration or a path to a JSON config file.
                   If None, an empty configuration is used.
        """
        self.config: Dict[str, Any] = {}
        self.sessions: Dict[str, MCPSession] = {}
        self.active_sessions: List[str] = []
        self.router_connector: Optional[MCPRouterConnector] = None

        # Load configuration if provided
        if config is not None:
            if isinstance(config, str):
                self.config = load_config_file(config)
            else:
                self.config = config

        # Setup the router connector if router_url is in config
        router_config = self.config.get("mcpRouter", {})
        if router_config and "router_url" in router_config:
            self.router_connector = MCPRouterConnector(
                router_url=router_config["router_url"],
                auth_token=router_config.get("auth_token"),
                headers=router_config.get("headers"),
            )

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "MCPRouterClient":
        """Create a MCPRouterClient from a dictionary.

        Args:
            config: The configuration dictionary.
        """
        return cls(config=config)

    @classmethod
    def from_config_file(cls, filepath: str) -> "MCPRouterClient":
        """Create a MCPRouterClient from a configuration file.

        Args:
            filepath: The path to the configuration file.
        """
        return cls(config=filepath)

    def add_server(
        self,
        name: str,
        server_config: Dict[str, Any],
    ) -> None:
        """Add a server configuration.

        Args:
            name: The name to identify this server.
            server_config: The server configuration.
        """
        if "mcpServers" not in self.config:
            self.config["mcpServers"] = {}

        self.config["mcpServers"][name] = server_config

    def remove_server(self, name: str) -> None:
        """Remove a server configuration.

        Args:
            name: The name of the server to remove.
        """
        if "mcpServers" in self.config and name in self.config["mcpServers"]:
            del self.config["mcpServers"][name]

            # If we removed an active session, remove it from active_sessions
            if name in self.active_sessions:
                self.active_sessions.remove(name)

    def get_server_names(self) -> List[str]:
        """Get the list of configured server names.

        Returns:
            List of server names.
        """
        return list(self.config.get("mcpServers", {}).keys())

    def save_config(self, filepath: str) -> None:
        """Save the current configuration to a file.

        Args:
            filepath: The path to save the configuration to.
        """
        with open(filepath, "w") as f:
            json.dump(self.config, f, indent=2)

    async def register_server_with_router(
        self, server_name: str
    ) -> Optional[str]:
        """Register a server with the MCP Router.

        This method registers the server configuration with the MCP Router
        and returns the assigned server ID.

        Args:
            server_name: The name of the server in the configuration.

        Returns:
            The server ID assigned by the MCP Router, or None if registration failed.

        Raises:
            ValueError: If no router connector is configured or the server doesn't exist.
        """
        if not self.router_connector:
            raise ValueError("No MCP Router connector configured")

        servers = self.config.get("mcpServers", {})
        if server_name not in servers:
            raise ValueError(f"Server '{server_name}' not found in config")

        server_config = servers[server_name]
        
        # If this is a command-based configuration, ensure it has the expected format
        if "command" in server_config and "args" in server_config:
            registration_config = {
                server_name: {
                    "command": server_config["command"],
                    "args": server_config["args"],
                    "env": server_config.get("env", {})
                }
            }
        else:
            # For other configs, wrap it with the server name
            registration_config = {server_name: server_config}
            
        # Register the server with the router
        logger.info(f"Registering server '{server_name}' with MCP Router")
        server_id = await self.router_connector.register_server(registration_config)
        
        if server_id:
            logger.info(f"Successfully registered server '{server_name}' with ID '{server_id}'")
            # Store the server ID in the config
            self.config["mcpServers"][server_name]["server_id"] = server_id
            return server_id
        else:
            logger.warning(f"Failed to register server '{server_name}' with MCP Router")
            return None

    async def start_server_in_router(self, server_name: str) -> bool:
        """Start a server in the MCP Router.

        Args:
            server_name: The name of the server to start.

        Returns:
            True if the server was started successfully, False otherwise.

        Raises:
            ValueError: If no router connector is configured or the server doesn't exist.
        """
        if not self.router_connector:
            raise ValueError("No MCP Router connector configured")

        servers = self.config.get("mcpServers", {})
        if server_name not in servers:
            raise ValueError(f"Server '{server_name}' not found in config")

        server_config = servers[server_name]
        server_id = server_config.get("server_id")
        
        if not server_id:
            # If the server hasn't been registered yet, register it first
            server_id = await self.register_server_with_router(server_name)
            if not server_id:
                return False
            
        # Start the server
        logger.info(f"Starting server '{server_name}' with ID '{server_id}' in MCP Router")
        return await self.router_connector._start_server(server_id)

    async def get_router_servers(self) -> List[Dict[str, Any]]:
        """Get a list of all servers registered with the MCP Router.

        Returns:
            A list of server information dictionaries.

        Raises:
            ValueError: If no router connector is configured.
        """
        if not self.router_connector:
            raise ValueError("No MCP Router connector configured")

        return await self.router_connector.get_all_servers()

    async def create_session(
        self, 
        server_name: str, 
        auto_initialize: bool = True,
        auto_register: bool = True
    ) -> MCPSession:
        """Create a session for the specified server.

        If auto_register is True and the server is not found in the MCP Router,
        the SDK will attempt to register and start the server automatically.

        Args:
            server_name: The name of the server to create a session for.
            auto_initialize: Whether to automatically initialize the session.
            auto_register: Whether to automatically register and start the server
                          if it doesn't exist in the MCP Router.

        Returns:
            The created MCPSession.

        Raises:
            ValueError: If no servers are configured or the specified server doesn't exist.
        """
        # Get server config
        servers = self.config.get("mcpServers", {})
        if not servers:
            raise ValueError("No MCP servers defined in config")

        if server_name not in servers:
            raise ValueError(f"Server '{server_name}' not found in config")

        server_config = servers[server_name]
        
        # If we're using the router connector
        if self.router_connector:
            # Check if this server needs registration with the router
            server_id = server_config.get("server_id")
            
            # If auto_register is enabled and the server doesn't have an ID
            if auto_register and not server_id:
                # Register and start the server
                server_id = await self.register_server_with_router(server_name)
                if server_id:
                    await self.start_server_in_router(server_name)
            
            # Create a router connector for this specific server
            router_url = self.config.get("mcpRouter", {}).get("router_url")
            if router_url:
                # Create a connector with the specific server ID
                connector = MCPRouterConnector(
                    router_url=router_url,
                    server_id=server_id,
                    auth_token=server_config.get("auth_token") or 
                              self.config.get("mcpRouter", {}).get("auth_token"),
                    headers=server_config.get("headers") or 
                            self.config.get("mcpRouter", {}).get("headers"),
                )
            else:
                # Fall back to standard connector creation
                connector = create_connector_from_config(server_config)
        else:
            # Use the standard connector creation
            connector = create_connector_from_config(server_config)

        # Create the session
        session = MCPSession(connector)
        if auto_initialize:
            await session.initialize()
            
        self.sessions[server_name] = session

        # Add to active sessions
        if server_name not in self.active_sessions:
            self.active_sessions.append(server_name)

        return session

    async def create_all_sessions(
        self,
        auto_initialize: bool = True,
        auto_register: bool = True,
    ) -> Dict[str, MCPSession]:
        """Create sessions for all configured servers.

        Args:
            auto_initialize: Whether to automatically initialize the sessions.
            auto_register: Whether to automatically register and start servers
                          if they don't exist in the MCP Router.

        Returns:
            Dictionary mapping server names to their MCPSession instances.

        Raises:
            ValueError: If no servers are configured.
        """
        # Get server config
        servers = self.config.get("mcpServers", {})
        if not servers:
            raise ValueError("No MCP servers defined in config")

        # Create sessions for all servers
        for name in servers:
            await self.create_session(name, auto_initialize, auto_register)

        return self.sessions

    def get_session(self, server_name: str) -> MCPSession:
        """Get an existing session.

        Args:
            server_name: The name of the server to get the session for.

        Returns:
            The MCPSession for the specified server.

        Raises:
            ValueError: If the specified session doesn't exist.
        """
        if server_name not in self.sessions:
            raise ValueError(f"No session exists for server '{server_name}'")

        return self.sessions[server_name]

    def get_all_active_sessions(self) -> Dict[str, MCPSession]:
        """Get all active sessions.

        Returns:
            Dictionary mapping server names to their MCPSession instances.
        """
        return {name: self.sessions[name] for name in self.active_sessions if name in self.sessions}

    async def close_session(self, server_name: str) -> None:
        """Close a session.

        Args:
            server_name: The name of the server to close the session for.

        Raises:
            ValueError: If the specified session doesn't exist.
        """
        # Check if the session exists
        if server_name not in self.sessions:
            logger.warning(f"No session exists for server '{server_name}', nothing to close")
            return

        # Get the session
        session = self.sessions[server_name]

        try:
            # Disconnect from the session
            logger.debug(f"Closing session for server '{server_name}'")
            await session.disconnect()
        except Exception as e:
            logger.error(f"Error closing session for server '{server_name}': {e}")
        finally:
            # Remove the session regardless of whether disconnect succeeded
            del self.sessions[server_name]

            # Remove from active_sessions
            if server_name in self.active_sessions:
                self.active_sessions.remove(server_name)

    async def close_all_sessions(self) -> None:
        """Close all active sessions.

        This method ensures all sessions are closed even if some fail.
        """
        # Get a list of all session names first to avoid modification during iteration
        server_names = list(self.sessions.keys())
        errors = []

        for server_name in server_names:
            try:
                logger.debug(f"Closing session for server '{server_name}'")
                await self.close_session(server_name)
            except Exception as e:
                error_msg = f"Failed to close session for server '{server_name}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Log summary if there were errors
        if errors:
            logger.error(f"Encountered {len(errors)} errors while closing sessions")
        else:
            logger.debug("All sessions closed successfully")
