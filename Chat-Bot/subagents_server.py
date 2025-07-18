#!/usr/bin/env python3
"""
Sub-Agents MCP Server

This MCP server provides delegation functionality for multi-agent systems.
It allows parent agents to call sub-agents through a single tool interface.
"""

import asyncio
import logging
from typing import Any, Sequence
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
import aiohttp

# Import the sub-agents mapping function
from mcp_servers_list import get_subagents_mapping

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance
server = Server("subagents-server")

# API endpoint configuration
API_BASE_URL = "http://localhost:8001"  # Adjust if needed
QUERY_ENDPOINT = f"{API_BASE_URL}/chat/api/subagent"

async def make_api_call(subagent_id: int, subagent_name: str, subagent_token: str, prompt: str):
    """
    Make the actual API call to the sub-agent in the background.
    This runs independently and doesn't block the parent agent.
    """
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "token": subagent_token,
                "Content-Type": "application/json"
            }
            payload = {
                "prompt": prompt
            }
            
            logger.info(f"🌐 Making API call to {QUERY_ENDPOINT} for sub-agent {subagent_id}")
            async with session.post(QUERY_ENDPOINT, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ Background task: API call failed for sub-agent {subagent_id} with status {response.status}: {error_text}")
                else:
                    logger.info(f"✅ Background task: Successfully delegated to sub-agent {subagent_id} ({subagent_name})")
    except Exception as e:
        logger.error(f"❌ Background task: Error in API call for sub-agent {subagent_id}: {str(e)}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools for sub-agent delegation.
    Returns the call_subagent tool that parent agents can use.
    """
    return [
        types.Tool(
            name="call_subagent",
            description="Delegate a task to a specific sub-agent by ID. This is an asynchronous operation - the sub-agent will process the task in the background while you continue with your work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subagent_id": {
                        "type": "integer",
                        "description": "The ID of the sub-agent to call (e.g., 279 for first subagent, 280 for second subagent)"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The task description/prompt to send to the sub-agent"
                    }
                },
                "required": ["subagent_id", "prompt"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Handle tool calls for sub-agent delegation.
    Currently supports the call_subagent tool.
    """
    if name == "call_subagent":
        return await call_subagent(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def call_subagent(arguments: dict) -> list[types.TextContent]:
    """
    Delegate a task to a specific sub-agent by making an asynchronous API call.
    Returns immediately after scheduling the task, doesn't wait for completion.
    
    Args:
        arguments: Dictionary containing:
            - subagent_id (int): ID of the target sub-agent
            - prompt (str): Task description to send to sub-agent
    
    Returns:
        List of TextContent confirming the task was scheduled
    """
    try:
        subagent_id = arguments.get("subagent_id")
        prompt = arguments.get("prompt")
        
        # Validate required parameters
        if not subagent_id:
            return [types.TextContent(
                type="text",
                text="Error: subagent_id parameter is required"
            )]
        
        if not prompt:
            return [types.TextContent(
                type="text", 
                text="Error: prompt parameter is required"
            )]
        
        # Get sub-agents mapping
        subagents_mapping = get_subagents_mapping()
        
        # Debug logging for mapping state
        logger.info(f"🔍 Debug: Sub-agents mapping contains {len(subagents_mapping)} entries")
        if subagents_mapping:
            available_ids = list(subagents_mapping.keys())
            logger.info(f"🔍 Debug: Available sub-agent IDs: {available_ids}")
        else:
            logger.warning(f"⚠️ Debug: Sub-agents mapping is empty!")
        
        # Convert subagent_id to string since JSON keys are strings
        subagent_id_str = str(subagent_id)
        
        # Check if the sub-agent exists in the mapping
        if subagent_id_str not in subagents_mapping:
            return [types.TextContent(
                type="text",
                text=f"Error: Sub-agent {subagent_id} not found or not available. Available sub-agents: {list(subagents_mapping.keys()) if subagents_mapping else 'None'}"
            )]
        
        # Get sub-agent information from mapping
        subagent_info = subagents_mapping[subagent_id_str]
        subagent_token = subagent_info.get("token")
        subagent_name = subagent_info.get("name", "Unknown")
        
        if not subagent_token:
            return [types.TextContent(
                type="text",
                text=f"Error: No token available for sub-agent {subagent_id}"
            )]
        
        # Create the background task without tracking
        asyncio.create_task(make_api_call(subagent_id, subagent_name, subagent_token, prompt))
        
        # Return immediately with confirmation
        return [types.TextContent(
            type="text",
            text=f"Task successfully delegated to sub-agent {subagent_id} ({subagent_name}). The sub-agent will process this task in the background while you continue with your work."
        )]
        
    except Exception as e:
        logger.error(f"❌ Error in call_subagent: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error delegating to sub-agent: {str(e)}"
        )]

async def main():
    """Main entry point for the MCP server."""
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="subagents-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    logger.info("🚀 Starting Sub-Agents MCP Server...")
    asyncio.run(main()) 