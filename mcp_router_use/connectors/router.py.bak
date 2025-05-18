"""
MCP Router connector for MCP implementations.

This module provides a connector for communicating with MCP Router,
which acts as an aggregator for MCP servers.
"""

import aiohttp
from typing import Any, Dict, List, Optional

from mcp import ClientSession

from ..logging import logger
from ..task_managers import SseConnectionManager
from .base import BaseConnector


class MCPRouterConnector(BaseConnector):
    """Connector for MCP Router implementation.

    This connector communicates with MCP Router which aggregates multiple
    MCP servers. It handles server registration, starting, and MCP API calls.
    """

    def __init__(
        self,
        router_url: str,
        server_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 5,
        sse_read_timeout: float = 60 * 5,
    ):
        """Initialize a new MCP Router connector.

        Args:
            router_url: The base URL of the MCP Router.
            server_id: Optional ID of the MCP server to use.
            auth_token: Optional authentication token.
            headers: Optional additional headers.
            timeout: Timeout for HTTP operations in seconds.
            sse_read_timeout: Timeout for SSE read operations in seconds.
        """
        super().__init__()
        self.router_url = router_url.rstrip("/")
        self.server_id = server_id
        self.auth_token = auth_token
        self.headers = headers or {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        self.timeout = timeout
        self.sse_read_timeout = sse_read_timeout
        
        # Router API endpoints
        self.mcp_endpoint = f"{self.router_url}/mcp"
        self.api_endpoint = f"{self.router_url}/api"
        self.servers_endpoint = f"{self.api_endpoint}/servers"

    async def connect(self) -> None:
        """Establish a connection to the MCP Router."""
        if self._connected:
            logger.debug("Already connected to MCP Router")
            return

        logger.debug(f"Connecting to MCP Router: {self.router_url}")
        try:
            # If a server ID is specified, make sure it's started
            if self.server_id:
                await self._ensure_server_running(self.server_id)
            
            # Create the SSE connection to the MCP Router's /mcp endpoint
            sse_url = self.mcp_endpoint
            
            # Create and start the connection manager
            self._connection_manager = SseConnectionManager(
                sse_url, self.headers, self.timeout, self.sse_read_timeout
            )
            read_stream, write_stream = await self._connection_manager.start()

            # Create the client session
            self.client = ClientSession(read_stream, write_stream, sampling_callback=None)
            await self.client.__aenter__()

            # Mark as connected
            self._connected = True
            logger.debug(f"Successfully connected to MCP Router: {self.router_url}")

        except Exception as e:
            logger.error(f"Failed to connect to MCP Router: {e}")

            # Clean up any resources if connection failed
            await self._cleanup_resources()

            # Re-raise the original exception
            raise

    async def _ensure_server_running(self, server_id: str) -> None:
        """Ensure that the specified server is running in the MCP Router.

        Args:
            server_id: The ID of the server to ensure is running.
        
        Raises:
            RuntimeError: If the server is not found or cannot be started.
        """
        try:
            # Check if the server exists and get its status
            server_info = await self._get_server_info(server_id)
            
            # If the server exists but is not running, start it
            if server_info and server_info.get("status") != "online":
                logger.info(f"Starting MCP server '{server_id}'")
                await self._start_server(server_id)
            elif server_info:
                logger.debug(f"MCP server '{server_id}' is already running")
            else:
                raise RuntimeError(f"MCP server '{server_id}' not found in MCP Router")
                
        except Exception as e:
            logger.error(f"Failed to ensure MCP server '{server_id}' is running: {e}")
            raise
    
    async def _get_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific server from the MCP Router.
        
        Args:
            server_id: The ID of the server.
            
        Returns:
            Server information or None if the server is not found.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get all servers and find the one with the matching ID
                async with session.get(
                    self.servers_endpoint,
                    headers=self.headers,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        servers = await response.json()
                        for server in servers:
                            if server.get("id") == server_id:
                                return server
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error when getting server info: {e}")
            return None
    
    async def _start_server(self, server_id: str) -> bool:
        """Start a server in the MCP Router.
        
        Args:
            server_id: The ID of the server to start.
            
        Returns:
            True if the server was started successfully, False otherwise.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.servers_endpoint}/{server_id}/start",
                    headers=self.headers,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success"):
                            logger.info(f"Successfully started MCP server '{server_id}'")
                            return True
                        else:
                            logger.warning(f"Failed to start MCP server '{server_id}': {result.get('message')}")
                    else:
                        error_text = await response.text()
                        logger.warning(f"Failed to start MCP server '{server_id}': {response.status} - {error_text}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error when starting server: {e}")
            return False
    
    async def register_server(self, server_config: Dict[str, Any]) -> Optional[str]:
        """Register a new server with the MCP Router.
        
        Args:
            server_config: The server configuration including command, args, and env.
            
        Returns:
            The ID of the registered server if successful, None otherwise.
        """
        try:
            # Structure the server configuration for the MCP Router API
            payload = {}
            # Check if we have a direct server config or one with a name
            if "command" in server_config and "args" in server_config:
                # Create a wrapper with a generated name
                name = server_config.get("name", f"server_{hash(str(server_config))}")
                payload[name] = {
                    "command": server_config["command"],
                    "args": server_config["args"],
                    "env": server_config.get("env", {})
                }
            else:
                # Assume it's already in the right format
                payload = server_config
                
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.servers_endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    if response.status in (200, 201):
                        result = await response.json()
                        if "results" in result and len(result["results"]) > 0:
                            # Find the first successful result
                            for server_result in result["results"]:
                                if server_result.get("success"):
                                    server_name = server_result.get("name")
                                    logger.info(f"Successfully registered MCP server '{server_name}'")
                                    return server_name
                        logger.warning(f"No servers were successfully registered: {result}")
                    else:
                        error_text = await response.text()
                        logger.warning(f"Failed to register MCP server: {response.status} - {error_text}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error when registering server: {e}")
            return None
    
    async def get_all_servers(self) -> List[Dict[str, Any]]:
        """Get a list of all available servers from the MCP Router.
        
        Returns:
            A list of server information dictionaries.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.servers_endpoint,
                    headers=self.headers,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Failed to get server list: {response.status}")
                        return []
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error when getting server list: {e}")
            return []
