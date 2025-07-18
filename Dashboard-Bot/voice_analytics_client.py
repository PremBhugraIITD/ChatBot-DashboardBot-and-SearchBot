#!/usr/bin/env python3

"""
Voice Analytics Client for Voice Analytics Bot (MCP Agent Pattern)
================================================================

This module provides the MCP client classes for voice analytics component generation
using the exact MCP implementation pattern. It contains the core agent functionality
for analyzing voice call data from the agent_executions table.

Key Features:
- Uses initialize_agent() and load_mcp_tools() for automatic MCP tool detection
- LLM automatically chooses appropriate MCP tools without manual prompting
- Workspace-based data filtering with auto-detection
- Direct analysis of agent_executions table (no form discovery needed)
- Voice call analytics focused on call quality, sentiment, agent performance
- Adaptable to new MCP servers added later

MCP Agent Pattern:
- VoiceAnalyticsAgent class uses exact pattern from dashboard_client.py
- Automatically loads MCP tools using load_mcp_tools()
- Creates LangChain agent with initialize_agent() and AgentType.OPENAI_FUNCTIONS
- Lets LLM naturally detect and call MCP tools based on user queries
- No manual JSON format specification to LLM

Usage:
    # Import and use in API server
    from voice_analytics_client import VoiceAnalyticsAgent
    
    # Create agent and process requests
    agent = VoiceAnalyticsAgent()
    await agent.initialize_mcp_agent(workspace_id)
    result = await agent.generate_analytics_component(user_prompt)
    
    Note: This is designed for REST API integration.
    All interaction should be through API endpoints.
"""

import asyncio
import os
import json
import mysql.connector
import pandas as pd
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from contextlib import AsyncExitStack

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser

# Load environment variables
load_dotenv(override=True)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# GLOBAL MODEL CONFIGURATION - SINGLE POINT OF MODEL SELECTION
# ============================================================================
MODEL = "gpt-4o-mini"  # Change this to switch models globally (gpt-4o, gpt-4o-mini, etc.)
# ============================================================================

