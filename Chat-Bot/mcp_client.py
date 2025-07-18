"""
MCP Client Manager and Agent Logic

This module contains the MCP (Model Context Protocol) client initialization,
agent creation, and routing logic. It's imported by api_server.py to provide
the core AI functionality.

Key Components:
- MCPClientManager: Manages MCP server connections and tool loading
- AgentTypeParser: Parses LLM responses to determine agent routing
- create_routing_chain: Creates the intelligent routing system
- create_sub_agents: Initializes specialized sub-agents (Developer, Writer, Sales, General)

Usage:
    from mcp_client import mcp_manager
    await mcp_manager.initialize()
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_community.callbacks.manager import get_openai_callback
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.manager import CallbackManager
from contextlib import AsyncExitStack

# Import centralized MCP servers configuration
from mcp_servers_list import get_mcp_servers, set_agent_context, set_gmail_context, set_sheets_context, set_docs_context, set_calendar_context, set_whatsapp_context, set_playwright_context, set_ocr_context, set_captcha_solver_context, set_youtube_context, set_heygen_context, set_airtable_context, set_notion_context, set_subagents_context, set_asana_context, set_servicenow_context, set_zendesk_context, set_freshdesk_context, set_salesforce_context, set_pipedrive_context

load_dotenv(override=True)

# Global configuration for token limits
MAX_TOKENS = 1000  # Single point to control token usage across all agents
MAX_ITERATIONS = 30  # Limit iterations to control token usage
MAX_EXECUTION_TIME = 120  # Limit execution time in seconds

# Conversation history settings
MAX_CONVERSATION_MESSAGES = 10  # Keep last 10 messages in context
CONVERSATION_CLEANUP_HOURS = 24  # Clean up conversations older than 24 hours

class ToolUseLogger(BaseCallbackHandler):
    """Enhanced callback handler that tracks tool usage for transparency and MongoDB activity tracking."""
    
    def __init__(self):
        self.tools_used = []  # List to collect tool names
        self.tool_activities = {}  # Track MongoDB activity IDs for each tool execution
        self.agent_id = None  # Will be set when needed
        self.workspace_id = None  # Will be set when needed
    
    def set_context(self, agent_id: int, workspace_id: int):
        """Set the agent and workspace context for MongoDB tracking."""
        self.agent_id = agent_id
        self.workspace_id = workspace_id
    
    def on_tool_end(self, output, **kwargs):
        """Called when a tool finishes executing - update MongoDB status immediately."""
        # Extract tool name from kwargs
        tool_name = None
        if 'name' in kwargs:
            tool_name = kwargs['name']
        elif hasattr(kwargs.get('tool', {}), 'name'):
            tool_name = kwargs['tool'].name
        elif 'serialized' in kwargs and isinstance(kwargs['serialized'], dict):
            tool_name = kwargs['serialized'].get('name')
        
        if tool_name and tool_name in self.tool_activities:
            # Update the specific tool as completed immediately
            self.update_tool_activity(tool_name, output, "completed")
            print(f"🔧 Tool completed individually: {tool_name}")
    
    def on_tool_error(self, error, **kwargs):
        """Called when a tool execution fails - update MongoDB status as failed."""
        # Extract tool name from kwargs
        tool_name = None
        if 'name' in kwargs:
            tool_name = kwargs['name']
        elif hasattr(kwargs.get('tool', {}), 'name'):
            tool_name = kwargs['tool'].name
        elif 'serialized' in kwargs and isinstance(kwargs['serialized'], dict):
            tool_name = kwargs['serialized'].get('name')
        
        if tool_name and tool_name in self.tool_activities:
            # Update the specific tool as failed immediately
            self.update_tool_activity(tool_name, str(error), "failed")
            print(f"❌ Tool failed individually: {tool_name}")
    
    def on_llm_end(self, response, **kwargs):
        """Called when LLM ends - look for function calls in the response."""
        # Extract tool names from LLM response
        if hasattr(response, 'generations') and response.generations:
            for generation_list in response.generations:
                for generation in generation_list:
                    if hasattr(generation, 'message') and hasattr(generation.message, 'additional_kwargs'):
                        # Check for tool calls in the message
                        additional_kwargs = generation.message.additional_kwargs
                        if 'function_call' in additional_kwargs:
                            function_call = additional_kwargs['function_call']
                            if 'name' in function_call:
                                tool_name = function_call['name']
                                tool_args = {}
                                try:
                                    import json
                                    tool_args = json.loads(function_call.get('arguments', '{}'))
                                except:
                                    tool_args = {}
                                
                                if tool_name not in self.tools_used:
                                    self.tools_used.append(tool_name)
                                    print(f"🛠️  Tool detected from LLM response: {tool_name}")
                                
                                # Create MongoDB activity record
                                self._create_tool_activity(tool_name, tool_args)
                        
                        # Check for tool_calls (newer format)
                        if 'tool_calls' in additional_kwargs:
                            tool_calls = additional_kwargs['tool_calls']
                            if isinstance(tool_calls, list):
                                for tool_call in tool_calls:
                                    if isinstance(tool_call, dict) and 'function' in tool_call:
                                        function_info = tool_call['function']
                                        if 'name' in function_info:
                                            tool_name = function_info['name']
                                            tool_args = {}
                                            try:
                                                import json
                                                tool_args = json.loads(function_info.get('arguments', '{}'))
                                            except:
                                                tool_args = {}
                                            
                                            if tool_name not in self.tools_used:
                                                self.tools_used.append(tool_name)
                                                print(f"🛠️  Tool detected from LLM tool_calls: {tool_name}")
                                            
                                            # Create MongoDB activity record
                                            self._create_tool_activity(tool_name, tool_args)
    
    def _create_tool_activity(self, tool_name: str, tool_args: dict):
        """Create a MongoDB activity record for tool execution."""
        if not self.agent_id or not self.workspace_id:
            return  # Skip if context not set
        
        try:
            # Import MongoDB manager
            import importlib.util
            import os
            mongodb_manager_path = os.path.join(os.path.dirname(__file__), 'mongodb_manager.py')
            spec = importlib.util.spec_from_file_location("aiagent_mongodb_manager", mongodb_manager_path)
            mongodb_manager_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mongodb_manager_module)
            
            # Create tool activity in MongoDB
            activity_id = mongodb_manager_module.mongodb_manager.create_tool_activity(
                agent_id=self.agent_id,
                workspace_id=self.workspace_id,
                tool_called=tool_name,
                tool_input=tool_args
            )
            
            if activity_id:
                # Store the activity ID for later updates
                self.tool_activities[tool_name] = activity_id
                print(f"📊 Tool activity created in MongoDB: {tool_name} | ID: {activity_id}")
            
        except Exception as e:
            print(f"❌ Failed to create tool activity in MongoDB: {e}")
    
    def update_tool_activity(self, tool_name: str, tool_output: any, status: str = "completed"):
        """Update a MongoDB activity record when tool execution completes."""
        if tool_name not in self.tool_activities:
            return  # No activity to update
        
        try:
            # Import MongoDB manager
            import importlib.util
            import os
            mongodb_manager_path = os.path.join(os.path.dirname(__file__), 'mongodb_manager.py')
            spec = importlib.util.spec_from_file_location("aiagent_mongodb_manager", mongodb_manager_path)
            mongodb_manager_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mongodb_manager_module)
            
            # Update tool activity in MongoDB
            activity_id = self.tool_activities[tool_name]
            success = mongodb_manager_module.mongodb_manager.update_tool_activity(
                activity_id=activity_id,
                tool_output=tool_output,
                status=status
            )
            
            if success:
                print(f"📊 Tool activity updated in MongoDB: {tool_name} | Status: {status}")
                # Remove from tracking after successful update
                del self.tool_activities[tool_name]
            
        except Exception as e:
            print(f"❌ Failed to update tool activity in MongoDB: {e}")
    
    def get_tools_used(self):
        """Get the list of tools used during execution."""
        return self.tools_used.copy()
    
    def reset(self):
        """Reset the tools used list for a new execution."""
        self.tools_used = []
        self.tool_activities = {}  # Also reset activity tracking

class ConversationMessage:
    """Represents a single message in a conversation."""
    
    def __init__(self, role: str, content: str, agent_type: str = None, timestamp: datetime = None):
        self.role = role  # 'user' or 'assistant'
        self.content = content
        self.agent_type = agent_type  # Which agent responded (for assistant messages)
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "agent_type": self.agent_type,
            "timestamp": self.timestamp.isoformat()
        }

class ConversationSession:
    """Manages conversation history for a single session."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[ConversationMessage] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    def add_message(self, role: str, content: str, agent_type: str = None):
        """Add a message to the conversation history."""
        message = ConversationMessage(role, content, agent_type)
        self.messages.append(message)
        self.last_activity = datetime.now()
        
        # Keep only the last MAX_CONVERSATION_MESSAGES to manage token usage
        if len(self.messages) > MAX_CONVERSATION_MESSAGES:
            self.messages = self.messages[-MAX_CONVERSATION_MESSAGES:]
    
    def get_context_string(self) -> str:
        """Get conversation history as a formatted string for agent context."""
        if not self.messages:
            return ""
        
        context_parts = ["Previous conversation context:"]
        for msg in self.messages[-MAX_CONVERSATION_MESSAGES:]:
            if msg.role == "user":
                context_parts.append(f"User: {msg.content}")
            else:
                agent_info = f" ({msg.agent_type} agent)" if msg.agent_type else ""
                context_parts.append(f"Assistant{agent_info}: {msg.content}")
        
        context_parts.append("---")
        return "\n".join(context_parts)
    
    def is_expired(self) -> bool:
        """Check if conversation session has expired."""
        return datetime.now() - self.last_activity > timedelta(hours=CONVERSATION_CLEANUP_HOURS)

