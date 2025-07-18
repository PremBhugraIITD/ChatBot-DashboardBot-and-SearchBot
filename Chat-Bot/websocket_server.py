"""
Chat-Bot WebSocket Server for MCP Multi-Agent System

This module provides WebSocket and REST API endpoints specifically for the Chat-Bot 
functionality of the MCP multi-agent system. It handles streaming responses, 
live agent routing, and real-time status updates.

NOTE: This server now focuses only on Chat-Bot functionality. For full integration
with Dashboard-Bot and Search-Bot, use the root server.py instead.

CONCURRENCY MODEL: Per-Connection MCP Managers
- Each WebSocket connection creates its own MCPClientManager instance
- This enables multiple users to connect simultaneously without interference
- Fixes the issue where multiple connections would cancel each other's initialization
- Each agent (93, 188, etc.) can connect and chat independently

Chat-Bot Endpoints:
- WS /chat/ws - Real-time chat with streaming responses and live agent routing
- GET /chat/api/test - Interactive HTML test page (served from websocket_frontend.html)  
- GET /chat/api/health - Health check with connection status
- POST /chat/api/query - Form metadata processing endpoint with intelligent agent routing
- POST /chat/api/subagent - Sub-agent delegation endpoint for chat prompts

Real-time Features:
- Streaming AI responses as tokens are generated
- Live agent routing notifications (Developer, Writer, Sales, General)
- Real-time tool execution status updates
- Multi-client connection management with per-connection isolation
- Error handling and connection recovery

Usage:
    python websocket_server.py  # Chat-Bot only
    # or
    python ../server.py         # Full integration with all three applications
    
    # Test WebSocket: http://localhost:8001/chat/api/test
"""

import os
import json
import asyncio
import logging
import httpx
import uuid
import aiomysql
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from contextlib import asynccontextmanager

# Import the MCP client manager class and conversation manager
from mcp_client import MCPClientManager, conversation_manager
from mcp_servers_list import get_mcp_servers
from dotenv import load_dotenv

load_dotenv(override=True) 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MySQL Configuration for OpenAI Usage Tracking
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'db': os.getenv('DB_NAME', 'aiagent'),
    'charset': 'utf8mb4'
}

async def get_mysql_connection():
    """Get async MySQL connection for usage tracking."""
    try:
        connection = await aiomysql.connect(**MYSQL_CONFIG)
        return connection
    except Exception as e:
        logger.error(f"❌ Failed to connect to MySQL: {e}")
        return None

async def update_openai_usage(company_id: int, workspace_id: int, agent_id: int, 
                            prompt_tokens: int, completion_tokens: int, 
                            total_tokens: int, model: str):
    """
    Update or insert OpenAI usage tracking in MySQL database.
    Uses UPSERT pattern to increment tokens and request count for existing workspace.
    Creates one row per (COMPANY_ID, WORKSPACE_ID) combination.
    """
    try:
        connection = await get_mysql_connection()
        if not connection:
            logger.error("❌ No MySQL connection available for usage tracking")
            return False
            
        async with connection:
            cursor = await connection.cursor()
            
            # First check if record exists
            check_query = """
            SELECT ID, REQUEST_COUNT, TOTAL_TOKENS_USED, PROMPT_TOKENS, COMPLETION_TOKENS 
            FROM openai_usage 
            WHERE COMPANY_ID = %s AND WORKSPACE_ID = %s AND MODEL = %s AND AGENT_ID = %s
            """
            
            await cursor.execute(check_query, (company_id, workspace_id, model, agent_id))
            existing_record = await cursor.fetchone()
            
            if existing_record:
                # Update existing record
                update_query = """
                UPDATE openai_usage 
                SET TOTAL_TOKENS_USED = TOTAL_TOKENS_USED + %s,
                    PROMPT_TOKENS = PROMPT_TOKENS + %s,
                    COMPLETION_TOKENS = COMPLETION_TOKENS + %s,
                    REQUEST_COUNT = REQUEST_COUNT + 1,
                    UPDATED_AT = CURRENT_TIMESTAMP
                WHERE COMPANY_ID = %s AND WORKSPACE_ID = %s AND MODEL = %s AND AGENT_ID = %s
                """
                
                await cursor.execute(update_query, (
                    total_tokens, prompt_tokens, completion_tokens,
                    company_id, workspace_id, model, agent_id
                ))
            else:
                # Insert new record
                insert_query = """
                INSERT INTO openai_usage 
                (COMPANY_ID, WORKSPACE_ID, MODEL, TOTAL_TOKENS_USED, PROMPT_TOKENS, 
                 COMPLETION_TOKENS, REQUEST_TYPE, REQUEST_COUNT, AGENT_ID, CREDENTIAL_USED)
                VALUES (%s, %s, %s, %s, %s, %s, 'chat', 1, %s, 'internal')
                """
                
                await cursor.execute(insert_query, (
                    company_id, workspace_id, model, total_tokens, prompt_tokens, 
                    completion_tokens, agent_id
                ))
            
            await connection.commit()
            
            action = "Updated" if existing_record else "Created"
            logger.info(f"✅ {action} OpenAI usage for workspace {workspace_id}: "
                       f"{prompt_tokens}+{completion_tokens}={total_tokens} tokens")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to update OpenAI usage tracking: {e}")
        return False

# Note: Dashboard-Bot and Search-Bot integration moved to root server.py
# This websocket_server.py now focuses only on Chat-Bot functionality

async def verify_agent_token(token: str):
    """
    Verify agent token for WebSocket connections using UnleashX API
    """
    try:
        logger.info(f"Agent token verification requested for token: {token[:10]}...")
        
        # Validate token presence
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Agent token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Call UnleashX API to verify agent token
        async with httpx.AsyncClient() as client:
            UNLEASHX_URL= os.getenv("UNLEASHX_URL")
            response = await client.post(
                f"{UNLEASHX_URL}/api/agent-scope/verify",
                headers={
                    "token": token,
                    "Content-Type": "application/json"
                },
                json={"app": "AI Agent Verification"}
            )
            
            # Check if the API call was successful
            if response.status_code != 200:
                logger.warning(f"Agent token verification failed: Status {response.status_code}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired agent token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Parse the response
            try:
                response_data = response.json()
                logger.info(f"Agent verification response received: {response_data.get('message', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to parse agent verification response: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Invalid response from authentication service"
                )
            
            # Check if the response indicates success
            if response_data.get("error", True) or response_data.get("code") != 200:
                logger.warning(f"Agent token verification failed: {response_data.get('message', 'Unknown error')}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired agent token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Extract agent data from response
            agent_data = response_data.get("data", {})
            
            # Return structured agent information
            return {
                "valid": True,
                "message": response_data.get("message", "Authenticated"),
                "timestamp": response_data.get("timestamp"),
                "agent_data": agent_data,
                "permissions": ["read", "write", "execute"],  # Default permissions
                "token_type": "agent",
                "full_response": response_data  # Keep full response for any additional needs
            }
        
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Network error during agent token verification: {e}")
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error during agent token verification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Token verification service error"
        )

async def fetch_agent_config(agent_token: str, agent_id: str):
    """
    Fetch agent personality prompt, temperature, and model from agent-scope/summary API.
    This function gets the dynamic personality prompt, temperature, and model that should be used for the agent.
    Returns a tuple: (prompt, temperature, model)
    """
    try:
        logger.info(f"🧠 Fetching agent configuration for agent: {agent_id}")
        
        UNLEASHX_URL = os.getenv("UNLEASHX_URL")
        url = f"{UNLEASHX_URL}/api/agent-scope/summary"
        
        # Debug: Print request details
        print(f"🔍 Debug - API Request:")
        print(f"  URL: {url}")
        print(f"  Agent ID: {agent_id}")
        print(f"  Token: {agent_token[:10]}..." if agent_token else "No token")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "token": agent_token,
                    "Content-Type": "application/json"
                },
                params={"agent_id": agent_id}
            )
            
            # Debug: Print response details
            print(f"🔍 Debug - API Response:")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}..." if len(response.text) > 200 else response.text)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ Failed to fetch agent configuration: Status {response.status_code}")
                return None, None, None  # Return None for all so we can handle gracefully
            
            response_data = response.json()
            
            # Check if the response indicates success
            if response_data.get("error", False) or response_data.get("code") != 200:
                logger.warning(f"⚠️ Agent configuration API error: {response_data.get('message', 'Unknown error')}")
                return None, None, None  # Return None for all so we can handle gracefully
            
            # Extract the prompt, temperature, and model version from the response data
            data = response_data.get("data", {})
            prompt = data.get("prompt", "")
            temperature = data.get("advanced", {}).get("temperature", 0)  # Always use API value, even if 0
            version = data.get("version", "")
            
            # Map API model version to OpenAI model names
            model_mapping = {
                "gpt-4o": "gpt-4o",
                "gpt-4o-mini": "gpt-4o-mini", 
                "Gpt-4-turbo": "gpt-4-turbo",
                "Gpt-4": "gpt-4",
                "Gpt-3.5-turbo": "gpt-3.5-turbo"
            }
            
            # Get mapped model or default to gpt-4o-mini
            model = model_mapping.get(version, "gpt-4o-mini")
            
            if prompt:
                logger.info(f"✅ Successfully fetched agent configuration for agent {agent_id} (prompt length: {len(prompt)} chars)")
                print(f"🧠 Agent Configuration for Agent {agent_id}:")
                print(f"📝 Prompt: {prompt}")
                print("=" * 80)
            else:
                logger.info(f"⚠️ No personality prompt found for agent {agent_id}")
            
            logger.info(f"🌡️ Agent {agent_id} temperature: {temperature}")
            logger.info(f"🤖 Agent {agent_id} model: {model} (from version: {version})")
            print(f"🌡️ Temperature for Agent {agent_id}: {temperature}")
            print(f"🤖 Model for Agent {agent_id}: {model} (API version: {version})")
            
            return prompt.strip() if prompt else None, temperature, model
                
    except httpx.RequestError as e:
        logger.error(f"❌ Network error fetching agent configuration: {e}")
        return None, None, None  # Return None for all so we can handle gracefully
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching agent configuration: {e}")
        return None, None, None  # Return None for all so we can handle gracefully

