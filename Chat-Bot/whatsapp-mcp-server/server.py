"""WhatsApp MCP Server implementation."""

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP, Context

import auth, group, message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Global state for the current session
current_session_id: Optional[str] = None


async def auto_ensure_session() -> tuple[bool, str]:
    """
    Automatically ensure a WhatsApp session is open.
    If no session exists, it will create one automatically.
    Returns (success, message).
    """
    try:
        if auth.auth_manager.is_authenticated():
            return True, "Session already active"
        
        # Auto-open session if none exists
        logger.info("No active session found, automatically opening a new session...")
        success, message = await auth.auth_manager.open_session()
        
        if success:
            logger.info("Session automatically opened successfully")
            return True, f"Auto-opened session: {message}"
        else:
            logger.error(f"Failed to auto-open session: {message}")
            return False, f"Failed to auto-open session: {message}"
            
    except Exception as e:
        logger.error(f"Error in auto_ensure_session: {e}")
        return False, f"Error auto-opening session: {str(e)}"


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle."""
    try:
        # Log server startup
        logger.info("WhatsApp MCP Server starting up")
        yield {}
    finally:
        # Cleanup resources when shutting down
        logger.info("WhatsApp MCP Server shutting down")


# Create the FastMCP server with lifespan support
mcp = FastMCP(
    "WhatsAppMCP",
    description="WhatsApp integration through the Model Context Protocol",
    lifespan=server_lifespan,
)


@mcp.tool()
async def open_session(ctx: Context) -> str:
    """Open a new WhatsApp session."""
    try:
        # Open a new session
        success, message_text = await auth.auth_manager.open_session()
        if success:
            return f"Success: {message_text}"
        else:
            return f"Error: {message_text}"
    except Exception as e:
        logger.error(f"Error opening session: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
async def send_message(
    ctx: Context, phone_number: str, content: str, reply_to: Optional[str] = None
) -> str:
    """
    Send a message to a chat. Automatically opens a session if none exists.

    Parameters:
    - phone_number: The phone number of the recipient
    - content: The content of the message to send
    - reply_to: ID of the message to reply to (optional)
    """
    try:
        # Auto-ensure session is open
        session_success, session_message = await auto_ensure_session()
        if not session_success:
            return f"Error: {session_message}"

        result = await message.send_message(
            phone_number=phone_number, content=content, reply_to=reply_to
        )
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
async def get_chats(ctx: Context, limit: int = 50, offset: int = 0) -> str:
    """
    Get a list of chats. Automatically opens a session if none exists.

    Parameters:
    - limit: Maximum number of chats to return (default: 50)
    - offset: Offset for pagination (default: 0)
    """
    try:
        # Auto-ensure session is open
        session_success, session_message = await auto_ensure_session()
        if not session_success:
            return f"Error: {session_message}"

        chats = await message.get_chats(limit=limit, offset=offset)
        return json.dumps({"chats": chats})
    except Exception as e:
        logger.error(f"Error getting chats: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
async def create_group(ctx: Context, group_name: str, participants: list[str]) -> str:
    """
    Create a new WhatsApp group. Automatically opens a session if none exists.

    Parameters:
    - group_name: Name of the group to create
    - participants: List of participant phone numbers
    """
    try:
        # Auto-ensure session is open
        session_success, session_message = await auto_ensure_session()
        if not session_success:
            return f"Error: {session_message}"

        group_result = await group.create_group(
            group_name=group_name,
            participants=participants,
        )
        return json.dumps(group_result.model_dump())
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
async def get_group_participants(ctx: Context, group_id: str) -> str:
    """
    Get the participants of a WhatsApp group. Automatically opens a session if none exists.

    Parameters:
    - group_id: The WhatsApp ID of the group
    """
    try:
        # Auto-ensure session is open
        session_success, session_message = await auto_ensure_session()
        if not session_success:
            return f"Error: {session_message}"

        participants = await group.get_group_participants(group_id=group_id)
        return json.dumps({"participants": [p.model_dump() for p in participants]})
    except Exception as e:
        logger.error(f"Error getting group participants: {e}")
        return f"Error: {str(e)}"