class ConversationManager:
    """Manages all conversation sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
    
    def get_or_create_session(self, session_id: str) -> ConversationSession:
        """Get existing session or create a new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationSession(session_id)
        return self.sessions[session_id]
    
    def cleanup_expired_sessions(self):
        """Remove expired conversation sessions."""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            print(f"🧹 Cleaned up {len(expired_sessions)} expired conversation sessions")

# Global conversation manager
conversation_manager = ConversationManager()

def create_sub_agents(all_tools, llm, personality_prompt=None, subagents_data=None, tool_logger=None):
    """Create the user agent with dynamic personality prompt and sub-agents information."""
    
    # Start with the base personality prompt
    user_agent_prompt = personality_prompt if personality_prompt else """You are a helpful AI assistant with access to various tools and services. 
    You can help with a wide variety of tasks and questions, including knowledge base queries, document management, 
    communication tools, and general assistance.
    
    Always be helpful, accurate, and use the appropriate tools when needed to assist users with their requests.
    You can refer to previous messages in the conversation to provide contextual responses and maintain conversation flow.
    
    IMPORTANT: Provide clear, concise responses that directly address the user's needs."""
    
    # Enhance with sub-agents information if available
    if subagents_data and len(subagents_data) > 0:
        subagents_info = "\n\nYou also have access to specialized sub-agents that can handle specific tasks:\n"
        
        for subagent in subagents_data:
            subagent_id = subagent.get("id")
            subagent_name = subagent.get("name")
            subagent_tools = subagent.get("tools", [])
            
            if subagent_id and subagent_name and subagent_tools:
                tools_list = ", ".join(subagent_tools)
                subagents_info += f"- Sub-agent {subagent_id} ({subagent_name}): Has access to {tools_list}\n"
        
        subagents_info += "\nIMPORTANT: Only delegate tasks to sub-agents using the call_subagent tool when you cannot handle the task with your own available tools. Always try to process requests with your own capabilities first. Use sub-agent delegation as a last resort when you lack the specific tools or access needed for the task. When delegating, use the sub-agent ID and provide a clear, detailed task description."
        
        # Append sub-agents information to the personality prompt
        user_agent_prompt += subagents_info
        
        print(f"🎯 Enhanced personality prompt with {len(subagents_data)} sub-agents information")
    else:
        print("⚠️ No sub-agents data provided - using base personality prompt only")
    
    # Log the complete agent_kwargs for debugging
    print("=" * 80)
    print("🤖 AGENT INITIALIZATION - Complete Personality Prompt:")
    print("=" * 80)
    print(user_agent_prompt)
    print("=" * 80)
    
    # Create callback manager with tool logger if provided
    callback_manager = None
    if tool_logger:
        callback_manager = CallbackManager([tool_logger])

    user_agent = initialize_agent(
        tools=all_tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        max_iterations=MAX_ITERATIONS,
        max_execution_time=MAX_EXECUTION_TIME,
        handle_parsing_errors=True,
        callback_manager=callback_manager,
        agent_kwargs={
            "system_message": user_agent_prompt
        }
    )
    
    return {
        "user_agent": user_agent
    }