# REST API Models and Functions

class QueryRequest(BaseModel):
    metadata: dict  # Dynamic form metadata for processing

class SubagentRequest(BaseModel):
    prompt: str  # Chat prompt for sub-agent delegation

async def fetch_tool_tokens(agent_token: str, agent_id: str):
    """
    Fetch Google tokens (Gmail + Sheets + Docs + Calendar), WhatsApp Business tokens, YouTube and HeyGen API keys, and Airtable/Notion API keys from agent-scope/get-agent-tools-status API.
    Returns tokens for Gmail, Google Sheets, Google Docs, Google Calendar, WhatsApp Business, YouTube, HeyGen, Airtable, Notion, and availability flags for special services.
    Uses the latest API response format with nested auth_data structure.
    """
    try:
        logger.info(f"🔑 Fetching service tokens (Gmail + Sheets + Docs + Calendar + WhatsApp + YouTube + HeyGen + Airtable + Notion) for agent {agent_id}...")
        
        UNLEASHX_URL = os.getenv("UNLEASHX_URL")
        url = f"{UNLEASHX_URL}/api/agent-scope/get-agent-tools-status"
        
        headers = {
            "token": agent_token,
            "Content-Type": "application/json"
        }
        
        payload = {
            "agent_id": agent_id
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url, 
                headers=headers, 
                params=payload  # Use params for GET request, not json
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("error") is False and data.get("code") == 200:
                    # Find Gmail, Sheets, Docs, Calendar, WhatsApp, Playwright, OCR, CAPTCHA solver, YouTube, and HeyGen integrations in the response
                    tools = data.get("data", {}).get("tools", [])
                    gmail_tokens = None
                    sheets_tokens = None
                    docs_tokens = None
                    calendar_tokens = None
                    whatsapp_tokens = None
                    playwright_enabled = False
                    ocr_enabled = False
                    captcha_solver_enabled = False
                    youtube_tokens = None
                    heygen_tokens = None
                    airtable_tokens = None
                    notion_tokens = None
                    asana_tokens = None
                    servicenow_tokens = None
                    zendesk_tokens = None
                    freshdesk_tokens = None
                    salesforce_tokens = None
                    pipedrive_tokens = None
                    
                    for tool in tools:
                        service_name = tool.get("service_name")
                        is_connected = tool.get("is_connected")
                        is_enabled = tool.get("is_enabled")
                        is_available = tool.get("is_available")
                        auth_data = tool.get("auth_data", {})
                        
                        if service_name == "gmail_mcp_server" and is_connected and is_enabled and is_available:
                            # Extract Gmail tokens from auth_data.tokens
                            access_token = auth_data.get("access_token")
                            refresh_token = auth_data.get("refresh_token")
                            
                            if access_token and refresh_token:
                                connected_account = tool.get('connected_account', 'Unknown')
                                logger.info(f"✅ Gmail tokens extracted for: {connected_account}")
                                gmail_tokens = {
                                    "access_token": access_token,
                                    "refresh_token": refresh_token
                                }
                        
                        elif (service_name == "sheet_mcp_server" or service_name == "sheets") and is_connected and is_enabled and is_available:
                            # Extract Google Sheets tokens from auth_data.tokens
                            access_token = auth_data.get("access_token")
                            refresh_token = auth_data.get("refresh_token")
                            
                            if access_token and refresh_token:
                                connected_account = tool.get('connected_account', 'Unknown')
                                logger.info(f"✅ Google Sheets tokens extracted for: {connected_account}")
                                sheets_tokens = {
                                    "access_token": access_token,
                                    "refresh_token": refresh_token
                                }
                        
                        elif service_name == "docs" and is_connected and is_enabled and is_available:
                            # Extract Google Docs tokens from auth_data
                            access_token = auth_data.get("access_token")
                            refresh_token = auth_data.get("refresh_token")
                            
                            if access_token and refresh_token:
                                connected_account = tool.get('connected_account', 'Unknown')
                                logger.info(f"✅ Google Docs tokens extracted for: {connected_account}")
                                docs_tokens = {
                                    "access_token": access_token,
                                    "refresh_token": refresh_token
                                }
                        
                        elif (service_name == "calendar" or service_name == "calandar_mcp_server") and is_connected and is_enabled and is_available:
                            # Extract Google Calendar tokens from auth_data
                            access_token = auth_data.get("access_token")
                            refresh_token = auth_data.get("refresh_token")
                            
                            if access_token and refresh_token:
                                connected_account = tool.get('connected_account', 'Unknown')
                                logger.info(f"✅ Google Calendar tokens extracted for: {connected_account}")
                                calendar_tokens = {
                                    "access_token": access_token,
                                    "refresh_token": refresh_token
                                }
                        
                        elif service_name == "whatsapp" and is_connected and is_enabled and is_available:
                            # Extract WhatsApp Business tokens from auth_data
                            green_api_token = auth_data.get("green_api_token")
                            # Handle the typo in API response: "greep_api_instance_id" vs "green_api_instance_id"
                            green_api_instance_id = auth_data.get("greep_api_instance_id") or auth_data.get("green_api_instance_id")
                            
                            if green_api_token and green_api_instance_id:
                                connected_account = tool.get('connected_account', 'Unknown')
                                logger.info(f"✅ WhatsApp Business tokens extracted for: {connected_account}")
                                whatsapp_tokens = {
                                    "green_api_token": green_api_token,
                                    "green_api_instance_id": green_api_instance_id
                                }
                        
                        elif service_name == "playwright" and is_enabled and is_available:
                            # Playwright requires all three: is_enabled, is_available (consistent with other services)
                            # Note: is_connected not required for Playwright as it doesn't need authentication
                            connected_account = tool.get('connected_account', 'Available')
                            logger.info(f"✅ Playwright enabled for: {connected_account}")
                            playwright_enabled = True
                        
                        elif service_name == "ocr" and is_enabled and is_available:
                            # OCR requires only is_enabled and is_available (no authentication needed)
                            # Note: is_connected not required for OCR as it doesn't need authentication
                            connected_account = tool.get('connected_account', 'Available')
                            logger.info(f"✅ OCR enabled for: {connected_account}")
                            ocr_enabled = True
                        
                        elif service_name == "captcha_solver" and is_enabled and is_available:
                            # CAPTCHA solver requires only is_enabled and is_available (no authentication needed)
                            # Note: is_connected not required for CAPTCHA solver as it uses env var for API key
                            connected_account = tool.get('connected_account', 'Available')
                            logger.info(f"✅ CAPTCHA solver enabled for: {connected_account}")
                            captcha_solver_enabled = True
                        
                        elif service_name == "youtube" and is_connected and is_enabled and is_available:
                            # Extract YouTube API key from auth_data (same pattern as Gmail/Sheets)
                            auth_data = tool.get("auth_data", {})
                            
                            api_key = auth_data.get("YOUTUBE_API_KEY")
                            
                            if api_key:
                                connected_account = tool.get('connected_account', 'Available')
                                logger.info(f"✅ YouTube API key extracted for: {connected_account}")
                                youtube_tokens = {
                                    "api_key": api_key
                                }
                        
                        elif service_name == "heygen" and is_connected and is_enabled and is_available:
                            # Extract HeyGen API key from auth_data (same pattern as Gmail/Sheets)
                            auth_data = tool.get("auth_data", {})
                            
                            api_key = auth_data.get("HEYGEN_API_KEY")
                            
                            if api_key:
                                connected_account = tool.get('connected_account', 'Available')
                                logger.info(f"✅ HeyGen API key extracted for: {connected_account}")
                                heygen_tokens = {
                                    "api_key": api_key
                                }
                        
                        elif service_name == "airtable" and is_connected and is_enabled and is_available:
                            # Extract Airtable API key from auth_data (same pattern as YouTube/HeyGen)
                            auth_data = tool.get("auth_data", {})
                            
                            api_key = auth_data.get("AIRTABLE_API_KEY")
                            
                            if api_key:
                                connected_account = tool.get('connected_account', 'Available')
                                logger.info(f"✅ Airtable API key extracted for: {connected_account}")
                                airtable_tokens = {
                                    "api_key": api_key
                                }
                        
                        elif service_name == "notion" and is_connected and is_enabled and is_available:
                            # Extract Notion API key from auth_data (same pattern as YouTube/HeyGen)
                            auth_data = tool.get("auth_data", {})
                            
                            api_key = auth_data.get("NOTION_API_KEY")
                            
                            if api_key:
                                connected_account = tool.get('connected_account', 'Available')
                                logger.info(f"✅ Notion API key extracted for: {connected_account}")
                                notion_tokens = {
                                    "api_key": api_key
                                }
                        
                        elif service_name == "asana" and is_connected and is_enabled and is_available:
                            access_token = auth_data.get("ASANA_ACCESS_TOKEN")
                            if access_token:
                                asana_tokens = {"ASANA_ACCESS_TOKEN": access_token}
                                logger.info(f"✅ Asana access token extracted for agent {agent_id}")
                        
                        elif service_name == "servicenow" and is_connected and is_enabled and is_available:
                            instance_url = auth_data.get("SERVICENOW_INSTANCE_URL")
                            username = auth_data.get("SERVICENOW_USERNAME")
                            password = auth_data.get("SERVICENOW_PASSWORD")
                            if instance_url and username and password:
                                servicenow_tokens = {
                                    "SERVICENOW_INSTANCE_URL": instance_url,
                                    "SERVICENOW_USERNAME": username,
                                    "SERVICENOW_PASSWORD": password
                                }
                                logger.info(f"✅ Servicenow credentials extracted for agent {agent_id}")
                        if service_name == "zendesk" and is_connected and is_enabled and is_available:
                            email = auth_data.get("ZENDESK_EMAIL")
                            api_key = auth_data.get("ZENDESK_API_KEY")
                            subdomain = auth_data.get("ZENDESK_SUBDOMAIN")
                            if email and api_key and subdomain:
                                zendesk_tokens = {
                                    "ZENDESK_EMAIL": email,
                                    "ZENDESK_API_KEY": api_key,
                                    "ZENDESK_SUBDOMAIN": subdomain
                                }
                                logger.info(f"✅ Zendesk credentials extracted for agent {agent_id}")
                        if service_name == "freshdesk" and is_connected and is_enabled and is_available:
                            domain = auth_data.get("FRESHDESK_DOMAIN")
                            api_key = auth_data.get("FRESHDESK_API_KEY")
                            if domain and api_key:
                                freshdesk_tokens = {
                                    "FRESHDESK_DOMAIN": domain,
                                    "FRESHDESK_API_KEY": api_key
                                }
                                logger.info(f"✅ Freshdesk credentials extracted for agent {agent_id}")
                        if service_name == "salesforce" and is_connected and is_enabled and is_available:
                            access_token = auth_data.get("SALESFORCE_ACCESS_TOKEN")
                            instance_url = auth_data.get("SALESFORCE_INSTANCE_URL")
                            if access_token and instance_url:
                                salesforce_tokens = {
                                    "SALESFORCE_ACCESS_TOKEN": access_token,
                                    "SALESFORCE_INSTANCE_URL": instance_url
                                }
                                logger.info(f"✅ Salesforce credentials extracted for agent {agent_id}")
                        if service_name == "pipedrive" and is_connected and is_enabled and is_available:
                            api_token = auth_data.get("PIPEDRIVE_API_TOKEN")
                            if api_token:
                                pipedrive_tokens = {"PIPEDRIVE_API_TOKEN": api_token}
                                logger.info(f"✅ Pipedrive credentials extracted for agent {agent_id}")
                    
                    # Log final results
                    if gmail_tokens:
                        logger.info(f"📧 Gmail service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Gmail service not available for agent {agent_id}")
                        
                    if sheets_tokens:
                        logger.info(f"📊 Google Sheets service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Google Sheets service not available for agent {agent_id}")
                    
                    if docs_tokens:
                        logger.info(f"📝 Google Docs service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Google Docs service not available for agent {agent_id}")
                    
                    if calendar_tokens:
                        logger.info(f"📅 Google Calendar service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Google Calendar service not available for agent {agent_id}")
                    
                    if whatsapp_tokens:
                        logger.info(f"📱 WhatsApp Business service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ WhatsApp Business service not available for agent {agent_id}")
                    
                    if playwright_enabled:
                        logger.info(f"🎭 Playwright service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Playwright service not available for agent {agent_id}")
                    
                    if ocr_enabled:
                        logger.info(f"👁️ OCR service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ OCR service not available for agent {agent_id}")
                    
                    if captcha_solver_enabled:
                        logger.info(f"🔐 CAPTCHA solver service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ CAPTCHA solver service not available for agent {agent_id}")
                    
                    if youtube_tokens:
                        logger.info(f"📺 YouTube service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ YouTube service not available for agent {agent_id}")
                    
                    if heygen_tokens:
                        logger.info(f"🎬 HeyGen service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ HeyGen service not available for agent {agent_id}")
                    
                    if airtable_tokens:
                        logger.info(f"📊 Airtable service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Airtable service not available for agent {agent_id}")
                    
                    if notion_tokens:
                        logger.info(f"📚 Notion service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Notion service not available for agent {agent_id}")
                    
                    if asana_tokens:
                        logger.info(f"💼 Asana service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Asana service not available for agent {agent_id}")
                    
                    if servicenow_tokens:
                        logger.info(f"🔧 ServiceNow service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ ServiceNow service not available for agent {agent_id}")
                    
                    if zendesk_tokens:
                        logger.info(f"💬 Zendesk service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Zendesk service not available for agent {agent_id}")
                    
                    if freshdesk_tokens:
                        logger.info(f"💬 Freshdesk service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Freshdesk service not available for agent {agent_id}")
                    
                    if salesforce_tokens:
                        logger.info(f"�� Salesforce service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Salesforce service not available for agent {agent_id}")
                    
                    if pipedrive_tokens:
                        logger.info(f"📊 Pipedrive service available for agent {agent_id}")
                    else:
                        logger.info(f"⚠️ Pipedrive service not available for agent {agent_id}")
                    
                    return {
                        "gmail": gmail_tokens,
                        "sheets": sheets_tokens,
                        "docs": docs_tokens,
                        "calendar": calendar_tokens,
                        "whatsapp": whatsapp_tokens,
                        "playwright": playwright_enabled,
                        "ocr": ocr_enabled,
                        "captcha_solver": captcha_solver_enabled,
                        "youtube": youtube_tokens,
                        "heygen": heygen_tokens,
                        "airtable": airtable_tokens,
                        "notion": notion_tokens,
                        "asana": asana_tokens,
                        "servicenow": servicenow_tokens,
                        "zendesk": zendesk_tokens,
                        "freshdesk": freshdesk_tokens,
                        "salesforce": salesforce_tokens,
                        "pipedrive": pipedrive_tokens
                    }
                else:
                    logger.warning(f"❌ API returned error for agent {agent_id}: {data.get('message', 'Unknown error')}")
                    return {"gmail": None, "sheets": None, "docs": None, "calendar": None, "whatsapp": None, "playwright": False, "ocr": False, "captcha_solver": False, "youtube": None, "heygen": None, "airtable": None, "notion": None, "asana": None, "servicenow": None, "zendesk": None, "freshdesk": None, "salesforce": None, "pipedrive": None}
            else:
                logger.error(f"❌ Failed to fetch tools status: HTTP {response.status_code}")
                return {"gmail": None, "sheets": None, "docs": None, "calendar": None, "whatsapp": None, "playwright": False, "ocr": False, "captcha_solver": False, "youtube": None, "heygen": None, "airtable": None, "notion": None, "asana": None, "servicenow": None, "zendesk": None, "freshdesk": None, "salesforce": None, "pipedrive": None}
                
    except Exception as e:
        logger.error(f"❌ Error fetching service tokens: {str(e)}")
        return {"gmail": None, "sheets": None, "docs": None, "calendar": None, "whatsapp": None, "playwright": False, "ocr": False, "captcha_solver": False, "youtube": None, "heygen": None, "airtable": None, "notion": None, "asana": None, "servicenow": None, "zendesk": None, "freshdesk": None, "salesforce": None, "pipedrive": None}

async def fetch_subagents_data(agent_token: str, agent_id: str):
    """
    Fetch sub-agents data from agent-scope/get-agent-tools-status API.
    Returns list of sub-agents with their IDs, names, tokens, and connected tools.
    """
    try:
        logger.info(f"🎯 Fetching sub-agents data for agent {agent_id}...")
        
        UNLEASHX_URL = os.getenv("UNLEASHX_URL")
        url = f"{UNLEASHX_URL}/api/agent-scope/get-agent-tools-status"
        
        headers = {
            "token": agent_token,
            "Content-Type": "application/json"
        }
        
        payload = {
            "agent_id": agent_id
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url, 
                headers=headers, 
                params=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("error") is False and data.get("code") == 200:
                    # Extract sub-agents data
                    subagents = data.get("data", {}).get("subagents", [])
                    subagents_data = []
                    
                    if subagents:
                        logger.info(f"🎯 Found {len(subagents)} sub-agents for agent {agent_id}")
                        for subagent in subagents:
                            if subagent.get("is_enabled", False):
                                subagent_info = {
                                    "id": subagent.get("id"),
                                    "name": subagent.get("name"),
                                    "token": subagent.get("token"),
                                    "tools": []
                                }
                                
                                # Extract tool names from sub-agent's tools
                                subagent_tools = subagent.get("tools", [])
                                for tool in subagent_tools:
                                    if tool.get("is_enabled", False):
                                        subagent_info["tools"].append(tool.get("integration_name", "Unknown Tool"))
                                
                                subagents_data.append(subagent_info)
                                logger.info(f"✅ Sub-agent {subagent_info['id']} ({subagent_info['name']}) - Tools: {', '.join(subagent_info['tools'])}")
                    else:
                        logger.info(f"⚠️ No sub-agents found for agent {agent_id}")
                    
                    return subagents_data
                else:
                    logger.warning(f"❌ API returned error for agent {agent_id}: {data.get('message', 'Unknown error')}")
                    return []
            else:
                logger.error(f"❌ Failed to fetch sub-agents data: HTTP {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"❌ Error fetching sub-agents data: {str(e)}")
        return []

async def send_completion_call(message_id: str, call_status: str):
    """
    Send completion call to UnleashX API after processing is done.
    
    Args:
        message_id: The message ID from request metadata
        call_status: "completed" or "failed"
    """
    try:
        if not message_id:
            logger.warning("⚠️ No message_id provided for completion call")
            return
        
        UNLEASHX_URL = os.getenv("UNLEASHX_URL")
        if not UNLEASHX_URL:
            logger.error("❌ UNLEASHX_URL not configured for completion call")
            return
            
        url = f"{UNLEASHX_URL}/api/guest/callcompletion"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "track_id": message_id,
            "call_status": call_status
        }
        
        logger.info(f"🔔 Sending completion call for message_id: {message_id} with status: {call_status}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Completion call successful for message_id: {message_id}")
            else:
                logger.warning(f"⚠️ Completion call failed for message_id: {message_id} - HTTP {response.status_code}")
                
    except Exception as e:
        logger.error(f"❌ Error sending completion call for message_id {message_id}: {str(e)}")
        # Don't raise the exception to avoid breaking the main flow

class ConnectionManager:
    """Manages WebSocket connections for real-time communication."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_sessions: Dict[WebSocket, str] = {}  # Map WebSocket to session ID
        self.connection_tasks: Dict[str, asyncio.Task] = {}  # Track running tasks per session
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Accept and store a WebSocket connection."""
        await websocket.accept()
        
        # Generate a unique session ID for conversation history
        session_id = str(uuid.uuid4())
        self.connection_sessions[websocket] = session_id
        
        if client_id:
            self.active_connections[client_id] = websocket
        print(f"📱 WebSocket connected: {client_id or 'anonymous'} (Session: {session_id})")
        return session_id
    
    def disconnect(self, websocket: WebSocket, client_id: str = None):
        """Remove a WebSocket connection with proper task cleanup."""
        # Clean up session mapping and cancel any running tasks
        if websocket in self.connection_sessions:
            session_id = self.connection_sessions[websocket]
            del self.connection_sessions[websocket]
            
            # Cancel any running tasks for this session
            if session_id in self.connection_tasks:
                task = self.connection_tasks[session_id]
                if not task.done():
                    try:
                        task.cancel()
                    except Exception as e:
                        print(f"⚠️ Warning cancelling task for session {session_id}: {e}")
                del self.connection_tasks[session_id]
            
            print(f"🧹 Cleaned up conversation session: {session_id}")
        
        if client_id and client_id in self.active_connections:
            del self.active_connections[client_id]
        print(f"📱 WebSocket disconnected: {client_id or 'anonymous'}")
    
    def register_task(self, session_id: str, task: asyncio.Task):
        """Register a task for proper cleanup on disconnection."""
        self.connection_tasks[session_id] = task
    
    def cleanup_task(self, session_id: str):
        """Clean up a completed task."""
        if session_id in self.connection_tasks:
            del self.connection_tasks[session_id]
    
    def get_session_id(self, websocket: WebSocket) -> str:
        """Get the conversation session ID for a WebSocket connection."""
        return self.connection_sessions.get(websocket)
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"❌ Error sending to {client_id}: {e}")
                self.disconnect(None, client_id)

# Global connection manager
connection_manager = ConnectionManager()

class StreamingCallbackHandler:
    """Callback handler for streaming agent responses over WebSocket."""
    
    def __init__(self, websocket: WebSocket, client_id: str = None):
        self.websocket = websocket
        self.client_id = client_id
    
    async def send_status(self, status: str, message: str):
        """Send status update to client."""
        await self.send_message({
            "type": "status",
            "status": status,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def send_agent_routing(self, agent_type: str):
        """Send agent routing notification."""
        await self.send_message({
            "type": "agent_routing",
            "agent": agent_type,
            "message": f"🎯 Routing to {agent_type} agent",
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def send_tool_execution(self, tool_name: str, status: str):
        """Send tool execution notification."""
        await self.send_message({
            "type": "tool_execution", 
            "tool": tool_name,
            "status": status,
            "message": f"🔧 {status.title()} tool: {tool_name}",
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def send_token(self, token: str):
        """Send streaming token to client."""
        await self.send_message({
            "type": "token",
            "content": token,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def send_final_response(self, response: str, agent_type: str):
        """Send final complete response."""
        await self.send_message({
            "type": "final_response",
            "content": response,
            "agent": agent_type,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def send_error(self, error: str):
        """Send error message."""
        await self.send_message({
            "type": "error",
            "message": error,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def send_message(self, message: dict):
        """Send message via connection manager with connection health check."""
        try:
            if self.client_id:
                await connection_manager.send_personal_message(message, self.client_id)
            else:
                # Check WebSocket connection state before sending
                if hasattr(self.websocket, 'client_state') and self.websocket.client_state.name != 'CONNECTED':
                    print(f"⚠️ WebSocket not connected, skipping message send")
                    return
                await self.websocket.send_text(json.dumps(message))
        except ConnectionResetError:
            print(f"🔌 WebSocket connection reset, client disconnected")
        except Exception as e:
            print(f"❌ Error sending WebSocket message: {e}")

async def process_query_with_streaming(query: str, callback_handler: StreamingCallbackHandler, mcp_manager, agent_type: str = None, session_id: str = None, agent_id: int = None, workspace_id: int = None, ip_address: str = None, user_agent: str = None, company_id: int = None):
    """Process a query with real-time streaming updates, conversation context, and token usage tracking."""
    manager = mcp_manager
    
    try:
        await callback_handler.send_status("processing", "Processing your query...")
        
        if agent_type:
            # Direct agent access
            if agent_type not in manager.sub_agents:
                await callback_handler.send_error(f"Agent '{agent_type}' not found")
                return None
            
            await callback_handler.send_agent_routing(agent_type)
            selected_agent = manager.sub_agents[agent_type]
        else:
            # Force routing to user_agent (personality-based agent)
            await callback_handler.send_status("routing", "Routing to your personalized agent...")
            
            if not manager.sub_agents or "user_agent" not in manager.sub_agents:
                await callback_handler.send_error("User agent not initialized")
                return None
            
            agent_type = "user_agent"
            await callback_handler.send_agent_routing(agent_type)
            selected_agent = manager.sub_agents["user_agent"]
        
        await callback_handler.send_status("executing", f"Executing with {agent_type} agent...")
        
        # Execute the query with conversation context, authentication data, and client info
        result = await manager.execute_agent_with_context(selected_agent, query, session_id, agent_id, workspace_id, ip_address, user_agent)
        
        # Extract token usage for tracking and billing
        if hasattr(result, '_extracted_token_usage'):
            token_usage = result._extracted_token_usage
        elif isinstance(result, dict) and '_extracted_token_usage' in result:
            token_usage = result['_extracted_token_usage']
        else:
            token_usage = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        
        # Update OpenAI usage tracking in database (async, don't block response)
        if company_id and workspace_id and agent_id and token_usage['total_tokens'] > 0:
            try:
                asyncio.create_task(update_openai_usage(
                    company_id=company_id,
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    prompt_tokens=token_usage['prompt_tokens'],
                    completion_tokens=token_usage['completion_tokens'],
                    total_tokens=token_usage['total_tokens'],
                    model=mcp_manager.model  # Use dynamic model from MCP manager
                ))
                logger.info(f"💰 Token usage tracked: {token_usage['prompt_tokens']}+{token_usage['completion_tokens']}={token_usage['total_tokens']} tokens for workspace {workspace_id}")
            except Exception as e:
                logger.error(f"❌ Failed to track token usage: {e}")
                # Don't break the response flow for tracking errors
        
        # Extract text content from result (handle different LangChain response types)
        response_text = manager._extract_response_content(result)
        
        # Send final response
        await callback_handler.send_final_response(response_text, agent_type)
        await callback_handler.send_status("completed", f"Query completed by {agent_type} agent")
        
        # Note: Chat interaction is stored in MongoDB by the MCP client during agent execution
        
        return {
            "response": result,
            "agent_used": agent_type,
            "message": f"Response generated by {agent_type} agent",
            "session_id": session_id,
            "token_usage": token_usage  # Include token usage in response
        }
        
    except asyncio.CancelledError:
        # Handle cancellation gracefully
        logger.info(f"🔄 Query processing cancelled for session {session_id}")
        await callback_handler.send_status("cancelled", "Query processing was cancelled")
        raise
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        logger.error(f"❌ {error_msg} for session {session_id}")
        await callback_handler.send_error(error_msg)
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager - MCP will be initialized per-connection after authentication."""
    try:
        # Don't initialize a global MCP manager - each connection gets its own
        # This prevents concurrency issues and initialization order problems
        # Each WebSocket connection will create and manage its own MCPClientManager
        
        logger.info("🚀 WebSocket server starting - per-connection MCP managers enabled")
        
        yield
    finally:
        # No global cleanup needed since each connection manages its own MCP manager
        logger.info("🛑 WebSocket server shutting down")

app = FastAPI(lifespan=lifespan, title="WebSocket Server", description="Real-time WebSocket API for MCP Multi-Agent System")

# Add CORS middleware to allow frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket endpoint for real-time chat
@app.websocket("/chat/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time AI chat with streaming and token authentication."""
    
    # Extract client information
    client_ip = websocket.client.host if websocket.client else "unknown"
    user_agent = websocket.headers.get("user-agent", "unknown")
    
    # Extract token from query parameters
    query_params = websocket.query_params
    token = query_params.get("token")
    
    if not token:
        # Send error message and close connection
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Authentication token is required. Please provide token as query parameter: ws://localhost:8001/chat/ws?token=your_token",
            "code": 401,
            "timestamp": asyncio.get_event_loop().time()
        }))
        await websocket.close(code=1008, reason="Token required")  # 1008 = Policy Violation
        return
    
    # Verify the token
    try:
        auth_result = await verify_agent_token(token)
        logger.info(f"✅ WebSocket authentication successful: {auth_result.get('message', 'Authenticated')}")
    except HTTPException as e:
        # Send authentication error and close connection
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Authentication failed: {e.detail}",
            "code": e.status_code,
            "timestamp": asyncio.get_event_loop().time()
        }))
        await websocket.close(code=1008, reason="Authentication failed")  # 1008 = Policy Violation
        return
    except Exception as e:
        # Send general error and close connection
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Authentication service error",
            "code": 500,
            "timestamp": asyncio.get_event_loop().time()
        }))
        await websocket.close(code=1011, reason="Authentication service error")  # 1011 = Server Error
        return
    
    # Authentication successful - proceed with connection
    session_id = await connection_manager.connect(websocket)
    callback_handler = StreamingCallbackHandler(websocket)
    
    # Extract chatbot details from authentication response
    agent_data = auth_result.get('agent_data', {})
    agent_id = agent_data.get('id')
    workspace_id = agent_data.get('workspace_id')
    company_id = agent_data.get('company_id')  # Extract company_id for usage tracking
    chatbot_name = agent_data.get('chatbot_name', 'AI Agent')
    chatbot_welcome_message = agent_data.get('chatbot_welcome_message', 'Hello! How can I help you today?')
    chatbot_image = agent_data.get('chatbot_image', '')
    
    # Create a dedicated MCP manager for this connection to avoid concurrency issues
    # Each WebSocket connection gets its own MCP manager instance
    connection_mcp_manager = MCPClientManager()
    logger.info(f"🔧 Created dedicated MCP manager for agent {agent_id} (session: {session_id})")
    
    # Fetch service tokens (Gmail + Sheets + WhatsApp) for this agent
    logger.info(f"🔑 Fetching service tokens...")
    service_tokens = await fetch_tool_tokens(token, str(agent_id))
    
    # Extract tokens from the response
    gmail_tokens = service_tokens.get("gmail")
    sheets_tokens = service_tokens.get("sheets")
    docs_tokens = service_tokens.get("docs")
    calendar_tokens = service_tokens.get("calendar")
    whatsapp_tokens = service_tokens.get("whatsapp")
    playwright_enabled = service_tokens.get("playwright", False)
    ocr_enabled = service_tokens.get("ocr", False)
    captcha_solver_enabled = service_tokens.get("captcha_solver", False)
    youtube_tokens = service_tokens.get("youtube")
    heygen_tokens = service_tokens.get("heygen")
    airtable_tokens = service_tokens.get("airtable")
    notion_tokens = service_tokens.get("notion")
    asana_tokens = service_tokens.get("asana")
    servicenow_tokens = service_tokens.get("servicenow")
    zendesk_tokens = service_tokens.get("zendesk")
    freshdesk_tokens = service_tokens.get("freshdesk")
    salesforce_tokens = service_tokens.get("salesforce")
    pipedrive_tokens = service_tokens.get("pipedrive")
    
    # Fetch sub-agents data
    logger.info(f"🎯 Fetching sub-agents data...")
    subagents_data = await fetch_subagents_data(token, str(agent_id))
    
    # Fetch personality prompt, temperature, and model for this agent
    personality_prompt, agent_temperature, agent_model = await fetch_agent_config(token, str(agent_id))
    
    # Initialize MCP manager for this connection
    try:
        logger.info(f"🔧 Initializing MCP manager with agent_id: {agent_id}")
        await connection_mcp_manager.initialize(
            agent_id=agent_id, 
            gmail_tokens=gmail_tokens, 
            sheets_tokens=sheets_tokens,
            docs_tokens=docs_tokens,
            calendar_tokens=calendar_tokens,
            whatsapp_tokens=whatsapp_tokens,
            playwright_enabled=playwright_enabled,
            ocr_enabled=ocr_enabled,
            captcha_solver_enabled=captcha_solver_enabled,
            youtube_tokens=youtube_tokens,
            heygen_tokens=heygen_tokens,
            airtable_tokens=airtable_tokens,
            notion_tokens=notion_tokens,
            asana_tokens=asana_tokens,
            servicenow_tokens=servicenow_tokens,
            zendesk_tokens=zendesk_tokens,
            freshdesk_tokens=freshdesk_tokens,
            salesforce_tokens=salesforce_tokens,
            pipedrive_tokens=pipedrive_tokens,
            personality_prompt=personality_prompt,
            temperature=agent_temperature,
            model=agent_model,
            subagents_data=subagents_data
        )
        logger.info(f"✅ MCP manager initialized successfully for agent {agent_id} (session: {session_id})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP manager for agent {agent_id}: {e}")
        await callback_handler.send_error(f"Failed to initialize tools for agent {agent_id}")
        await websocket.close(code=1011, reason="MCP initialization failed")
        return
    
    try:
        # Send enhanced connection success message with chatbot details
        connection_response = {
            "type": "status",
            "status": "connected",
            "message": "chat websocket successfully connected",
            "chatbot_name": chatbot_name,
            "chatbot_welcome_message": chatbot_welcome_message,
            "chatbot_image": chatbot_image,
            "session_id": session_id,  # Send full session ID
            "timestamp": asyncio.get_event_loop().time()
        }
        await callback_handler.send_message(connection_response)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            query = message_data.get("query", "")
            # Note: agent_type is no longer extracted from message to force use of user_agent (subagent functionality)
            # This matches the API endpoint behavior where subagents are used instead of manual agent selection
            
            if not query.strip():
                await callback_handler.send_error("Empty query received")
                continue
            
            # Create a task for query processing to enable proper cancellation
            # Pass agent_type=None to force use of user_agent (personality-based agent with subagent capabilities)
            task = asyncio.create_task(
                process_query_with_streaming(query, callback_handler, connection_mcp_manager, None, session_id, agent_id, workspace_id, client_ip, user_agent, company_id)
            )
            
            # Register task for cleanup
            connection_manager.register_task(session_id, task)
            
            try:
                # Wait for task completion
                await task
            except asyncio.CancelledError:
                logger.info(f"🔄 Query processing cancelled for session {session_id}")
                break
            except Exception as e:
                logger.error(f"❌ Error processing query for session {session_id}: {e}")
                await callback_handler.send_error(f"Query processing error: {str(e)}")
            finally:
                # Clean up completed task
                connection_manager.cleanup_task(session_id)
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info(f"📱 Authenticated WebSocket disconnected normally (agent: {agent_id}, session: {session_id})")
        # Force cleanup of MCP manager if needed to prevent resource leaks
        try:
            await asyncio.wait_for(connection_mcp_manager._force_cleanup(), timeout=2.0)
            logger.info(f"🧹 MCP manager cleanup completed for agent {agent_id}")
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ MCP manager cleanup timed out for agent {agent_id}")
        except Exception as e:
            logger.warning(f"⚠️ MCP manager cleanup warning for agent {agent_id}: {e}")
    except asyncio.CancelledError:
        connection_manager.disconnect(websocket)
        logger.info(f"🔄 WebSocket connection cancelled (agent: {agent_id}, session: {session_id})")
        # Quick cleanup on cancellation
        try:
            await asyncio.wait_for(connection_mcp_manager._force_cleanup(), timeout=1.0)
        except:
            pass  # Ignore cleanup errors on cancellation
        raise
    except Exception as e:
        logger.error(f"❌ WebSocket error for agent {agent_id}: {e}")
        await callback_handler.send_error(f"Connection error: {str(e)}")
        connection_manager.disconnect(websocket)
        # Cleanup on error
        try:
            await asyncio.wait_for(connection_mcp_manager._force_cleanup(), timeout=2.0)
        except:
            pass  # Ignore cleanup errors


# Test HTML page for WebSocket
@app.get("/chat/api/test")
async def get_test_page():
    """Serve a test HTML page for WebSocket functionality."""
    try:
        # Read HTML content from external file
        html_file_path = os.path.join(os.path.dirname(__file__), "websocket_frontend.html")
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # Fallback error message if HTML file is not found
        error_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>❌ Error</h1>
            <p>WebSocket test page not found. Please ensure 'websocket_frontend.html' exists in the same directory.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=404)

# Health check endpoint with WebSocket connection status
@app.get("/chat/api/health")
async def health_check():
    """Health check endpoint with WebSocket connection status and Dashboard-Bot integration."""
    # Since we now use per-connection MCP managers, health check shows general server status
    
    health_data = {
        "status": "healthy",
        "server_type": "websocket",
        "concurrency_model": "per_connection_mcp_managers",
        "agents_available": True,  # MCPClientManager class is always available
        "mcp_servers_configured": len(get_mcp_servers()),  # Number of configured MCP servers
        "websocket_connections": {
            "active_connections": len(connection_manager.active_connections),
            "total_connections": len(connection_manager.active_connections)
        },
        "conversation_sessions": {
            "active_sessions": len(conversation_manager.sessions),
            "session_mapping": len(connection_manager.connection_sessions)
        },
        "integration_note": "Dashboard-Bot and Search-Bot integration moved to root server.py"
    }
    
    return health_data

# REST API Endpoints

@app.post("/chat/api/query")
async def query_endpoint(request: QueryRequest, token: str = Header(...)):
    """
    Form metadata processing endpoint with token authentication and agent-specific configuration.
    Analyzes form metadata and performs operations based on agent's personality prompt.
    """
    # Extract message_id from metadata early for completion tracking
    message_id = request.metadata.get("message_id") if request.metadata else None
    
    try:
        # Step 1: Verify the token
        logger.info(f"🔐 Verifying token for API request...")
        auth_result = await verify_agent_token(token)
        logger.info(f"✅ Token verification successful: {auth_result.get('message', 'Authenticated')}")
        
        # Step 2: Extract agent data
        agent_data = auth_result.get('agent_data', {})
        agent_id = agent_data.get('id')
        workspace_id = agent_data.get('workspace_id')
        company_id = agent_data.get('company_id')  # Extract company_id for usage tracking
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="Agent ID not found in authentication response")
        
        logger.info(f"🤖 Processing query for agent {agent_id}")
        if message_id:
            logger.info(f"📋 Processing request with message_id: {message_id}")
        
        # Step 3: Fetch service tokens (Gmail + Sheets + WhatsApp + ... + Asana + Servicenow)
        logger.info(f"🔑 Fetching service tokens...")
        service_tokens = await fetch_tool_tokens(token, str(agent_id))
        
        # Extract tokens from the response
        gmail_tokens = service_tokens.get("gmail")
        sheets_tokens = service_tokens.get("sheets")
        whatsapp_tokens = service_tokens.get("whatsapp")
        playwright_enabled = service_tokens.get("playwright", False)
        ocr_enabled = service_tokens.get("ocr", False)
        captcha_solver_enabled = service_tokens.get("captcha_solver", False)
        youtube_tokens = service_tokens.get("youtube")
        heygen_tokens = service_tokens.get("heygen")
        airtable_tokens = service_tokens.get("airtable")
        notion_tokens = service_tokens.get("notion")
        asana_tokens = service_tokens.get("asana")
        servicenow_tokens = service_tokens.get("servicenow")
        zendesk_tokens = service_tokens.get("zendesk")
        freshdesk_tokens = service_tokens.get("freshdesk")
        salesforce_tokens = service_tokens.get("salesforce")
        pipedrive_tokens = service_tokens.get("pipedrive")
        
        # Step 4: Fetch sub-agents data
        logger.info(f"🎯 Fetching sub-agents data...")
        subagents_data = await fetch_subagents_data(token, str(agent_id))
        
        # Step 5: Fetch personality prompt, temperature, and model for this agent
        personality_prompt, agent_temperature, agent_model = await fetch_agent_config(token, str(agent_id))
        
        # Create MCP manager for this request (stateless)
        request_mcp_manager = MCPClientManager()
        
        try:
            logger.info(f"🔧 Initializing MCP manager for request with agent_id: {agent_id}")
            await request_mcp_manager.initialize(
                agent_id=agent_id, 
                gmail_tokens=gmail_tokens, 
                sheets_tokens=sheets_tokens,
                whatsapp_tokens=whatsapp_tokens,
                playwright_enabled=playwright_enabled,
                ocr_enabled=ocr_enabled,
                captcha_solver_enabled=captcha_solver_enabled,
                youtube_tokens=youtube_tokens,
                heygen_tokens=heygen_tokens,
                airtable_tokens=airtable_tokens,
                notion_tokens=notion_tokens,
                asana_tokens=asana_tokens,
                servicenow_tokens=servicenow_tokens,
                zendesk_tokens=zendesk_tokens,
                freshdesk_tokens=freshdesk_tokens,
                salesforce_tokens=salesforce_tokens,
                pipedrive_tokens=pipedrive_tokens,
                personality_prompt=personality_prompt,
                temperature=agent_temperature,
                model=agent_model,
                subagents_data=subagents_data
            )
            
            # Step 7: Process the form metadata using user_agent (personality-based agent)
            if not request_mcp_manager.sub_agents or "user_agent" not in request_mcp_manager.sub_agents:
                raise HTTPException(status_code=500, detail="User agent not initialized")
            
            logger.info(f"🎯 Processing form metadata with user_agent...")
            selected_agent = request_mcp_manager.sub_agents["user_agent"]
            
            # Create form analysis prompt based on the metadata
            form_analysis_prompt = f"""
You are analyzing form metadata and should perform operations based on your personality and capabilities.

FORM METADATA TO ANALYZE:
{json.dumps(request.metadata, indent=2)}

Based on your personality prompt and available tools, analyze this form data and perform the appropriate operations. Consider:
1. The form structure (headers and field types)
2. The submitted data (datalist)
3. Ignore any redundant or irrelevant fields
"""
            
            # Execute the form analysis with conversation context and authentication data
            result = await request_mcp_manager.execute_agent_with_context(
                selected_agent, 
                form_analysis_prompt, 
                session_id=None,  # No session for REST API
                agent_id=agent_id,
                workspace_id=workspace_id,
                ip_address="api_request",  # Mark as API request
                user_agent="rest_api_form_processing"
            )
        
            # Extract response content
            response_content = request_mcp_manager._extract_response_content(result)
            
            # Extract token usage for tracking
            token_usage = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
            
            if hasattr(result, '_extracted_token_usage'):
                token_usage = result._extracted_token_usage
            elif isinstance(result, dict) and '_extracted_token_usage' in result:
                token_usage = result['_extracted_token_usage']
            
            # Extract tools used for tracking (NEW FUNCTIONALITY)
            tools_used = []
            if hasattr(result, '_extracted_tools_used'):
                tools_used = result._extracted_tools_used
            elif isinstance(result, dict) and '_extracted_tools_used' in result:
                tools_used = result['_extracted_tools_used']
            
            # Update OpenAI usage tracking in database (async, don't block response)
            if company_id and workspace_id and agent_id and token_usage['total_tokens'] > 0:
                try:
                    asyncio.create_task(update_openai_usage(
                        company_id=company_id,
                        workspace_id=workspace_id,
                        agent_id=agent_id,
                        prompt_tokens=token_usage['prompt_tokens'],
                        completion_tokens=token_usage['completion_tokens'],
                        total_tokens=token_usage['total_tokens'],
                        model=request_mcp_manager.model  # Use dynamic model from MCP manager
                    ))
                    logger.info(f"💰 Token usage tracked (API): {token_usage['prompt_tokens']}+{token_usage['completion_tokens']}={token_usage['total_tokens']} tokens for workspace {workspace_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to track token usage (API): {e}")
                    # Don't break the response flow for tracking errors
        
            logger.info(f"✅ Form metadata processed successfully for agent {agent_id}")
        
            # Send completion call before returning response
            if message_id:
                asyncio.create_task(send_completion_call(message_id, "completed"))
        
            return JSONResponse(
                status_code=200,
                content={
                    "analysis": response_content,
                    "agent_used": "user_agent",
                    "agent_id": agent_id,
                    "workspace_id": workspace_id,
                    "metadata_processed": True,
                    "token_usage": token_usage,  # Include token usage in response
                    "tools_used": tools_used,  # Include tools used in response (NEW FIELD)
                    "message": "Form metadata processed successfully",
                    "status": "success"
                }
            )
            
        finally:
            # Step 8: Cleanup MCP manager
            try:
                # Use force cleanup with timeout like in websocket_server.py
                await asyncio.wait_for(request_mcp_manager._force_cleanup(), timeout=2.0)
                logger.info(f"🧹 MCP manager cleanup completed for agent {agent_id}")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ MCP manager cleanup timed out for agent {agent_id}")
                # Try regular cleanup as fallback
                try:
                    await asyncio.wait_for(request_mcp_manager.cleanup(), timeout=1.0)
                except:
                    pass  # Suppress any cleanup errors to prevent 500 responses
            except Exception as cleanup_error:
                logger.warning(f"⚠️ MCP manager cleanup warning for agent {agent_id}: {cleanup_error}")
                # Try regular cleanup as fallback
                try:
                    await asyncio.wait_for(request_mcp_manager.cleanup(), timeout=1.0)
                except:
                    pass  # Suppress any cleanup errors to prevent 500 responses
        
    except HTTPException:
        # Re-raise HTTP exceptions (authentication errors, etc.)
        # Send completion call for HTTP exceptions (like auth failures)
        if message_id:
            asyncio.create_task(send_completion_call(message_id, "failed"))
        raise
    except Exception as e:
        logger.error(f"❌ Error processing form metadata: {str(e)}")
        
        # Send completion call for general exceptions
        if message_id:
            asyncio.create_task(send_completion_call(message_id, "failed"))
        
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": str(e),
                "status": "error"
            }
        )

