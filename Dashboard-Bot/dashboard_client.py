#!/usr/bin/env python3

"""
Dashboard Client for Dashboard-Bot Version 4 (MCP Agent Pattern)
===============================================================

This module provides the MCP client classes for dashboard component generation
using the exact MCP implementation pattern. It contains the core agent functionality
used by the API server for intelligent form discovery and component generation.

Key Features:
- Uses initialize_agent() and load_mcp_tools() for automatic MCP tool detection
- LLM automatically chooses appropriate MCP tools without manual prompting
- Workspace-based form filtering with auto-detection
- Smart form selection from form_objects table
- Database analysis with SQL queries
- Adaptable to new MCP servers added later

MCP Agent Pattern:
- DashboardAgent class uses exact pattern from mcp_client_interactive.py
- Automatically loads MCP tools using load_mcp_tools()
- Creates LangChain agent with initialize_agent() and AgentType.OPENAI_FUNCTIONS
- Lets LLM naturally detect and call MCP tools based on user queries
- No manual JSON format specification to LLM

Usage:
    # Import and use in API server
    from dashboard_client import DashboardAgent
    
    # Create agent and process requests
    agent = DashboardAgent()
    await agent.initialize_mcp_agent(workspace_id)
    result = await agent.generate_component_with_discovery(user_prompt)
    
    Note: CLI functionality has been removed in Version 4.
    All interaction is now through REST API endpoints (/chat/forms/*).
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

class DashboardAgent:
    """MCP agent for dashboard generation using the exact pattern from mcp_client_interactive.py"""
    
    def __init__(self):
        self.session = None
        self.exit_stack = None
        self.agent = None
        # Add token usage tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens_used = 0
        
        # Set the model name directly in the code
        self.model_name = "gpt-4o-mini"  # Default model for dashboard generation
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0,
            max_tokens=1000,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
    
    def set_model(self, model_name):
        """Change the model being used by the agent"""
        self.model_name = model_name
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            max_tokens=1000,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        # The agent will be rebuilt when initialize_mcp_agent is called
        # No need to rebuild here since tools are required

    async def store_token_usage_to_db(self, workspace_id, company_id):
        """Store token usage directly to database from dashboard client"""
        if self.total_tokens_used == 0:
            return True, "No token usage to store"
        
        try:
            import mysql.connector
            
            # Connect to MySQL database
            connection = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST'),
                user=os.getenv('MYSQL_USER'),
                password=os.getenv('MYSQL_PASSWORD'),
                database=os.getenv('MYSQL_DATABASE')
            )
            
            cursor = connection.cursor()
            
            # Check if record exists for this workspace and model
            check_query = """
            SELECT ID, TOTAL_TOKENS_USED, PROMPT_TOKENS, COMPLETION_TOKENS, REQUEST_COUNT 
            FROM openai_usage 
            WHERE WORKSPACE_ID = %s AND MODEL = %s AND REQUEST_TYPE = 'image' AND CREDENTIAL_USED = 'internal'
            """
            cursor.execute(check_query, (workspace_id, self.model_name))
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Update existing record
                record_id, existing_total, existing_prompt, existing_completion, existing_count = existing_record
                
                new_total = existing_total + self.total_tokens_used
                new_prompt = existing_prompt + self.total_prompt_tokens
                new_completion = existing_completion + self.total_completion_tokens
                new_count = existing_count + 1
                
                update_query = """
                UPDATE openai_usage 
                SET TOTAL_TOKENS_USED = %s, PROMPT_TOKENS = %s, COMPLETION_TOKENS = %s, REQUEST_COUNT = %s, UPDATED_AT = CURRENT_TIMESTAMP
                WHERE ID = %s
                """
                cursor.execute(update_query, (new_total, new_prompt, new_completion, new_count, record_id))
                
                print(f"💾 Updated OpenAI usage for workspace {workspace_id}, model {self.model_name}: +{self.total_tokens_used} tokens (total: {new_total}), request #{new_count}")
                
            else:
                # Create new record
                insert_query = """
                INSERT INTO openai_usage 
                (COMPANY_ID, WORKSPACE_ID, MODEL, TOTAL_TOKENS_USED, PROMPT_TOKENS, COMPLETION_TOKENS, REQUEST_TYPE, REQUEST_COUNT, CREDENTIAL_USED)
                VALUES (%s, %s, %s, %s, %s, %s, 'image', 1, 'internal')
                """
                cursor.execute(insert_query, (company_id, workspace_id, self.model_name, self.total_tokens_used, self.total_prompt_tokens, self.total_completion_tokens))
                
                print(f"💾 Created OpenAI usage record for workspace {workspace_id}, model {self.model_name}: {self.total_tokens_used} tokens, request #1")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return True, "Token usage stored successfully"
            
        except Exception as e:
            print(f"❌ Failed to store token usage: {str(e)}")
            return False, f"Failed to store token usage: {str(e)}"

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
        """Initialize MCP agent using the exact pattern from mcp_client_interactive.py"""
        try:
            # Create exit stack for resource management
            self.exit_stack = AsyncExitStack()
            await self.exit_stack.__aenter__()
            
            # Set up dashboard MCP server parameters (workspace_id now read from middle.json)
            server_params = StdioServerParameters(
                command="python",
                args=[os.path.join(CURRENT_DIR,"dashboard_server.py")]
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
            print(f"📦 Loaded MCP tools:")
            for tool in tools:
                print(f"  • {tool.name}")
            
            if not tools:
                raise RuntimeError("❌ No tools loaded from dashboard MCP server.")
            
            # Create agent using the exact pattern from mcp_client_interactive.py
            self.agent = initialize_agent(
                tools=tools,
                llm=self.llm,
                agent=AgentType.OPENAI_FUNCTIONS,
                verbose=True,
                agent_kwargs={
                    "system_message": """You are a Dashboard expert that creates data visualization components (like charts, tables, metrics, etc.) using SQL queries against real database tables.
                    You specialize in finding relevant forms, analyzing table structures, and generating accurate SQL queries for component generation.
                    
                    You have access to MCP tools:
                    - form searching mcp tools which allow you to search for relevant form by name or patterns
                    - get_table_sample_data(table_name: str): Get sample data from the secondary table to understand its structure
                    - execute_sql_query(query: str): Execute a SQL query and return results (use this to validate queries)
                    - component generation MCP tools which return HTML codes for different component types (charts, tables, metrics) by taking SQL queries as input
                    
                    MANDATORY WORKFLOW FOR COMPONENT GENERATION:
                    1. FIRST: Find the most relevant form using form searching MCP tools
                    2. ANALYZE: Use get_table_sample_data to understand the forms data structure through its secondary table
                    3. UNDERSTAND: Examine component generation MCP tools to see what SQL queries they need
                    4. GENERATE: Create SQL queries that match the required format
                    5. VALIDATE: Use execute_sql_query to test all queries and verify they return data
                    6. CHECK: Ensure data returned matches expected format
                    7. EXECUTE: Call component generation MCP tools with validated queries
                    
                    CRITICAL RULES FOR SQL QUERY GENERATION:
                    1. You work with key-value storage tables where:
                       - Always use the secondary table for looking at the form's sample data
                       - FIELD_NAME column contains field names (like 'age', 'name', 'email')
                       - FIELD_VALUE column contains the actual values of those fields
                       - Each row is one field-value pair for a record
                    
                    CRITICAL: SECONDARY TABLE STRUCTURE UNDERSTANDING
                    - Secondary tables use key-value storage with only 2 columns: FIELD_NAME and FIELD_VALUE
                    - FIELD_NAME contains the field names (like 'age', 'email', 'model_name')
                    - FIELD_VALUE contains the actual data values
                    - You CANNOT use field names as column names directly!
                    
                    WRONG: SELECT age FROM secondary_table
                    CORRECT: SELECT FIELD_VALUE FROM secondary_table WHERE FIELD_NAME = 'age'
                    
                    2. Always generate relevant SQL queries based on component generation MCP tool requirements
                    
                    3. Validate each SQL query using execute_sql_query tool before using it to generate components
                    
                    4. Handle NULL/empty values properly:
                       - Use CASE statements to convert NULL/empty to 'Unknown/Empty'
                       - Example: "CASE WHEN FIELD_VALUE IS NULL OR FIELD_VALUE = '' THEN 'Unknown/Empty' ELSE FIELD_VALUE END"
                    
                    6. Security: Only generate SELECT queries, never DROP, DELETE, INSERT, UPDATE, etc.
                    
                    Always find the relevant form name first, then analyze the form's sample data and then validate your SQL queries before creating components!"""
                }
            )
            
            print("✅ MCP Dashboard Agent initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize MCP agent: {str(e)}")
            if self.exit_stack:
                await self.exit_stack.__aexit__(None, None, None)
            return False

    async def generate_component_with_discovery(self, current_prompt: str, workspace_id: int, company_id: int, past_prompts: List[str] = None) -> str:
        """Let agent discover the relevant form using MCP tools and generate component with conversation context"""
        if not self.agent:
            return "❌ MCP agent not initialized"
        
        try:
            # Build conversation context if past prompts exist
            conversation_context = ""
            if past_prompts and len(past_prompts) > 0:
                conversation_context = "\n\nCONVERSATION CONTEXT:\n"
                conversation_context += "Recent user requests in this conversation:\n"
                for i, past_prompt in enumerate(reversed(past_prompts), 1):
                    conversation_context += f"{i}. {past_prompt}\n"
                conversation_context += f"\nCurrent request: {current_prompt}\n"
                conversation_context += "\nIMPORTANT: Use the conversation context to understand:\n"
                conversation_context += "- If current request is missing form name, infer it from past requests\n"
                conversation_context += "- If current request is missing data field context, add it from past requests\n"
                conversation_context += "- If current request only specifies chart type change, keep the same data analysis\n"
                conversation_context += "- Always preserve the user's specified chart type in the current request\n"
            
            prompt = f"""Find the most relevant form for this user query and create a visualization: {current_prompt}

WORKFLOW:
1. Use form search MCP tools to find the most relevant form for the query
2. Analyze the form's data structure using the get_table_sample_data mcp tool
3. Generate appropriate SQL queries for visualization
4. Validate each query using execute_sql_query mcp tool
5. Create the component using component generation MCP tools (charts, tables, metrics) using the validated SQL queries

CRITICAL: SECONDARY TABLE STRUCTURE UNDERSTANDING
- Secondary tables use key-value storage with only 2 columns: FIELD_NAME and FIELD_VALUE
- FIELD_NAME contains the field names (like 'age', 'email', 'model_name')
- FIELD_VALUE contains the actual data values
- You CANNOT use field names as column names directly!

WRONG: SELECT age FROM secondary_table
CORRECT: SELECT FIELD_VALUE FROM secondary_table WHERE FIELD_NAME = 'age'

{conversation_context}

USER QUERY: {current_prompt}

Start by searching for relevant forms using the form search tools."""

            print("🤖 Agent discovering form, analyzing structure and generating component...")
            
            # Track token usage from LLM calls
            import langchain
            from langchain.callbacks import get_openai_callback
            
            # Use callback to track token usage
            with get_openai_callback() as cb:
                result = await self.agent.ainvoke(prompt)
                
                # Update token usage counters
                self.total_prompt_tokens += cb.prompt_tokens
                self.total_completion_tokens += cb.completion_tokens
                self.total_tokens_used += cb.total_tokens
                
                print(f"📊 Token usage for this request: {cb.prompt_tokens} prompt + {cb.completion_tokens} completion = {cb.total_tokens} total")
                print(f"📊 Session total tokens: {self.total_tokens_used}")
            
            # Store token usage directly to database
            try:
                success, message = await self.store_token_usage_to_db(workspace_id, company_id)
                if success:
                    print(f"💾 Database storage: {message}")
                else:
                    print(f"⚠️ Database storage failed: {message}")
            except Exception as db_error:
                print(f"❌ Database storage error: {db_error}")
            
            if isinstance(result, dict) and "output" in result:
                return result["output"]
            else:
                return str(result)
                
        except Exception as e:
            return f"❌ Error in agent discovery and component generation: {str(e)}"
    
    async def cleanup(self):
        """Cleanup MCP resources"""
        if self.exit_stack:
            await self.exit_stack.__aexit__(None, None, None)

# Note: CLI functionality has been removed in Dashboard-Bot Version 4
# This module now only provides the DashboardAgent class
# for use by the API server. All interaction is now through REST API endpoints.