class MCPClientManager:
    """Manages MCP clients and tools for the API server."""
    
    def __init__(self):
        self.stack = None
        self.server_tools = {}
        self.all_tools = []
        self.sub_agents = None
        self.agent = None
        self.temperature = 0.7  # Default temperature, will be overridden by API value
        self.model = "gpt-4o-mini"  # Default model, will be overridden by API value
        self._initialization_lock = asyncio.Lock()
        self._is_initializing = False
        self.tool_logger = ToolUseLogger()  # Tool usage tracker
    
    async def initialize(self, agent_id=None, gmail_tokens=None, sheets_tokens=None, docs_tokens=None, calendar_tokens=None, whatsapp_tokens=None, playwright_enabled=None, ocr_enabled=None, captcha_solver_enabled=None, youtube_tokens=None, heygen_tokens=None, airtable_tokens=None, notion_tokens=None, asana_tokens=None, servicenow_tokens=None, zendesk_tokens=None, freshdesk_tokens=None, salesforce_tokens=None, pipedrive_tokens=None, personality_prompt=None, temperature=None, model=None, subagents_data=None):
        """Initialize all MCP servers and create agents with proper cleanup handling."""
        async with self._initialization_lock:
            try:
                # If already initializing, wait for it to complete
                if self._is_initializing:
                    print("⚠️ MCP initialization already in progress, waiting...")
                    return
                
                self._is_initializing = True
                
                # Force cleanup of any existing connections first
                await self._force_cleanup()
                
                # Reset all state
                self.server_tools = {}
                self.all_tools = []
                self.sub_agents = None
                self.agent = None
                
                # Set agent context for dynamic MCP server configuration
                if agent_id:
                    set_agent_context(agent_id)
                    print(f"🔧 Set agent context: {agent_id}")
                
                # Store temperature from API (use API value even if 0)
                if temperature is not None:
                    self.temperature = temperature
                    print(f"🌡️ Set agent temperature: {temperature}")
                else:
                    self.temperature = 0.7  # Fallback (should not happen with API integration)
                    print(f"⚠️ No temperature provided, using default: 0.7")
                
                # Store model from API (use API value or default)
                if model is not None:
                    self.model = model
                    print(f"🤖 Set agent model: {model}")
                else:
                    self.model = "gpt-4o-mini"  # Fallback (should not happen with API integration)
                    print(f"⚠️ No model provided, using default: gpt-4o-mini")
                
                # Set Gmail context for dynamic Gmail server configuration (same pattern as agent_id)
                if gmail_tokens:
                    set_gmail_context(gmail_tokens)
                    print(f"🔑 Set Gmail context for agent: {agent_id}")
                else:
                    # Clear Gmail context if no tokens provided
                    set_gmail_context(None)
                    print(f"⚠️ No Gmail tokens provided for agent: {agent_id}")
                
                # Set Google Sheets context for dynamic Sheets server configuration (same pattern as Gmail)
                if sheets_tokens:
                    set_sheets_context(sheets_tokens)
                    print(f"🔑 Set Google Sheets context for agent: {agent_id}")
                else:
                    # Clear Sheets context if no tokens provided
                    set_sheets_context(None)
                    print(f"⚠️ No Google Sheets tokens provided for agent: {agent_id}")
                
                # Set Google Docs context for dynamic Docs server configuration (same pattern as Gmail/Sheets)
                if docs_tokens:
                    set_docs_context(docs_tokens)
                    print(f"🔑 Set Google Docs context for agent: {agent_id}")
                else:
                    # Clear Docs context if no tokens provided
                    set_docs_context(None)
                    print(f"⚠️ No Google Docs tokens provided for agent: {agent_id}")
                
                # Set Google Calendar context for dynamic Calendar server configuration (same pattern as Gmail/Sheets)
                if calendar_tokens:
                    set_calendar_context(calendar_tokens)
                    print(f"🔑 Set Google Calendar context for agent: {agent_id}")
                else:
                    # Clear Calendar context if no tokens provided
                    set_calendar_context(None)
                    print(f"⚠️ No Google Calendar tokens provided for agent: {agent_id}")
                
                # Set WhatsApp Business context for dynamic WhatsApp server configuration (same pattern as Gmail/Sheets)
                if whatsapp_tokens:
                    set_whatsapp_context(whatsapp_tokens)
                    print(f"📱 Set WhatsApp Business context for agent: {agent_id}")
                else:
                    # Clear WhatsApp context if no tokens provided
                    set_whatsapp_context(None)
                    print(f"⚠️ No WhatsApp Business tokens provided for agent: {agent_id}")
                
                # Set Playwright context for dynamic Playwright server configuration (same pattern as other special servers)
                if playwright_enabled:
                    set_playwright_context(True)
                    print(f"🎭 Set Playwright context enabled for agent: {agent_id}")
                else:
                    # Clear Playwright context if not enabled
                    set_playwright_context(False)
                    print(f"⚠️ Playwright not enabled for agent: {agent_id}")
                
                # Set OCR context for dynamic OCR server configuration (same pattern as Playwright)
                if ocr_enabled:
                    set_ocr_context(True)
                    print(f"👁️ Set OCR context enabled for agent: {agent_id}")
                else:
                    # Clear OCR context if not enabled
                    set_ocr_context(False)
                    print(f"⚠️ OCR not enabled for agent: {agent_id}")
                
                # Set CAPTCHA solver context for dynamic CAPTCHA solver server configuration (same pattern as Playwright/OCR)
                if captcha_solver_enabled:
                    set_captcha_solver_context(True)
                    print(f"🔐 Set CAPTCHA solver context enabled for agent: {agent_id}")
                else:
                    # Clear CAPTCHA solver context if not enabled
                    set_captcha_solver_context(False)
                    print(f"⚠️ CAPTCHA solver not enabled for agent: {agent_id}")
                
                # Set YouTube context for dynamic YouTube server configuration (same pattern as Gmail/Sheets)
                if youtube_tokens:
                    set_youtube_context(youtube_tokens)
                    print(f"📺 Set YouTube context for agent: {agent_id}")
                else:
                    # Clear YouTube context if no tokens provided
                    set_youtube_context(None)
                    print(f"⚠️ No YouTube tokens provided for agent: {agent_id}")
                
                # Set HeyGen context for dynamic HeyGen server configuration (same pattern as Gmail/Sheets)
                if heygen_tokens:
                    set_heygen_context(heygen_tokens)
                    print(f"🎬 Set HeyGen context for agent: {agent_id}")
                else:
                    # Clear HeyGen context if no tokens provided
                    set_heygen_context(None)
                    print(f"⚠️ No HeyGen tokens provided for agent: {agent_id}")
                
                # Set Airtable context for dynamic Airtable server configuration (same pattern as Gmail/Sheets)
                if airtable_tokens:
                    set_airtable_context(airtable_tokens)
                    print(f"📊 Set Airtable context for agent: {agent_id}")
                else:
                    # Clear Airtable context if no tokens provided
                    set_airtable_context(None)
                    print(f"⚠️ No Airtable tokens provided for agent: {agent_id}")
                
                # Set Notion context for dynamic Notion server configuration (same pattern as Gmail/Sheets)
                if notion_tokens:
                    set_notion_context(notion_tokens)
                    print(f"📝 Set Notion context for agent: {agent_id}")
                else:
                    # Clear Notion context if no tokens provided
                    set_notion_context(None)
                    print(f"⚠️ No Notion tokens provided for agent: {agent_id}")
                
                # Set Asana context for dynamic Asana server configuration (special server)
                if asana_tokens:
                    set_asana_context(asana_tokens)
                    print(f"\u2705 Set Asana context for agent: {agent_id}")
                else:
                    set_asana_context(None)
                    print(f"\u26a0\ufe0f No Asana tokens provided for agent: {agent_id}")
                # Set Servicenow context for dynamic Servicenow server configuration (special server)
                if servicenow_tokens:
                    set_servicenow_context(servicenow_tokens)
                    print(f"\u2705 Set Servicenow context for agent: {agent_id}")
                else:
                    set_servicenow_context(None)
                    print(f"\u26a0\ufe0f No Servicenow tokens provided for agent: {agent_id}")
                # Set Zendesk context for dynamic Zendesk server configuration (special server)
                if zendesk_tokens:
                    set_zendesk_context(zendesk_tokens)
                    print(f"\u2705 Set Zendesk context for agent: {agent_id}")
                else:
                    set_zendesk_context(None)
                    print(f"\u26a0\ufe0f No Zendesk tokens provided for agent: {agent_id}")
                # Set Freshdesk context for dynamic Freshdesk server configuration (special server)
                if freshdesk_tokens:
                    set_freshdesk_context(freshdesk_tokens)
                    print(f"\u2705 Set Freshdesk context for agent: {agent_id}")
                else:
                    set_freshdesk_context(None)
                    print(f"\u26a0\ufe0f No Freshdesk tokens provided for agent: {agent_id}")
                
                # Set sub-agents context for delegation by subagents MCP server
                if subagents_data:
                    set_subagents_context(subagents_data)
                    print(f"🎯 Set sub-agents context for agent: {agent_id}")
                else:
                    # Clear sub-agents context if no data provided
                    set_subagents_context(None)
                    print(f"⚠️ No sub-agents data provided for agent: {agent_id}")
                
                # Set Salesforce context for dynamic Salesforce server configuration (special server)
                if salesforce_tokens:
                    set_salesforce_context(salesforce_tokens)
                    print(f"\u2705 Set Salesforce context for agent: {agent_id}")
                else:
                    set_salesforce_context(None)
                    print(f"\u26a0\ufe0f No Salesforce tokens provided for agent: {agent_id}")
                # Set Pipedrive context for dynamic Pipedrive server configuration (special server)
                if pipedrive_tokens:
                    set_pipedrive_context(pipedrive_tokens)
                    print(f"\u2705 Set Pipedrive context for agent: {agent_id}")
                else:
                    set_pipedrive_context(None)
                    print(f"\u26a0\ufe0f No Pipedrive tokens provided for agent: {agent_id}")
                
                # Create new stack
                self.stack = AsyncExitStack()
                await self.stack.__aenter__()
                
                try:
                    # Get dynamic MCP servers configuration
                    mcp_servers = get_mcp_servers()

                    # Spin up each MCP server and load its tools
                    for cfg in mcp_servers:
                        server_id = cfg["id"]
                        params = StdioServerParameters(
                            command=cfg["command"],
                            args=cfg["args"],
                            env=cfg.get("env", {}),
                        )
                        try:
                            read, write = await self.stack.enter_async_context(stdio_client(params))
                            session = await self.stack.enter_async_context(ClientSession(read, write))
                            await session.initialize()
                        except Exception as e:
                            print(f"⚠️  Failed to connect/init {cfg['args'][0]}: {e}")
                            continue

                        try:
                            tools = await load_mcp_tools(session)
                            print(f"📦 Loaded tools from {cfg['args'][0]}:")
                            for t in tools:
                                print(f"  • {t.name}")
                            # Store per-server tool list
                            self.server_tools[server_id] = tools
                            self.all_tools.extend(tools)
                        except Exception as e:
                            print(f"⚠️  Failed to load tools from {cfg['args'][0]}: {e}")

                    if not self.all_tools:
                        raise RuntimeError("❌ No tools loaded from any MCP server.")

                    # Initialize LLM with dynamic model, token limits for cost control and dynamic temperature
                    llm = ChatOpenAI(
                        model=self.model,  # Use dynamic model from API
                        max_tokens=MAX_TOKENS,  # Single point token control
                        temperature=self.temperature,  # Use temperature from API
                        request_timeout=30
                    )
                    
                    # Create sub-agents with sub-agents data and tool logger
                    self.sub_agents = create_sub_agents(self.all_tools, llm, personality_prompt, subagents_data, self.tool_logger)
                    
                    # Keep the original agent for backward compatibility
                    self.agent = initialize_agent(
                        tools=self.all_tools,
                        llm=llm,
                        agent=AgentType.OPENAI_FUNCTIONS,
                        verbose=True,
                        max_iterations=MAX_ITERATIONS,
                        max_execution_time=MAX_EXECUTION_TIME,
                        handle_parsing_errors=True,
                    )

                    print("🤖 Initialized user agent with personality prompt")
                    
                except Exception as e:
                    await self._force_cleanup()
                    raise e
                finally:
                    self._is_initializing = False
                    
            except Exception as e:
                self._is_initializing = False
                raise e
    
    async def _force_cleanup(self):
        """Force cleanup of resources, handling any errors gracefully."""
        if self.stack:
            try:
                # Use asyncio.wait_for to add timeout to cleanup
                await asyncio.wait_for(self.stack.__aexit__(None, None, None), timeout=5.0)
            except asyncio.TimeoutError:
                print("⚠️ Stack cleanup timed out after 5 seconds")
            except Exception as e:
                print(f"⚠️ Warning during stack cleanup: {e}")
            finally:
                self.stack = None
    
    async def cleanup(self):
        """Clean up resources with proper error handling."""
        async with self._initialization_lock:
            # Cancel any running tasks first
            current_task = asyncio.current_task()
            if current_task:
                try:
                    # Get all tasks except current one
                    tasks = [task for task in asyncio.all_tasks() if task != current_task and not task.done()]
                    if tasks:
                        print(f"🔄 Cancelling {len(tasks)} running tasks")
                        for task in tasks:
                            if hasattr(task, 'get_name') and 'mcp' in task.get_name().lower():
                                task.cancel()
                        
                        # Wait briefly for tasks to cancel
                        await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"⚠️ Warning cancelling tasks: {e}")
            
            # Force cleanup of MCP resources
            await self._force_cleanup()
            
            # Reset all state
            self.server_tools = {}
            self.all_tools = []
            self.sub_agents = None
            self.agent = None
        
        # Clean up expired conversation sessions
        try:
            conversation_manager.cleanup_expired_sessions()
        except Exception as e:
            print(f"⚠️ Warning cleaning up conversation sessions: {e}")
    
    async def execute_agent_with_context(self, agent, query: str, session_id: str = None, agent_id: int = None, workspace_id: int = None, ip_address: str = None, user_agent: str = None) -> str:
        """Execute an agent with conversation context if available."""
        # Reset tool logger for this execution
        self.tool_logger.reset()
        
        # Set MongoDB context for tool activity tracking
        if agent_id and workspace_id:
            self.tool_logger.set_context(agent_id, workspace_id)
        
        if session_id:
            # Get conversation session and add user message
            session = conversation_manager.get_or_create_session(session_id)
            session.add_message("user", query)
            
            # Store user message in MongoDB immediately
            try:
                # Use absolute path to ensure we get the correct mongodb_manager
                import importlib.util
                import os
                mongodb_manager_path = os.path.join(os.path.dirname(__file__), 'mongodb_manager.py')
                spec = importlib.util.spec_from_file_location("aiagent_mongodb_manager", mongodb_manager_path)
                mongodb_manager_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mongodb_manager_module)
                
                await mongodb_manager_module.mongodb_manager.store_message_async(
                    session_id=session_id,
                    message_content=query,
                    sender_type="user",
                    agent_used="",  # Will be determined after routing
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            except Exception as e:
                # Log error but don't break the response flow
                print(f"❌ Failed to store user message in MongoDB: {e}")
            
            # Prepare query with conversation context
            context = session.get_context_string()
            if context:
                contextual_query = f"{context}\n\nCurrent user message: {query}"
            else:
                contextual_query = query
        else:
            contextual_query = query
        
        # Execute the agent with timeout and proper cancellation handling
        try:
            result = await asyncio.wait_for(
                self._execute_agent_isolated(agent, contextual_query),
                timeout=60.0  # 60 second timeout for agent execution
            )
        except asyncio.TimeoutError:
            # Update any pending tool activities as failed
            self._update_pending_tool_activities("failed", "Execution timeout")
            raise Exception("Agent execution timed out after 60 seconds")
        except asyncio.CancelledError:
            # Update any pending tool activities as failed
            self._update_pending_tool_activities("failed", "Execution cancelled")
            print(f"🔄 Agent execution cancelled for session {session_id}")
            raise
        except Exception as e:
            # Update any pending tool activities as failed
            self._update_pending_tool_activities("failed", str(e))
            raise
        
        # Extract response content and add to conversation history
        response_content = self._extract_response_content(result)
        
        # Check if any tools are still pending and update them
        # (This is a fallback in case on_tool_end wasn't called for some tools)
        if self.tool_logger.tool_activities:
            print(f"⚠️  Found {len(self.tool_logger.tool_activities)} pending tool activities, updating as completed")
            self._update_pending_tool_activities("completed", response_content)
        
        # Extract token usage for tracking (this will be used by calling function)
        token_usage = self._extract_token_usage(result)
        
        # Extract tools used for tracking (NEW FUNCTIONALITY)
        tools_used = self.tool_logger.get_tools_used()
        
        # Store token usage and tools used in result for external access
        if isinstance(result, dict):
            result['_extracted_token_usage'] = token_usage
            result['_extracted_tools_used'] = tools_used
        else:
            result._extracted_token_usage = token_usage
            result._extracted_tools_used = tools_used
        
        if session_id and response_content:
            session = conversation_manager.get_or_create_session(session_id)
            # Determine agent type from the agent object
            agent_type = self._get_agent_type(agent)
            session.add_message("assistant", response_content, agent_type)
            
            # Store bot response in MongoDB
            try:
                # Use absolute path to ensure we get the correct mongodb_manager
                import importlib.util
                import os
                mongodb_manager_path = os.path.join(os.path.dirname(__file__), 'mongodb_manager.py')
                spec = importlib.util.spec_from_file_location("aiagent_mongodb_manager", mongodb_manager_path)
                mongodb_manager_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mongodb_manager_module)
                
                await mongodb_manager_module.mongodb_manager.store_message_async(
                    session_id=session_id,
                    message_content=response_content,
                    sender_type="bot",
                    agent_used=agent_type,
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            except Exception as e:
                # Log error but don't break the response flow
                print(f"❌ Failed to store bot response in MongoDB: {e}")
        
        return result
    
    async def _execute_agent_isolated(self, agent, query: str):
        """Execute agent in an isolated context and capture token usage."""
        with get_openai_callback() as cb:
            # Pass the tool logger as a callback to the agent execution
            callbacks = [self.tool_logger] if self.tool_logger else []
            
            # Execute the agent with callbacks
            result = await agent.ainvoke(query, config={"callbacks": callbacks})
            
            # Attach token usage to result for later extraction
            token_usage = {
                'prompt_tokens': cb.prompt_tokens,
                'completion_tokens': cb.completion_tokens,
                'total_tokens': cb.total_tokens,
                'successful_requests': cb.successful_requests,
                'total_cost': getattr(cb, 'total_cost', 0.0)
            }
            
            # Store token usage in result object
            if isinstance(result, dict):
                result['_token_usage'] = token_usage
            else:
                # For other result types, add as attribute
                result._token_usage = token_usage
                
            return result
    
    def _extract_response_content(self, result) -> str:
        """Extract text content from agent response."""
        if isinstance(result, dict):
            return result.get('output') or result.get('content') or result.get('text') or str(result)
        elif hasattr(result, 'content'):
            return result.content
        elif hasattr(result, 'output'):
            return result.output
        elif hasattr(result, 'text'):
            return result.text
        else:
            return str(result)
    
    def _get_agent_type(self, agent) -> str:
        """Determine agent type from agent object."""
        return "user_agent"
    
    def _extract_token_usage(self, result) -> Dict[str, int]:
        """Extract token usage from agent result."""
        if isinstance(result, dict) and '_token_usage' in result:
            return result['_token_usage']
        elif hasattr(result, '_token_usage'):
            return result._token_usage
        else:
            return {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'successful_requests': 0,
                'total_cost': 0.0
            }
    
    def _extract_tools_used(self, result) -> List[str]:
        """Extract tools used from agent result."""
        if isinstance(result, dict) and '_extracted_tools_used' in result:
            return result['_extracted_tools_used']
        elif hasattr(result, '_extracted_tools_used'):
            return result._extracted_tools_used
        else:
            return []
    
    def _update_pending_tool_activities(self, status: str, output: any):
        """Update any pending tool activities with completion status."""
        for tool_name in list(self.tool_logger.tool_activities.keys()):
            self.tool_logger.update_tool_activity(tool_name, output, status)

# Create a global instance
mcp_manager = MCPClientManager()