@app.post("/chat/api/subagent")
async def subagent_endpoint(request: SubagentRequest, token: str = Header(...)):
    """
    Sub-agent delegation endpoint with token authentication and agent-specific configuration.
    Processes regular chat prompts for sub-agent delegation (restored old functionality).
    """
    try:
        # Step 1: Verify the token
        logger.info(f"🔐 Verifying token for sub-agent API request...")
        auth_result = await verify_agent_token(token)
        logger.info(f"✅ Token verification successful: {auth_result.get('message', 'Authenticated')}")
        
        # Step 2: Extract agent data
        agent_data = auth_result.get('agent_data', {})
        agent_id = agent_data.get('id')
        workspace_id = agent_data.get('workspace_id')
        company_id = agent_data.get('company_id')  # Extract company_id for usage tracking
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="Agent ID not found in authentication response")
        
        logger.info(f"🤖 Processing sub-agent request for agent {agent_id}")
        
        # Step 3: Fetch service tokens (Gmail + Sheets + WhatsApp)
        logger.info(f"🔑 Fetching service tokens...")
        service_tokens = await fetch_tool_tokens(token, str(agent_id))
        
        # Extract tokens from the response
        gmail_tokens = service_tokens.get("gmail")
        sheets_tokens = service_tokens.get("sheets")
        docs_tokens = service_tokens.get("docs")
        calendar_tokens = service_tokens.get("calendar")
        whatsapp_tokens = service_tokens.get("whatsapp")
        playwright_enabled = service_tokens.get("playwright", False)
        ocr_enabled = service_tokens.get("ocr", False)
        captcha_solver_enabled = service_tokens.get("captcha_solver", False)
        youtube_tokens = service_tokens.get("youtube")
        heygen_tokens = service_tokens.get("heygen")
        airtable_tokens = service_tokens.get("airtable")
        notion_tokens = service_tokens.get("notion")
        asana_tokens = service_tokens.get("asana")
        servicenow_tokens = service_tokens.get("servicenow")
        zendesk_tokens = service_tokens.get("zendesk")
        freshdesk_tokens = service_tokens.get("freshdesk")
        salesforce_tokens = service_tokens.get("salesforce")
        pipedrive_tokens = service_tokens.get("pipedrive")
        
        # Step 4: Fetch sub-agents data
        logger.info(f"🎯 Fetching sub-agents data...")
        subagents_data = await fetch_subagents_data(token, str(agent_id))
        
        # Step 5: Fetch personality prompt, temperature, and model for this agent
        personality_prompt, agent_temperature, agent_model = await fetch_agent_config(token, str(agent_id))
        
        # Create MCP manager for this request (stateless)
        request_mcp_manager = MCPClientManager()
        
        try:
            logger.info(f"🔧 Initializing MCP manager for sub-agent request with agent_id: {agent_id}")
            await request_mcp_manager.initialize(
                agent_id=agent_id, 
                gmail_tokens=gmail_tokens, 
                sheets_tokens=sheets_tokens,
                docs_tokens=docs_tokens,
                calendar_tokens=calendar_tokens,
                whatsapp_tokens=whatsapp_tokens,
                playwright_enabled=playwright_enabled,
                ocr_enabled=ocr_enabled,
                captcha_solver_enabled=captcha_solver_enabled,
                youtube_tokens=youtube_tokens,
                heygen_tokens=heygen_tokens,
                airtable_tokens=airtable_tokens,
                notion_tokens=notion_tokens,
                asana_tokens=asana_tokens,
                servicenow_tokens=servicenow_tokens,
                zendesk_tokens=zendesk_tokens,
                freshdesk_tokens=freshdesk_tokens,
                salesforce_tokens=salesforce_tokens,
                pipedrive_tokens=pipedrive_tokens,
                personality_prompt=personality_prompt,
                temperature=agent_temperature,
                model=agent_model,
                subagents_data=subagents_data
            )
            
            # Step 7: Process the prompt using user_agent (personality-based agent)
            if not request_mcp_manager.sub_agents or "user_agent" not in request_mcp_manager.sub_agents:
                raise HTTPException(status_code=500, detail="User agent not initialized")
            
            logger.info(f"🎯 Processing prompt with user_agent...")
            selected_agent = request_mcp_manager.sub_agents["user_agent"]
            
            # Execute the prompt directly (restored old functionality)
            result = await request_mcp_manager.execute_agent_with_context(
                selected_agent, 
                request.prompt, 
                session_id=None,  # No session for REST API
                agent_id=agent_id,
                workspace_id=workspace_id,
                ip_address="api_request",  # Mark as API request
                user_agent="rest_api_subagent"
            )
        
            # Extract response content
            response_content = request_mcp_manager._extract_response_content(result)
            
            # Extract token usage for tracking
            token_usage = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
            
            if hasattr(result, '_extracted_token_usage'):
                token_usage = result._extracted_token_usage
            elif isinstance(result, dict) and '_extracted_token_usage' in result:
                token_usage = result['_extracted_token_usage']
            
            # Extract tools used for tracking (NEW FUNCTIONALITY)
            tools_used = []
            if hasattr(result, '_extracted_tools_used'):
                tools_used = result._extracted_tools_used
            elif isinstance(result, dict) and '_extracted_tools_used' in result:
                tools_used = result['_extracted_tools_used']
            
            # Update OpenAI usage tracking in database (async, don't block response)
            if company_id and workspace_id and agent_id and token_usage['total_tokens'] > 0:
                try:
                    asyncio.create_task(update_openai_usage(
                        company_id=company_id,
                        workspace_id=workspace_id,
                        agent_id=agent_id,
                        prompt_tokens=token_usage['prompt_tokens'],
                        completion_tokens=token_usage['completion_tokens'],
                        total_tokens=token_usage['total_tokens'],
                        model=request_mcp_manager.model  # Use dynamic model from MCP manager
                    ))
                    logger.info(f"💰 Token usage tracked (Sub-agent API): {token_usage['prompt_tokens']}+{token_usage['completion_tokens']}={token_usage['total_tokens']} tokens for workspace {workspace_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to track token usage (Sub-agent API): {e}")
                    # Don't break the response flow for tracking errors
        
            logger.info(f"✅ Sub-agent prompt processed successfully for agent {agent_id}")
        
            return JSONResponse(
                status_code=200,
                content={
                    "response": response_content,
                    "agent_used": "user_agent",
                    "agent_id": agent_id,
                    "workspace_id": workspace_id,
                    "prompt_processed": True,
                    "token_usage": token_usage,  # Include token usage in response
                    "tools_used": tools_used,  # Include tools used in response (NEW FIELD)
                    "message": "Sub-agent prompt processed successfully",
                    "status": "success"
                }
            )
            
        finally:
            # Step 8: Cleanup MCP manager
            try:
                # Use force cleanup with timeout like in websocket_server.py
                await asyncio.wait_for(request_mcp_manager._force_cleanup(), timeout=2.0)
                logger.info(f"🧹 MCP manager cleanup completed for sub-agent {agent_id}")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ MCP manager cleanup timed out for sub-agent {agent_id}")
                # Try regular cleanup as fallback
                try:
                    await asyncio.wait_for(request_mcp_manager.cleanup(), timeout=1.0)
                except:
                    pass  # Suppress any cleanup errors to prevent 500 responses
            except Exception as cleanup_error:
                logger.warning(f"⚠️ MCP manager cleanup warning for sub-agent {agent_id}: {cleanup_error}")
                # Try regular cleanup as fallback
                try:
                    await asyncio.wait_for(request_mcp_manager.cleanup(), timeout=1.0)
                except:
                    pass  # Suppress any cleanup errors to prevent 500 responses
        
    except HTTPException:
        # Re-raise HTTP exceptions (authentication errors, etc.)
        raise
    except Exception as e:
        logger.error(f"❌ Error processing sub-agent prompt: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": str(e),
                "status": "error"
            }
        )