class VoiceAnalyticsAgent:
    """MCP agent for voice analytics generation using the exact pattern from dashboard_client.py"""
    
    def __init__(self):
        self.session = None
        self.exit_stack = None
        self.agent = None
        # Add token usage tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens_used = 0
        
        # Use the global MODEL variable
        self.model_name = MODEL
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0,
            max_completion_tokens=1000
        )
    
    def set_model(self, model_name):
        """Change the model being used by the agent and update global MODEL"""
        global MODEL
        MODEL = model_name
        self.model_name = model_name
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            max_completion_tokens=1000
        )
        # The agent will be rebuilt when initialize_mcp_agent is called
        # No need to rebuild here since tools are required

    async def print_token_usage(self, workspace_id, company_id):
        """Print token usage to terminal only (no database storage)"""
        if self.total_tokens_used == 0:
            return True, "No token usage to print"
        
        try:
            # Print detailed token usage information to terminal
            print("="*80)
            print("🔥 VOICE ANALYTICS TOKEN USAGE SUMMARY")
            print("="*80)
            print(f"📍 Workspace ID: {workspace_id}")
            print(f"🏢 Company ID: {company_id}")
            print(f"🤖 Model: {self.model_name}")
            print(f"📝 Request Type: voice_analytics")
            print("-"*40)
            print(f"📊 This Request:")
            print(f"   • Prompt Tokens: {self.total_prompt_tokens}")
            print(f"   • Completion Tokens: {self.total_completion_tokens}")
            print(f"   • Total Tokens: {self.total_tokens_used}")
            print("-"*40)
            print(f"💰 Estimated Cost (GPT-4o-mini):")
            # GPT-4o-mini pricing: $0.00015 per 1K input tokens, $0.0006 per 1K output tokens
            input_cost = (self.total_prompt_tokens / 1000) * 0.00015
            output_cost = (self.total_completion_tokens / 1000) * 0.0006
            total_cost = input_cost + output_cost
            print(f"   • Input Cost: ${input_cost:.6f}")
            print(f"   • Output Cost: ${output_cost:.6f}")
            print(f"   • Total Cost: ${total_cost:.6f}")
            print("="*80)
            
            return True, "Token usage printed successfully"
            
        except Exception as e:
            print(f"❌ Failed to print token usage: {str(e)}")
            return False, f"Failed to print token usage: {str(e)}"

    def get_token_usage(self):
        """Return current token usage statistics"""
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens_used,
            "model": self.model_name
        }
    
    def reset_token_usage(self):
        """Reset token usage counters"""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens_used = 0
    
    async def initialize_mcp_agent(self):
        """Initialize MCP agent using the exact pattern from dashboard_client.py"""
        try:
            # Create exit stack for resource management
            self.exit_stack = AsyncExitStack()
            await self.exit_stack.__aenter__()
            
            # Set up voice analytics MCP server parameters (workspace_id now read from middle.json)
            server_params = StdioServerParameters(
                command="python",
                args=[os.path.join(CURRENT_DIR, "voice_analytics_server.py")]
                # No environment variables needed - workspace_id read from middle.json
            )
            
            # Connect to MCP server
            read, write = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self.session.initialize()
            
            # Load MCP tools using the exact pattern
            tools = await load_mcp_tools(self.session)
            print(f"📦 Loaded Voice Analytics MCP tools:")
            for tool in tools:
                print(f"  • {tool.name}")
            
            if not tools:
                raise RuntimeError("❌ No tools loaded from voice analytics MCP server.")
            
            # Create agent using the exact pattern from dashboard_client.py
            self.agent = initialize_agent(
                tools=tools,
                llm=self.llm,
                agent=AgentType.OPENAI_FUNCTIONS,
                verbose=True,
                agent_kwargs={
                    "system_message": """You are a Voice Analytics expert that creates data visualization components (like charts, tables, metrics, etc.) using SQL queries against the agent_executions table.
                    You specialize in analyzing voice call data, agent performance, call quality metrics, sentiment analysis, and business intelligence from phone conversations.
                    
                    You have access to MCP tools:
                    - get_agent_executions_sample_data(): Get sample data from agent_executions table to understand its structure
                    - execute_sql_query(query: str): Execute a SQL query and return results (use this to validate queries)
                    - component generation MCP tools which return HTML codes for different component types (charts, tables, metrics) by taking SQL queries as input
                    
                    MANDATORY WORKFLOW FOR VOICE ANALYTICS COMPONENT GENERATION:
                    1. UNDERSTAND: Use get_agent_executions_sample_data() to understand the table structure (only if needed)
                    2. ANALYZE: Examine component generation MCP tools to see what SQL queries they need
                    3. GENERATE: Create SQL queries targeting agent_executions table columns
                    4. VALIDATE: Use execute_sql_query to test all queries and verify they return data
                    5. CHECK: Ensure data returned matches expected format for visualization
                    6. EXECUTE: Call component generation MCP tools with validated queries
                    
                    CRITICAL RULES FOR SQL QUERY GENERATION:
                    1. You work with the agent_executions table which has standard columns (not key-value storage):
                       - Direct column access: SELECT CALL_STATUS, COUNT(*) FROM agent_executions GROUP BY CALL_STATUS
                       - Use standard SQL column names like: AGENT_ID, ACTION_TYPE, STATUS, TOTAL_DURATION, etc.                    

                    2. Key columns for voice analytics:
                       - Call Quality: TOTAL_DURATION, AGENT_TALK_RATIO, INTERRUPTIONS_COUNT, SILENCE_DURATION_TOTAL
                       - Sentiment: OVERALL_SENTIMENT, CUSTOMER_SENTIMENT_SCORE
                       - Business: IS_HOT_DEAL, IS_ESCALATED, CALL_STATUS
                       - Performance: STATUS, ERROR_MESSAGE, LLM_FAILURE_FLAG
                       - Timing: CREATED_AT, START_TIME, END_TIME
                    
                    3. Always generate relevant SQL queries based on component generation MCP tool requirements
                    
                    4. Validate each SQL query using execute_sql_query tool before using it to generate components
                    
                    5. Handle NULL/empty values properly:
                       - Use CASE statements to convert NULL/empty to 'Unknown/Empty'
                       - Example: "CASE WHEN CALL_STATUS IS NULL OR CALL_STATUS = '' THEN 'Unknown' ELSE CALL_STATUS END"
                    
                    6. Security: Only generate SELECT queries, never DROP, DELETE, INSERT, UPDATE, etc.
                    
                    Always analyze the agent_executions table structure first, then validate your SQL queries before creating components!"""
                }
            )
            
            print("✅ MCP Voice Analytics Agent initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize MCP agent: {str(e)}")
            if self.exit_stack:
                await self.exit_stack.__aexit__(None, None, None)
            return False

    async def generate_analytics_component(self, current_prompt: str, workspace_id: int, company_id: int) -> str:
        """Let agent analyze agent_executions table and generate voice analytics component"""
        if not self.agent:
            return "❌ MCP agent not initialized"
        
        try:
            prompt = f"""Analyze voice call data from the agent_executions table and create a visualization: {current_prompt}

WORKFLOW:
1. Understand the agent_executions table structure (if needed) using get_agent_executions_sample_data()
2. Generate appropriate SQL queries for voice analytics visualization
3. Validate each query using execute_sql_query tool
4. Create the component using component generation MCP tools (charts, tables, metrics) using the validated SQL queries

CRITICAL: AGENT_EXECUTIONS TABLE STRUCTURE UNDERSTANDING
- This is a standard SQL table with normal columns (not key-value storage)
- Direct column access: SELECT CALL_STATUS FROM agent_executions
- Key columns: AGENT_ID, ACTION_TYPE, STATUS, CALL_STATUS, TOTAL_DURATION, OVERALL_SENTIMENT, etc.
- Security filtering is handled automatically by the system

EXAMPLE QUERIES:
✅ CORRECT: SELECT CALL_STATUS, COUNT(*) FROM agent_executions GROUP BY CALL_STATUS
✅ CORRECT: SELECT AVG(TOTAL_DURATION) FROM agent_executions WHERE STATUS = 'completed'
✅ CORRECT: SELECT DATE(CREATED_AT) AS call_date, COUNT(*) FROM agent_executions GROUP BY DATE(CREATED_AT)

USER QUERY: {current_prompt}

Start by analyzing the agent_executions table structure and generating appropriate voice analytics queries."""

            print("🤖 Agent analyzing voice call data and generating analytics component...")
            
            # Track token usage from LLM calls
            import langchain
            from langchain.callbacks import get_openai_callback
            
            # Use callback to track token usage
            with get_openai_callback() as cb:
                result = await self.agent.ainvoke({"input": prompt})
                
                # Update token usage counters
                self.total_prompt_tokens += cb.prompt_tokens
                self.total_completion_tokens += cb.completion_tokens
                self.total_tokens_used += cb.total_tokens
                
                print(f"📊 Token usage for this request: {cb.prompt_tokens} prompt + {cb.completion_tokens} completion = {cb.total_tokens} total")
                print(f"📊 Session total tokens: {self.total_tokens_used}")
            
            # Print token usage to terminal
            try:
                success, message = await self.print_token_usage(workspace_id, company_id)
                if success:
                    print(f"✅ Token usage printed: {message}")
                else:
                    print(f"⚠️ Token usage printing failed: {message}")
            except Exception as print_error:
                print(f"❌ Token usage printing error: {print_error}")
            
            if isinstance(result, dict) and "output" in result:
                return result["output"]
            else:
                return str(result)
                
        except Exception as e:
            return f"❌ Error in agent voice analytics component generation: {str(e)}"
    
    async def cleanup(self):
        """Cleanup MCP resources"""
        if self.exit_stack:
            await self.exit_stack.__aexit__(None, None, None)

# Note: This module provides the VoiceAnalyticsAgent class
# for use by API servers. All interaction should be through REST API endpoints. 