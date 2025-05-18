# MCP Router Use

An SDK for using MCP Router to manage and communicate with MCP servers programmatically. MCP Router Use is designed to be a drop-in replacement for [mcp-use](https://github.com/modelhouse/mcp-use), maintaining API compatibility while using MCP Router under the hood.

## Overview

MCP Router Use is a Python SDK that allows you to interact with MCP servers through the MCP Router. It maintains compatibility with the mcp-use API while leveraging MCP Router's capabilities to manage servers. The SDK provides a simplified interface for:

- Registering MCP servers with MCP Router
- Starting and stopping MCP servers
- Creating sessions to communicate with MCP servers
- Calling tools exposed by MCP servers

The SDK handles the complexities of server management, allowing you to focus on using the MCP tools.

## Installation

```bash
pip install mcp-router-use
```

## Configuration

To use the SDK, you need to create a configuration object that specifies:

1. The MCP Router URL and authentication details
2. The MCP servers you want to use

Here's an example configuration:

```python
config = {
    "mcpRouter": {
        "router_url": "http://localhost:3282",
        "auth_token": "your_token_here",  # Optional
    },
    "mcpServers": {
        "puppeteer": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
            "env": {
                "PUPPETEER_LAUNCH_OPTIONS": "{ \"headless\": false }",
                "ALLOW_DANGEROUS": "true"
            }
        }
    }
}
```

## Usage

### Basic Usage

```python
import asyncio
from mcp_router_use import MCPClient

async def main():
    # Create a client with your configuration
    client = MCPClient(config=config)
    
    # Create a session with auto-registration
    session = await client.create_session("puppeteer", auto_register=True)
    
    # Call a tool
    result = await session.call_tool("browser.navigate", {"url": "https://www.example.com"})
    
    # Disconnect when done
    await session.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Using MCPRouterClient

For compatibility and convenience, the SDK also provides an `MCPRouterClient` class that enables auto-registration by default:

```python
import asyncio
from mcp_router_use import MCPRouterClient

async def main():
    # Create a client with your configuration
    client = MCPRouterClient(config=config)
    
    # Create a session (auto_register=True by default)
    session = await client.create_session("puppeteer")
    
    # List available tools
    for tool in session.tools:
        print(f"Tool: {tool['name']} - {tool['description']}")
    
    # Call a tool
    result = await session.call_tool("browser.navigate", {"url": "https://www.example.com"})
    
    # Disconnect when done
    await session.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Loading Configuration from a File

You can also load your configuration from a JSON file:

```python
import asyncio
from mcp_router_use import MCPClient

async def main():
    # Load configuration from a file
    client = MCPClient(config="config.json")
    
    # Use the client as before
    session = await client.create_session("puppeteer", auto_register=True)
    
    # ...

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage

### Managing Servers Manually

If you need more control over server registration and startup:

```python
import asyncio
from mcp_router_use import MCPClient

async def main():
    client = MCPClient(config=config)
    
    # Register a server manually
    server_id = await client.register_server_with_router("puppeteer")
    print(f"Server registered with ID: {server_id}")
    
    # Start the server manually
    started = await client.start_server_in_router("puppeteer")
    if started:
        print("Server started successfully")
    
    # Get a list of all registered servers
    servers = await client.get_router_servers()
    for server in servers:
        print(f"Server: {server.get('name')} - Status: {server.get('status')}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Using Multiple Servers

You can manage and use multiple MCP servers through the same client:

```python
import asyncio
from mcp_router_use import MCPClient

async def main():
    # Configuration with multiple servers
    config = {
        "mcpRouter": {
            "router_url": "http://localhost:3282",
        },
        "mcpServers": {
            "puppeteer": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
                "env": {
                    "PUPPETEER_LAUNCH_OPTIONS": "{ \"headless\": false }"
                }
            },
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "env": {}
            }
        }
    }
    
    client = MCPClient(config=config)
    
    # Create sessions for different servers
    browser_session = await client.create_session("puppeteer", auto_register=True)
    fs_session = await client.create_session("filesystem", auto_register=True)
    
    # Use both sessions
    await browser_session.call_tool("browser.navigate", {"url": "https://www.example.com"})
    files = await fs_session.call_tool("fs.readdir", {"path": "."})
    
    # Disconnect sessions when done
    await browser_session.disconnect()
    await fs_session.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### MCPClient

The main client class for interacting with MCP Router.

#### Constructor

```python
MCPClient(config: Union[str, Dict[str, Any], None] = None)
```

- `config`: Either a dictionary containing configuration or a path to a JSON config file.

#### Methods

- `async create_session(server_name: str, auto_initialize: bool = True, auto_register: bool = True) -> MCPSession`: 
  Creates a session for the specified server. If `auto_register` is True, registers and starts the server if needed.

- `async register_server_with_router(server_name: str) -> Optional[str]`: 
  Registers a server with the MCP Router and returns the assigned server ID.

- `async start_server_in_router(server_name: str) -> bool`: 
  Starts a registered server in the MCP Router.

- `async get_router_servers() -> List[Dict[str, Any]]`: 
  Gets a list of all servers registered with the MCP Router.

### MCPRouterClient

A specialized client that extends MCPClient with default auto-registration.

### MCPSession

Represents a session with an MCP server.

#### Methods

- `async connect() -> None`: 
  Connects to the MCP server.

- `async disconnect() -> None`: 
  Disconnects from the MCP server.

- `async initialize() -> dict[str, Any]`: 
  Initializes the session and discovers available tools.

- `async discover_tools() -> list[dict[str, Any]]`: 
  Discovers available tools from the MCP server.

- `async call_tool(name: str, arguments: dict[str, Any]) -> Any`: 
  Calls a tool with the given arguments.

## Troubleshooting

### Common Issues

1. **Connection Error**: Ensure MCP Router is running and accessible at the configured URL.

2. **Authentication Error**: Check if your `auth_token` is correct and properly configured.

3. **Server Registration Failure**: Make sure the server configuration is correct and the necessary packages are installed.

4. **Server Start Failure**: Check the MCP Router logs for errors during server startup.

## Compatibility with mcp-use

MCP Router Use is designed to be a drop-in replacement for mcp-use. If you're already using mcp-use in your project, you can switch to MCP Router Use with minimal changes to your code:

```python
# Before: with mcp-use
from mcp_use import MCPClient

# After: with MCP Router Use
from mcp_router_use import MCPClient
```

The key differences are:

1. MCP Router Use communicates with MCP servers through MCP Router's `/mcp` endpoint
2. MCP Router Use can automatically register and start servers if they don't exist
3. MCP Router Use requires MCP Router to be running and accessible

All public methods and classes maintain the same signatures and behavior, ensuring a smooth transition.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