# Note: Flask App Integration moved to root server.py
# This file now only handles Chat-Bot specific endpoints

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Chat-Bot WebSocket Server with Token Usage Tracking")
    print("=" * 70)
    print("✨ Features enabled:")
    print("   • Real-time token usage tracking and billing")
    print("   • MySQL database integration for usage analytics")
    print("   • Per-workspace token consumption monitoring")
    print("   • Company-based billing and cost tracking")
    print()
    print("⚠️  IMPORTANT: This server only runs Chat-Bot functionality.")
    print("⚠️  For full integration with Dashboard-Bot and Search-Bot, use: python ../server.py")
    print()
    print("📱 WebSocket Endpoints:")
    print("   • WS   /chat/ws - Real-time chat with streaming responses")
    print()
    print("🔗 API Endpoints:")
    print("   • GET  /chat/api/test - Interactive WebSocket test page")
    print("   • GET  /chat/api/health - Health check with connection status")
    print("   • POST /chat/api/query - Form metadata processing endpoint")
    print("     Headers: {\"token\": \"agent_token\"}")
    print("     Body: {\"metadata\": {\"form_data_structure\": \"...\"}}")
    print("   • POST /chat/api/subagent - Sub-agent delegation endpoint")
    print("     Headers: {\"token\": \"agent_token\"}")
    print("     Body: {\"prompt\": \"Your message here\"}")
    print()
    print("🔗 Chat-Bot Features:")
    print("   • Token-based authentication with UnleashX")
    print("   • Intelligent agent routing (uses user_agent with personality)")
    print("   • MCP tool integration and execution")
    print("   • Sub-agent delegation capabilities")
    print("   • WebSocket streaming and REST API support")
    print()
    print("🌐 Server starting on http://localhost:8001")
    print("📱 WebSocket URL: ws://localhost:8001/chat/ws?token=your_token")
    print()
    
    uvicorn.run("websocket_server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8001)), reload=True)
