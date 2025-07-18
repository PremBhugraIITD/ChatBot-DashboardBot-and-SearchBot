#!/usr/bin/env python3
"""
API Server for Dashboard Bot Version 4 (MCP-based Architecture)
================================================================

REST API endpoints for the new MCP-based dashboard component generator.
Uses the DashboardAgent with MCP tools for intelligent form discovery and component generation.

Features:
- MCP-based intelligent form discovery
- Agent-driven component generation  
- Support for charts, tables, and metrics
- Workspace-based security
- Authentication via session tokens
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import traceback
import asyncio
import os
import mysql.connector
from dotenv import load_dotenv
import httpx
from pymongo import MongoClient
from datetime import datetime
from typing import List
from openai import OpenAI
import uuid

# Load environment variables
load_dotenv(override=True)

# Set current directory for consistent file operations
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_sql_clauses(sql_query: str) -> dict:
    """
    Parse SQL query to extract WHERE, GROUP BY, and ORDER BY clauses
    
    Args:
        sql_query: Complete SQL query string
        
    Returns:
        dict: Contains 'where', 'group_by', 'order_by' clauses as strings or None
    """
    import re
    
    try:
        query = sql_query.strip()
        clauses = {
            'where': '',
            'group_by': '', 
            'order_by': ''
        }
        
        # Extract WHERE clause
        where_match = re.search(r'\bWHERE\s+(.*?)(?=\s*(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$))', query, re.IGNORECASE | re.DOTALL)
        if where_match:
            clauses['where'] = where_match.group(1).strip()
        
        # Extract GROUP BY clause
        group_by_match = re.search(r'\bGROUP\s+BY\s+(.*?)(?=\s*(?:ORDER\s+BY|LIMIT|$))', query, re.IGNORECASE | re.DOTALL)
        if group_by_match:
            clauses['group_by'] = group_by_match.group(1).strip()
        
        # Extract ORDER BY clause
        order_by_match = re.search(r'\bORDER\s+BY\s+(.*?)(?=\s*(?:LIMIT|$))', query, re.IGNORECASE | re.DOTALL)
        if order_by_match:
            clauses['order_by'] = order_by_match.group(1).strip()
        
        return clauses
        
    except Exception as e:
        logger.error(f"Error parsing SQL clauses: {str(e)}")
        return {'where': '', 'group_by': '', 'order_by': ''}

def test_database_connection():
    """Test database connection and return status"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            connection_timeout=5
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return True, "Database connection successful"
        
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"

def store_voice_analytics_to_mysql(sql_query: str, workspace_id: int, company_id: int, component_type: str, component_html: str) -> tuple:
    """
    Store voice analytics component in MySQL dashboard_templates table
    
    Args:
        sql_query: The SQL query used to generate the component
        workspace_id: Current workspace ID
        company_id: Current company ID
        component_type: Type of component (pie_chart, bar_graph, etc.)
        component_html: Generated HTML for the component
        
    Returns:
        tuple: (success: bool, message: str, template_id: int or None)
    """
    try:
        # Parse SQL query to extract clauses
        sql_clauses = parse_sql_clauses(sql_query)
        
        # Connect to MySQL database
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = connection.cursor()
        
        # Insert into dashboard_templates table
        insert_query = """
        INSERT INTO dashboard_templates 
        (SQL_QUERY, LIST_DATA, `WHERE`, GROUP_BY, ORDER_BY, WORKSPACE_ID, COMPANY_ID, 
         COMPONENT_TYPE, DASHBOARD_TYPE, COMPONENT_HTML, CREATED_AT, UPDATED_AT)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        
        # Prepare values (LIST_DATA kept empty as requested)
        values = (
            sql_query,                              # SQL_QUERY
            '',                                     # LIST_DATA (empty for now)
            sql_clauses.get('where', ''),           # WHERE
            sql_clauses.get('group_by', ''),        # GROUP_BY
            sql_clauses.get('order_by', ''),        # ORDER_BY
            workspace_id,                           # WORKSPACE_ID
            company_id,                             # COMPANY_ID
            component_type,                         # COMPONENT_TYPE
            2,                                      # DASHBOARD_TYPE (2 for voice analytics)
            component_html                          # COMPONENT_HTML
        )
        
        cursor.execute(insert_query, values)
        connection.commit()
        
        # Get the auto-generated ID
        template_id = cursor.lastrowid
        
        cursor.close()
        connection.close()
        
        logger.info(f"✅ Voice analytics component stored in MySQL with ID: {template_id}")
        return True, f"Component stored successfully with ID: {template_id}", template_id
        
    except Exception as e:
        error_msg = f"Failed to store voice analytics component in MySQL: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None

@app.route('/chat/forms/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Dashboard Bot Version 4
    
    Verifies:
    - API server is running
    - MySQL database connectivity
    - MongoDB connectivity
    - Environment variables are loaded
    - MCP components are available
    
    Returns:
    {
        "service": "Dashboard Bot Version 4 API",
        "status": "healthy|unhealthy",
        "version": "4.0.0",
        "timestamp": "2025-06-20T10:30:00Z",
        "database": {"status": "connected|failed", "message": "..."},
        "mongodb": {"status": "connected|failed", "message": "..."}
    }
    """
    try:
        from datetime import datetime
        
        # Initialize health check response
        health_response = {
            "service": "Dashboard Bot Version 4 API", 
            "status": "healthy",
            "version": "4.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database": {},
            "mongodb": {}
        }
        
        overall_healthy = True
        
        # Check database connection
        db_connected, db_message = test_database_connection()
        health_response["database"] = {
            "status": "connected" if db_connected else "failed",
            "message": db_message
        }
        if not db_connected:
            overall_healthy = False
        
        # Check MongoDB connection
        mongo_db, mongo_message = get_mongodb_connection()
        health_response["mongodb"] = {
            "status": "connected" if mongo_db is not None else "failed",
            "message": mongo_message
        }
        if mongo_db is None:
            overall_healthy = False
        
        # Check environment variables (simplified - no details in response)
        required_env_vars = ['OPENAI_API_KEY', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
        # MongoDB vars are optional since we support flexible connection
        mongodb_vars = ['MONGODB_URI', 'MONGODB_HOST', 'MONGODB_DB_NAME']
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        # Check if at least one MongoDB connection method is available
        mongodb_available = any(os.getenv(var) for var in mongodb_vars)
        
        if missing_vars:
            overall_healthy = False
        if not mongodb_available:
            overall_healthy = False
        
        # Check MCP components availability (simplified - no details in response)
        try:
            # Try to import the dashboard components
            from dashboard_client import DashboardAgent
            from dashboard_server import mcp  # This will verify MCP server can be imported
        except Exception as e:
            overall_healthy = False
        
        # Set overall status
        health_response["status"] = "healthy" if overall_healthy else "unhealthy"
        
        # Return appropriate HTTP status code
        status_code = 200 if overall_healthy else 503
        
        logger.info(f"Health check completed - Status: {health_response['status']}")
        return jsonify(health_response), status_code
        
    except Exception as e:
        from datetime import datetime
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "Dashboard Bot Version 4 API",
            "version": "4.0.0", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 503

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": [
            "/chat/forms/health",
            "/chat/forms/list",
            "/chat/forms/generate",
            "/chat/forms/refresh",
            "/chat/analytics/voice",
            "/chat/analytics/refresh"
        ],
        "message": "Check the endpoint URL and try again"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong processing your request"
    }), 500

async def verify_user_session_token(token: str):
    """
    Verify user session token for endpoints using UnleashX API
    """
    try:
        logger.info(f"User session token verification requested...")
        
        # Validate token presence
        if not token:
            raise ValueError("User session token is required")
        
        # Call UnleashX API to verify user session token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{os.getenv('UNLEASHX_URL')}/api/getuser",
                headers={
                    "token": token,
                    "Content-Type": "application/json"
                },
                json={}
            )
            
            # Check if the API call was successful
            if response.status_code != 200:
                logger.warning(f"User token verification failed: Status {response.status_code}")
                raise ValueError("Invalid or expired user session token")
            
            # Parse the response
            try:
                response_data = response.json()
                logger.info(f"User verification response received for user: {response_data.get('data', {}).get('loginname', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to parse user verification response: {e}")
                raise ValueError("Invalid response from authentication service")
            
            # Check if the response indicates success
            if response_data.get("error", True) or response_data.get("code") != 200:
                logger.warning(f"User token verification failed: {response_data.get('message', 'Unknown error')}")
                raise ValueError("Invalid or expired user session token")
            
            # Extract user data from response
            user_data = response_data.get("data", {})
            
            # Return structured user information
            return {
                "valid": True,
                "user_id": user_data.get("user_id"),
                "id": user_data.get("id"),
                "loginname": user_data.get("loginname"),
                "first_name": user_data.get("first_name"),
                "last_name": user_data.get("last_name"),
                "workspace_id": user_data.get("workspace_id"),
                "workspace_name": user_data.get("workspace_name"),
                "company_id": user_data.get("company_id"),
                "company_domain": user_data.get("company_domain"),
                "is_superadmin": user_data.get("is_superadmin", False),
                "country": user_data.get("country"),
                "language": user_data.get("language", "en"),
                "device": user_data.get("device"),
                "device_type": user_data.get("device_type"),
                "token_type": "user_session",
                "full_response": user_data
            }
        
    except ValueError:
        raise
    except httpx.RequestError as e:
        logger.error(f"Network error during user token verification: {e}")
        raise ValueError("Authentication service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error during user token verification: {e}")
        raise ValueError("Token verification service error")

def get_available_forms(workspace_id: int):
    """
    Get list of available forms for a specific workspace
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT ID, OBJECT_NAME, SECONDARY_TABLE 
        FROM form_objects 
        WHERE STATUS = 1 AND WORKSPACE_ID = %s
        ORDER BY OBJECT_NAME ASC
        """
        cursor.execute(query, (workspace_id,))
        forms = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return forms
        
    except Exception as e:
        logger.error(f"Error fetching forms for workspace {workspace_id}: {e}")
        raise Exception(f"Database error: {str(e)}")

@app.route('/chat/forms/list', methods=['GET'])
def list_forms():
    """
    List available forms for authenticated user's workspace
    
    Headers:
        token: User session token for authentication
    
    Returns:
    {
        "service": "Dashboard Bot Version 4 API",
        "success": true,
        "workspace_id": 98,
        "user": "aadityadubey@gmail.com", 
        "forms": [
            {
                "ID": 1,
                "OBJECT_NAME": "Form Name",
                "SECONDARY_TABLE": "table_name"
            }
        ],
        "count": 5,
        "timestamp": "2025-06-19T10:30:00Z"
    }
    """
    try:
        # Get token from headers
        token = request.headers.get('token') or request.headers.get('Token')
        
        if not token:
            return jsonify({
                "service": "Dashboard Bot Version 4 API",
                "success": False,
                "error": "Authentication token is required in headers"
            }), 401
        
        # Authenticate user token
        try:
            user_info = asyncio.run(verify_user_session_token(token))
        except ValueError as e:
            return jsonify({
                "service": "Dashboard Bot Version 4 API", 
                "success": False,
                "error": str(e)
            }), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                "service": "Dashboard Bot Version 4 API",
                "success": False,
                "error": "Authentication service error"
            }), 500
        
        # Extract workspace_id
        workspace_id = user_info.get('workspace_id')
        if not workspace_id:
            return jsonify({
                "service": "Dashboard Bot Version 4 API",
                "success": False,
                "error": "No workspace_id found for user"
            }), 400
        
        logger.info(f"🔍 Listing forms for user {user_info.get('loginname')} (workspace_id: {workspace_id})")
        
        # Get forms for the workspace
        try:
            forms = get_available_forms(workspace_id)
        except Exception as e:
            return jsonify({
                "service": "Dashboard Bot Version 4 API",
                "success": False,
                "error": str(e)
            }), 500
        
        # Return successful response
        from datetime import datetime
        return jsonify({
            "service": "Dashboard Bot Version 4 API",
            "success": True,
            "workspace_id": workspace_id,
            "user": user_info.get('loginname'),
            "forms": forms,
            "count": len(forms),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        logger.error(f"Error in list_forms endpoint: {e}")
        from datetime import datetime
        return jsonify({
            "service": "Dashboard Bot Version 4 API",
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

@app.route('/chat/forms/generate', methods=['POST'])
def generate_components():
    """
    Generate dashboard components using MCP agent for authenticated user's workspace
    
    Headers:
        token: User session token for authentication
    
    Request Body:
    {
        "prompt": "Show me a pie chart of customer distribution"
    }
    
    Returns:
    {
        "success": true,
        "user_prompt": "Show me a pie chart of customer distribution",
        "result": "HTML component generated by bot",
        "workspace_id": 98,
        "timestamp": "2025-06-19T10:30:00Z"
    }
    """
    try:
        from datetime import datetime
        
        # Get token from headers
        token = request.headers.get('token') or request.headers.get('Token')
        
        if not token:
            return jsonify({
                "success": False,
                "error": "Authentication token is required in headers"
            }), 401
        
        # Authenticate user token
        try:
            user_info = asyncio.run(verify_user_session_token(token))
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                "success": False,
                "error": "Authentication service error"
            }), 500
        
        # Extract workspace_id
        workspace_id = user_info.get('workspace_id')
        if not workspace_id:
            return jsonify({
                "success": False,
                "error": "No workspace_id found for user"
            }), 400
        
        # Get prompt from request body
        data = request.get_json()
        if not data or not data.get('prompt'):
            return jsonify({
                "success": False,
                "error": "Prompt is required in request body"
            }), 400
        
        user_prompt = data.get('prompt')
        # Model is now hardcoded in dashboard_client.py - no need to pass it
        logger.info(f"🚀 Processing prompt for workspace {workspace_id}: {user_prompt}")
        
        # Retrieve recent chat history for context (no LLM combination needed)
        try:
            past_prompts = get_recent_user_prompts(workspace_id, limit=3)
            
            if past_prompts:
                logger.info(f"📚 Retrieved {len(past_prompts)} past prompts for context")
                logger.debug(f"Current: {user_prompt}")
                logger.debug(f"Past prompts: {past_prompts}")
            else:
                logger.info(f"📚 No past prompts found for context")
                
        except Exception as e:
            logger.warning(f"Chat history retrieval failed, proceeding without context: {str(e)}")
            past_prompts = []
        
        # Write workspace_id to middle.json BEFORE MCP agent initialization (clear previous data)
        try:
            import json
            import time
            middle_json_path = os.path.join(CURRENT_DIR, "middle.json")
            # Clear middle.json and write only workspace_id
            middle_data = {"workspace_id": workspace_id}
            with open(middle_json_path, "w") as f:
                json.dump(middle_data, f)
            logger.info(f"📝 Workspace ID {workspace_id} written to middle.json (cleared previous data)")
        except Exception as e:
            logger.error(f"Failed to write workspace_id to middle.json: {e}")
            return jsonify({
                "success": False,
                "error": "Failed to initialize workspace context"
            }), 500

        # Initialize and run MCP Dashboard Agent with optimized polling
        try:
            from dashboard_client import DashboardAgent
            
            async def run_mcp_agent_with_polling():
                """Run MCP agent and poll for completion simultaneously"""
                import concurrent.futures
                import threading
                
                def poll_middle_json():
                    """Poll middle.json for component_html completion"""
                    import json
                    import time
                    
                    max_wait_time = 30  # Maximum 30 seconds timeout
                    poll_interval = 0.2  # Poll every 200ms
                    start_time = time.time()
                    
                    logger.info("🔍 Starting optimized polling for component completion...")
                    
                    while time.time() - start_time < max_wait_time:
                        try:
                            with open(middle_json_path, "r") as f:
                                middle_data = json.load(f)
                            
                            # Check if component_html is present and non-null
                            component_html = middle_data.get("component_html")
                            if component_html is not None and component_html != "" and component_html.strip():
                                elapsed_time = time.time() - start_time
                                logger.info(f"✅ Component completion detected in {elapsed_time:.2f}s - returning immediately!")
                                return middle_data, None
                            
                            # Also check for error conditions to exit early
                            error_msg = middle_data.get("error")
                            if error_msg is not None and error_msg.strip():
                                elapsed_time = time.time() - start_time
                                logger.info(f"⚠️ Error condition detected in {elapsed_time:.2f}s - returning with error")
                                return middle_data, None
                                
                        except (FileNotFoundError, json.JSONDecodeError) as e:
                            # File might be being written, continue polling
                            pass
                        
                        time.sleep(poll_interval)
                    
                    # Timeout reached
                    logger.warning(f"⏰ Polling timeout reached ({max_wait_time}s) - falling back to current middle.json state")
                    try:
                        with open(middle_json_path, "r") as f:
                            middle_data = json.load(f)
                        return middle_data, "Timeout: Component generation took longer than expected"
                    except Exception as e:
                        return {"form_id": None, "component_html": None, "error": f"Timeout and failed to read middle.json: {str(e)}"}, "Polling timeout"
                
                async def run_mcp_agent():
                    """Run the MCP agent normally"""
                    agent = DashboardAgent()
                    try:
                        # Model is now hardcoded in dashboard_client.py - no need to set it
                        
                        # Initialize MCP agent (workspace_id now read from middle.json)
                        initialized = await agent.initialize_mcp_agent()
                        
                        if not initialized:
                            return None, "Failed to initialize MCP agent"
                        
                        # Generate component using MCP agent - this will populate middle.json
                        # Now passing workspace_id and company_id for direct database storage
                        company_id = user_info.get("company_id", 1)  # Default to 1 if not found
                        await agent.generate_component_with_discovery(user_prompt, workspace_id, company_id, past_prompts)
                        
                        # Read the component data from middle.json (fallback)
                        import json
                        try:
                            with open(middle_json_path, "r") as f:
                                middle_data = json.load(f)
                            
                            return middle_data, None
                        except (FileNotFoundError, json.JSONDecodeError) as e:
                            return {"form_id": None, "component_html": None, "error": f"Failed to read middle.json: {str(e)}"}, None
                        
                    except Exception as e:
                        logger.error(f"MCP agent internal error: {e}")
                        return None, str(e)
                    finally:
                        # Cleanup agent resources
                        try:
                            await agent.cleanup()
                        except Exception as cleanup_error:
                            logger.warning(f"Cleanup warning: {cleanup_error}")
                
                # Run polling in a separate thread while MCP agent runs
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Start polling in background thread
                    polling_future = executor.submit(poll_middle_json)
                    
                    # Start MCP agent
                    mcp_task = asyncio.create_task(run_mcp_agent())
                    
                    # Wait for both polling and MCP agent, but prioritize MCP agent for token usage
                    done = False
                    polling_result = None
                    while not done:
                        # Check if polling found result
                        if polling_future.done() and polling_result is None:
                            polling_result, polling_error = polling_future.result()
                            logger.info("📊 Polling detected completion first!")
                            # Don't return yet - wait for MCP agent to get token usage
                        
                        # Check if MCP agent finished
                        if mcp_task.done():
                            mcp_result, mcp_error = await mcp_task
                            logger.info("🤖 MCP agent completed normally with token usage")
                            
                            # If we have MCP result, use it (includes token usage)
                            if mcp_result and not mcp_error:
                                return mcp_result, mcp_error
                            # If MCP failed but polling succeeded, use polling result
                            elif polling_result and not polling_error:
                                logger.warning("⚠️ MCP agent failed but polling succeeded - using polling result (no token usage)")
                                return polling_result, polling_error
                            else:
                                return mcp_result, mcp_error
                        
                        # Brief sleep to avoid busy waiting
                        await asyncio.sleep(0.1)
            
            # Run MCP agent with parallel polling
            result, error = asyncio.run(run_mcp_agent_with_polling())
            
            if error or result is None:
                return jsonify({
                    "success": False,
                    "error": error or "No result returned from MCP agent"
                }), 500

            # 🧹 CRITICAL: Clear middle.json immediately after reading to prevent cross-request contamination
            try:
                with open(middle_json_path, "w") as f:
                    json.dump({}, f)  # Clear the file completely
                logger.info("🧹 middle.json cleared after reading component data")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clear middle.json: {cleanup_error}")

            # Extract data from middle.json result
            form_id = result.get("form_id")
            component_html = result.get("component_html") 
            error_msg = result.get("error")
            component_type = result.get("component_type")
            sql_used = result.get("sql_used")  # Extract the SQL query used
            
            # Extract x_name and y_name only if they exist (for bar_graph and line_chart)
            x_name = result.get("x_name")  # Will be None if not present
            y_name = result.get("y_name")  # Will be None if not present
            
            # Generate unique component ID
            component_id = str(uuid.uuid4())
            
            # Prepare bot response for MongoDB storage (conditionally includes x_name, y_name)
            bot_response = {
                "component_id": component_id,
                "form_id": form_id,
                "component_html": component_html,
                "error": error_msg,
                "component_type": component_type,
                "sql_used": sql_used
            }
            
            # Add x_name and y_name only if they exist in the result
            if x_name is not None:
                bot_response["x_name"] = x_name
            if y_name is not None:
                bot_response["y_name"] = y_name
            
            # Get client information for MongoDB storage
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))
            user_agent = request.headers.get('User-Agent', 'Unknown')
            
            # Store chat history in MongoDB
            try:
                store_success, store_message = store_chat_history(
                    user_prompt=user_prompt,
                    bot_response=bot_response,
                    workspace_id=workspace_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                if store_success:
                    logger.info(f"💾 Chat history stored: {store_message}")
                else:
                    logger.warning(f"⚠️ Failed to store chat history: {store_message}")
            except Exception as mongo_error:
                logger.error(f"❌ MongoDB storage error: {mongo_error}")
            
            # Token usage is now handled directly in dashboard_client.py
            # No need to track it here anymore
            
            # Return response with middle.json data
            response_data = {
                "success": True,
                "user_prompt": user_prompt,
                "workspace_id": workspace_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "component_id": component_id,
                "form_id": form_id,
                "component_html": component_html,
                "error": error_msg,
                "component_type": component_type
            }
            
            # Add x_name and y_name only if they exist in the result
            if x_name is not None:
                response_data["x_name"] = x_name
            if y_name is not None:
                response_data["y_name"] = y_name
            
            # Set success to false if there's an error
            if error_msg:
                response_data["success"] = False
            
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"MCP agent error: {e}")
            return jsonify({
                "success": False,
                "error": f"Component generation failed: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.error(f"Error in generate_components endpoint: {e}")
        from datetime import datetime
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

@app.route('/chat/forms/refresh', methods=['POST'])
def refresh_component():
    """
    Refresh an existing dashboard component with latest data using stored SQL query
    
    Headers:
        token: User session token for authentication
    
    Request Body:
    {
        "component_id": "uuid-string-of-existing-component"
    }
    
    Returns:
    {
        "success": true,
        "component_id": "original-uuid-123",
        "component_html": "Refreshed HTML with latest data",
        "component_type": "pie_chart",
        "form_id": 123,
        "error": null,
        "x_name": "Categories",  // Only for bar_graph/line_chart
        "y_name": "Count"        // Only for bar_graph/line_chart
    }
    """
    try:
        from datetime import datetime
        
        # Get token from headers
        token = request.headers.get('token') or request.headers.get('Token')
        
        if not token:
            return jsonify({
                "success": False,
                "error": "Authentication token is required in headers"
            }), 401
        
        # Authenticate user token
        try:
            user_info = asyncio.run(verify_user_session_token(token))
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                "success": False,
                "error": "Authentication service error"
            }), 500
        
        # Extract workspace_id
        workspace_id = user_info.get('workspace_id')
        if not workspace_id:
            return jsonify({
                "success": False,
                "error": "No workspace_id found for user"
            }), 400
        
        # Get component_id from request body
        data = request.get_json()
        if not data or not data.get('component_id'):
            return jsonify({
                "success": False,
                "error": "component_id is required in request body"
            }), 400
        
        component_id = data.get('component_id')
        logger.info(f"🔄 Refreshing component {component_id} for workspace {workspace_id}")
        
        # Search MongoDB for the component
        try:
            db, connection_msg = get_mongodb_connection()
            if db is None:
                logger.error(f"Failed to connect to MongoDB: {connection_msg}")
                return jsonify({
                    "success": False,
                    "error": "Database connection failed"
                }), 500
            
            # Find document with matching component_id in bot_response
            collection = db["dashboard_bot_chat_history"]
            document = collection.find_one({
                "bot_response.component_id": component_id,
                "workspace_id": workspace_id  # Ensure user can only refresh their own components
            })
            
            if not document:
                return jsonify({
                    "success": False,
                    "error": "Component not found or access denied"
                }), 404
            
            # Extract required data from bot_response
            bot_response = document["bot_response"]
            sql_used = bot_response.get("sql_used")
            component_type = bot_response.get("component_type")
            form_id = bot_response.get("form_id")
            x_name = bot_response.get("x_name")
            y_name = bot_response.get("y_name")
            
            if not sql_used or not component_type or not form_id:
                return jsonify({
                    "success": False,
                    "error": "Incomplete component data found"
                }), 400
            
            logger.info(f"📊 Refreshing {component_type} component with SQL: {sql_used[:50]}...")
            
        except Exception as e:
            logger.error(f"MongoDB lookup error: {e}")
            return jsonify({
                "success": False,
                "error": "Database lookup failed"
            }), 500
        
        # Import dashboard server functions for direct calls
        try:
            from dashboard_server import (
                generate_pie_chart_component,
                generate_bar_graph_component,
                generate_line_chart_component,
                generate_table_component,
                generate_metric_component
            )
            
            # Call appropriate function based on component_type
            if component_type == "pie_chart":
                result = generate_pie_chart_component(sql_used, form_id)
            elif component_type == "bar_graph":
                if not x_name or not y_name:
                    return jsonify({
                        "success": False,
                        "error": "Missing x_name or y_name for bar graph component"
                    }), 400
                result = generate_bar_graph_component(sql_used, x_name, y_name, form_id)
            elif component_type == "line_chart":
                if not x_name or not y_name:
                    return jsonify({
                        "success": False,
                        "error": "Missing x_name or y_name for line chart component"
                    }), 400
                result = generate_line_chart_component(sql_used, x_name, y_name, form_id)
            elif component_type == "table":
                result = generate_table_component(sql_used, form_id)
            elif component_type == "metric":
                result = generate_metric_component(sql_used, form_id)
            else:
                return jsonify({
                    "success": False,
                    "error": f"Unknown component type: {component_type}"
                }), 400
            
            # Check if result contains an error (functions return error strings when they fail)
            if result and result.startswith("<p>❌ Error:") or result.startswith("<div><p>❌ Error:"):
                # Function returned an error
                response_data = {
                    "success": False,
                    "component_id": component_id,
                    "component_html": None,
                    "component_type": component_type,
                    "form_id": form_id,
                    "error": result
                }
            else:
                # Function succeeded
                response_data = {
                    "success": True,
                    "component_id": component_id,  # Keep original component_id
                    "component_html": result,
                    "component_type": component_type,
                    "form_id": form_id,
                    "error": None
                }
            
            # Add x_name and y_name only if they exist (for bar_graph and line_chart)
            if x_name is not None:
                response_data["x_name"] = x_name
            if y_name is not None:
                response_data["y_name"] = y_name
            
            logger.info(f"✅ Component {component_id} refreshed successfully")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Component refresh error: {e}")
            return jsonify({
                "success": False,
                "error": f"Component refresh failed: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.error(f"Error in refresh_component endpoint: {e}")
        from datetime import datetime
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

@app.route('/chat/analytics/voice', methods=['POST'])
def generate_voice_analytics():
    """
    Generate voice analytics components using MCP agent for authenticated user's workspace
    
    Headers:
        token: User session token for authentication
    
    Request Body:
    {
        "prompt": "Show me call duration distribution for agents"
    }
    
    Returns:
    {
        "success": true,
        "user_prompt": "Show me call duration distribution for agents",
        "result": "HTML component generated by voice analytics bot",
        "workspace_id": 98,
        "timestamp": "2025-06-19T10:30:00Z",
        "component_type": "pie_chart",
        "sql_used": "SELECT AGENT_ID, AVG(TOTAL_DURATION) FROM agent_executions WHERE WORKSPACE_ID = 98 GROUP BY AGENT_ID"
    }
    """
    try:
        from datetime import datetime
        
        # Get token from headers
        token = request.headers.get('token') or request.headers.get('Token')
        
        if not token:
            return jsonify({
                "success": False,
                "error": "Authentication token is required in headers"
            }), 401
        
        # Authenticate user token
        try:
            user_info = asyncio.run(verify_user_session_token(token))
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                "success": False,
                "error": "Authentication service error"
            }), 500
        
        # Extract workspace_id
        workspace_id = user_info.get('workspace_id')
        if not workspace_id:
            return jsonify({
                "success": False,
                "error": "No workspace_id found for user"
            }), 400
        
        # Get prompt from request body
        data = request.get_json()
        if not data or not data.get('prompt'):
            return jsonify({
                "success": False,
                "error": "Prompt is required in request body"
            }), 400
        
        user_prompt = data.get('prompt')
        logger.info(f"🎙️ Processing voice analytics prompt for user {user_info.get('loginname')} (workspace_id: {workspace_id}): {user_prompt}")
        
        # Write workspace_id to middle.json BEFORE MCP agent initialization (clear previous data)
        try:
            import json
            import time
            middle_json_path = os.path.join(CURRENT_DIR, "middle.json")
            # Clear middle.json and write only workspace_id
            middle_data = {"workspace_id": workspace_id}
            with open(middle_json_path, "w") as f:
                json.dump(middle_data, f)
            logger.info(f"📝 Workspace ID {workspace_id} written to middle.json for voice analytics")
        except Exception as e:
            logger.error(f"Failed to write workspace_id to middle.json: {e}")
            return jsonify({
                "success": False,
                "error": "Failed to initialize workspace context"
            }), 500

        # Initialize and run Voice Analytics MCP Agent
        try:
            from voice_analytics_client import VoiceAnalyticsAgent
            
            async def run_voice_analytics_agent():
                """Run Voice Analytics MCP agent"""
                agent = VoiceAnalyticsAgent()
                try:
                    # Initialize MCP agent (workspace_id now read from middle.json)
                    initialized = await agent.initialize_mcp_agent()
                    
                    if not initialized:
                        return None, "Failed to initialize Voice Analytics MCP agent"
                    
                    # Generate analytics component using MCP agent - this will populate middle.json
                    company_id = 1  # Default company_id since no authentication
                    await agent.generate_analytics_component(user_prompt, workspace_id, company_id)
                    
                    # Read the component data from middle.json
                    import json
                    try:
                        with open(middle_json_path, "r") as f:
                            middle_data = json.load(f)
                        
                        return middle_data, None
                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        return {"component_html": None, "error": f"Failed to read middle.json: {str(e)}"}, None
                    
                except Exception as e:
                    logger.error(f"Voice Analytics MCP agent internal error: {e}")
                    return None, str(e)
                finally:
                    # Cleanup agent resources
                    try:
                        await agent.cleanup()
                    except Exception as cleanup_error:
                        logger.warning(f"Cleanup warning: {cleanup_error}")
            
            # Run Voice Analytics agent
            result, error = asyncio.run(run_voice_analytics_agent())
            
            if error or result is None:
                return jsonify({
                    "success": False,
                    "error": error or "No result returned from voice analytics agent"
                }), 500

            # At this point, result is guaranteed to be not None
            assert result is not None

            # 🧹 CRITICAL: Clear middle.json immediately after reading to prevent cross-request contamination
            try:
                with open(middle_json_path, "w") as f:
                    json.dump({}, f)  # Clear the file completely
                logger.info("🧹 middle.json cleared after reading voice analytics component data")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clear middle.json: {cleanup_error}")

            # Extract data from middle.json result
            component_html = result.get("component_html") 
            error_msg = result.get("error")
            component_type = result.get("component_type")
            sql_used = result.get("sql_used")  # Extract the SQL query used
            
            # Extract x_name and y_name only if they exist (for bar_graph and line_chart)
            x_name = result.get("x_name")  # Will be None if not present
            y_name = result.get("y_name")  # Will be None if not present
            
            # Store voice analytics component in MySQL dashboard_templates table
            template_id = None
            company_id = user_info.get("company_id", 1)  # Default to 1 if not found
            if component_html and not error_msg and sql_used and component_type:
                try:
                    success, message, template_id = store_voice_analytics_to_mysql(
                        sql_query=sql_used,
                        workspace_id=workspace_id,
                        company_id=company_id,
                        component_type=component_type,
                        component_html=component_html
                    )
                    if success:
                        logger.info(f"💾 Voice analytics component stored in MySQL: {message}")
                    else:
                        logger.warning(f"⚠️ Failed to store voice analytics component in MySQL: {message}")
                except Exception as mysql_error:
                    logger.error(f"❌ MySQL storage error: {mysql_error}")
            
            # Token usage is printed to terminal in voice_analytics_client.py
            # No need to track it here
            
            # Return response with middle.json data (without component_id, using template_id if needed)
            response_data = {
                "success": True,
                "user_prompt": user_prompt,
                "workspace_id": workspace_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "component_id": template_id,  # MySQL auto-increment ID as component_id
                "component_html": component_html,
                "error": error_msg,
                "component_type": component_type,
                "sql_used": sql_used,
                "analytics_type": "voice"
            }
            
            # Add template_id if component was successfully stored (keeping for backwards compatibility)
            if template_id is not None:
                response_data["template_id"] = template_id
            
            # Add x_name and y_name only if they exist in the result
            if x_name is not None:
                response_data["x_name"] = x_name
            if y_name is not None:
                response_data["y_name"] = y_name
            
            # Set success to false if there's an error
            if error_msg:
                response_data["success"] = False
            
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Voice Analytics MCP agent error: {e}")
            return jsonify({
                "success": False,
                "error": f"Voice analytics component generation failed: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.error(f"Error in generate_voice_analytics endpoint: {e}")
        from datetime import datetime
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

def modify_sql_with_conditions(original_sql: str, conditions: dict, workspace_id: int) -> str:
    """
    Modify SQL query by applying user conditions to WHERE, GROUP BY, and ORDER BY clauses
    Always adds WORKSPACE_ID and ACTION_TYPE = 'calling' to WHERE clause for voice analytics bot.
    
    SAFE APPROACH: For complex SQL with subqueries, use string replacement instead of regex parsing.
    """
    import re
    
    try:
        sql = original_sql.strip()
        logger.info(f"🔍 Original SQL: {sql}")
        
        # Check if SQL contains actual subqueries (not just CASE WHEN expressions)
        # Look for SELECT statements inside parentheses, excluding the main SELECT
        has_actual_subquery = False
        if '(' in sql:
            # Find all SELECT occurrences after parentheses
            sql_upper = sql.upper()
            paren_positions = [i for i, char in enumerate(sql) if char == '(']
            for paren_pos in paren_positions:
                # Look for SELECT after this opening parenthesis
                remaining_after_paren = sql_upper[paren_pos:]
                if 'SELECT' in remaining_after_paren:
                    # Check if this SELECT is not just part of a column name or function
                    select_pos = remaining_after_paren.find('SELECT')
                    # Ensure it's a word boundary (actual SELECT statement)
                    if select_pos > 0:
                        char_before = remaining_after_paren[select_pos - 1]
                        if char_before in ' \t\n\r(':
                            has_actual_subquery = True
                            break
        
        logger.info(f"🔍 Subquery detection: has_parentheses={('(' in sql)}, has_actual_subquery={has_actual_subquery}")
        
        if has_actual_subquery:
            logger.info(f"🔍 Detected actual subquery - using safe string replacement approach")
            return modify_sql_with_string_replacement(sql, conditions, workspace_id)
        
        # For simple SQL without subqueries, use the original regex approach
        logger.info(f"🔍 Simple SQL detected - using regex parsing approach")
        
        select_match = re.search(r'^(SELECT\s+.*?\s+FROM\s+\w+)', sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            raise ValueError("Could not parse SELECT clause from SQL")
        select_part = select_match.group(1)
        remaining_sql = sql[select_match.end():].strip()
        
        logger.info(f"🔍 SELECT part: '{select_part}'")
        logger.info(f"🔍 Remaining SQL: '{remaining_sql}'")
        
        # Parse WHERE clause - fixed regex to handle end of string properly  
        where_match = re.search(r'WHERE\s+(.*?)(?=\s*(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$))', remaining_sql, re.IGNORECASE | re.DOTALL)
        existing_where = where_match.group(1).strip() if where_match else ""
        logger.info(f"🔍 WHERE regex match: {where_match is not None}")
        if where_match:
            logger.info(f"🔍 WHERE match groups: {where_match.groups()}")
        logger.info(f"🔍 Existing WHERE clause: '{existing_where}'")
        
        # Also check what the full remaining SQL looks like for GROUP BY/ORDER BY parsing
        logger.info(f"🔍 Full remaining SQL for clause parsing: '{remaining_sql}'")
        
        # Parse GROUP BY clause - search in remaining SQL with flexible whitespace
        group_by_match = re.search(r'GROUP\s+BY\s+(.*?)(?=\s*(?:ORDER\s+BY|LIMIT|$))', remaining_sql, re.IGNORECASE | re.DOTALL)
        existing_group_by = group_by_match.group(1).strip() if group_by_match else ""
        
        # Parse ORDER BY clause - search in remaining SQL with flexible whitespace  
        order_by_match = re.search(r'ORDER\s+BY\s+(.*?)(?=\s*(?:LIMIT|$))', remaining_sql, re.IGNORECASE | re.DOTALL)
        existing_order_by = order_by_match.group(1).strip() if order_by_match else ""
        limit_match = re.search(r'LIMIT\s+\d+', remaining_sql, re.IGNORECASE)
        existing_limit = limit_match.group(0) if limit_match else ""
        
        # Build new WHERE clause following merge rules
        new_where_parts = []
        
        # Always ensure security filtering (these are always required)
        new_where_parts.append(f"WORKSPACE_ID = {workspace_id}")
        new_where_parts.append(f"ACTION_TYPE = 'calling'")
        
        # Parse existing WHERE conditions from original SQL (excluding security filters)
        existing_conditions = {}
        if existing_where:
            # Split by AND to get individual conditions - handle extra spaces
            where_parts = [part.strip() for part in re.split(r'\s+AND\s+', existing_where, flags=re.IGNORECASE)]
            logger.info(f"🔍 WHERE parts: {where_parts}")
            
            for part in where_parts:
                part = part.strip()
                # Skip security filters (they're handled separately) - be more precise
                part_upper = part.upper()
                is_workspace_filter = part_upper.startswith('WORKSPACE_ID') and '=' in part_upper
                is_action_filter = part_upper.startswith('ACTION_TYPE') and '=' in part_upper
                
                if is_workspace_filter or is_action_filter:
                    logger.info(f"🔍 Skipping security filter: {part}")
                    continue
                    
                # Parse condition - handle both equals and non-equals conditions
                if ' = ' in part:
                    # Handle standard equals conditions
                    column, value = part.split(' = ', 1)
                    column = column.strip()
                    value = value.strip()
                    
                    # Preserve original quotes for string values
                    if value.startswith("'") and value.endswith("'"):
                        # String value with single quotes
                        existing_conditions[column] = value[1:-1]  # Remove quotes for storage
                    elif value.startswith('"') and value.endswith('"'):
                        # String value with double quotes  
                        existing_conditions[column] = value[1:-1]  # Remove quotes for storage
                    else:
                        # Numeric or unquoted value
                        existing_conditions[column] = value
                        
                    logger.info(f"🔍 Parsed equals condition: {column} = {existing_conditions[column]}")
                else:
                    # Handle non-equals conditions (IS NOT NULL, !=, >, <, LIKE, etc.)
                    # Store the complete condition as-is with a unique key
                    condition_key = f"_condition_{len(existing_conditions)}"
                    existing_conditions[condition_key] = part
                    logger.info(f"🔍 Preserved non-equals condition: {part}")
        
        logger.info(f"🔍 Existing conditions: {existing_conditions}")
        
        # Get API WHERE conditions
        api_conditions = conditions.get('where', {})
        logger.info(f"🔍 API conditions: {api_conditions}")
        
        # Merge conditions: Start with existing, then update/add from API
        merged_conditions = existing_conditions.copy()
        if api_conditions:
            for column, value in api_conditions.items():
                merged_conditions[column] = value  # This updates existing or adds new
        
        logger.info(f"🔍 Merged conditions: {merged_conditions}")
        
        # Add merged conditions to WHERE clause
        for column, value in merged_conditions.items():
            if column.startswith("_condition_"):
                # This is a preserved non-equals condition - add as-is
                new_where_parts.append(str(value))
                logger.info(f"🔍 Added preserved condition: {value}")
            elif isinstance(value, str):
                new_where_parts.append(f"{column} = '{value}'")
            elif isinstance(value, (int, float)):
                new_where_parts.append(f"{column} = {value}")
            else:
                new_where_parts.append(f"{column} = '{str(value)}'")
        
        # Only override GROUP BY if explicitly provided in conditions
        if 'group_by' in conditions and conditions['group_by'] is not None:
            new_group_by = conditions['group_by']
            if isinstance(new_group_by, list):
                new_group_by = ", ".join(new_group_by)
        else:
            new_group_by = existing_group_by
        
        # Only override ORDER BY if explicitly provided in conditions
        if 'order_by' in conditions and conditions['order_by'] is not None:
            new_order_by = conditions['order_by']
            if isinstance(new_order_by, list):
                new_order_by = ", ".join(new_order_by)
        else:
            new_order_by = existing_order_by
            
        final_sql_parts = [select_part]
        if new_where_parts:
            final_sql_parts.append(f"WHERE {' AND '.join(new_where_parts)}")
        if new_group_by:
            final_sql_parts.append(f"GROUP BY {new_group_by}")
        if new_order_by:
            final_sql_parts.append(f"ORDER BY {new_order_by}")
        if existing_limit:
            final_sql_parts.append(existing_limit)
            
        final_sql = " ".join(final_sql_parts)
        logger.info(f"✅ Modified SQL: {final_sql}")
        return final_sql
    except Exception as e:
        logger.error(f"❌ Error modifying SQL: {str(e)}")
        raise ValueError(f"Failed to modify SQL query: {str(e)}")

def modify_sql_with_string_replacement(original_sql: str, conditions: dict, workspace_id: int) -> str:
    """
    SAFE approach for complex SQL with subqueries - use string replacement instead of regex parsing
    """
    import re
    
    try:
        sql = original_sql.strip()
        logger.info(f"🔧 Using string replacement approach for complex SQL")
        
        # Step 1: Update workspace_id (replace old workspace_id with new one)
        # Find current workspace_id in the main WHERE clause (not subqueries)
        workspace_pattern = r'WORKSPACE_ID\s*=\s*\d+'
        sql = re.sub(workspace_pattern, f'WORKSPACE_ID = {workspace_id}', sql)
        
        # Step 2: Get API conditions
        api_conditions = conditions.get('where', {})
        if not api_conditions:
            logger.info(f"🔧 No API conditions to apply - only updated workspace_id")
            return sql
        
        # Step 3: Find the main WHERE clause (not in subqueries)
        # Look for the first WHERE that's not inside parentheses
        where_positions = []
        paren_depth = 0
        sql_upper = sql.upper()
        
        for i, char in enumerate(sql):
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif paren_depth == 0 and sql_upper[i:i+5] == 'WHERE':
                where_positions.append(i)
        
        if not where_positions:
            logger.warning(f"⚠️ No main WHERE clause found - cannot apply conditions")
            return sql
        
        main_where_pos = where_positions[0]
        
        # Step 4: Find the end of the main WHERE clause
        # Look for GROUP BY, ORDER BY, or end of string (not in subqueries)
        where_end_pos = len(sql)
        paren_depth = 0
        for i in range(main_where_pos + 5, len(sql)):
            if sql[i] == '(':
                paren_depth += 1
            elif sql[i] == ')':
                paren_depth -= 1
            elif paren_depth == 0:
                # Check for GROUP BY or ORDER BY
                if sql_upper[i:i+8] == 'GROUP BY' or sql_upper[i:i+8] == 'ORDER BY':
                    where_end_pos = i
                    break
        
        # Step 5: Extract the main WHERE clause
        where_clause = sql[main_where_pos + 5:where_end_pos].strip()
        logger.info(f"🔧 Extracted main WHERE clause: '{where_clause}'")
        logger.info(f"🔧 WHERE clause positions: start={main_where_pos + 5}, end={where_end_pos}")
        
        # Step 6: Add API conditions to the WHERE clause
        new_conditions = []
        for column, value in api_conditions.items():
            if isinstance(value, str):
                new_conditions.append(f"{column} = '{value}'")
            elif isinstance(value, (int, float)):
                new_conditions.append(f"{column} = {value}")
            else:
                new_conditions.append(f"{column} = '{str(value)}'")
        
        if new_conditions:
            # Add new conditions to existing WHERE clause
            updated_where = where_clause + ' AND ' + ' AND '.join(new_conditions)
            # Replace the WHERE clause in the original SQL
            new_sql = sql[:main_where_pos + 5] + ' ' + updated_where + ' ' + sql[where_end_pos:]
            logger.info(f"🔧 Applied API conditions: {api_conditions}")
        else:
            new_sql = sql
        
        logger.info(f"✅ Safe modified SQL: {new_sql}")
        return new_sql
        
    except Exception as e:
        logger.error(f"❌ Error in safe SQL modification: {str(e)}")
        # Fallback: return original SQL with just workspace_id updated
        workspace_pattern = r'WORKSPACE_ID\s*=\s*\d+'
        fallback_sql = re.sub(workspace_pattern, f'WORKSPACE_ID = {workspace_id}', original_sql)
        logger.warning(f"⚠️ Falling back to minimal modification")
        return fallback_sql

@app.route('/chat/analytics/refresh', methods=['POST'])
def refresh_analytics_component():
    """
    Refresh voice analytics component with latest data or modified conditions
    
    Headers:
        token: User session token for authentication
    
    Request Body:
    {
        "component_id": "uuid-string-of-existing-component",
        "conditions": {
            "where": {"AGENT_ID": 103, "STATUS": "completed"},
            "group_by": "ACTION_TYPE",
            "order_by": "CREATED_AT DESC"
        }
    }
    
    If conditions is empty, functions like /chat/forms/refresh (re-execute same SQL).
    If conditions provided, modifies WHERE, GROUP BY, ORDER BY clauses of original SQL.
    
    Returns:
    {
        "success": true,
        "component_id": "original-uuid-123",
        "component_html": "Refreshed HTML with latest data",
        "component_type": "pie_chart",
        "sql_used": "Modified SQL query",
        "analytics_type": "voice_refresh"
    }
    """
    try:
        from datetime import datetime
        import re
        
        # Get token from headers
        token = request.headers.get('token') or request.headers.get('Token')
        
        if not token:
            return jsonify({
                "success": False,
                "error": "Authentication token is required in headers"
            }), 401
        
        # Authenticate user token
        try:
            user_info = asyncio.run(verify_user_session_token(token))
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                "success": False,
                "error": "Authentication service error"
            }), 500
        
        # Extract workspace_id
        workspace_id = user_info.get('workspace_id')
        if not workspace_id:
            return jsonify({
                "success": False,
                "error": "No workspace_id found for user"
            }), 400
        
        # Get component_id and conditions from request body
        data = request.get_json()
        if not data or not data.get('component_id'):
            return jsonify({
                "success": False,
                "error": "component_id is required in request body"
            }), 400
        
        component_id = data.get('component_id')
        conditions = data.get('conditions', {})
        
        logger.info(f"🔄 Refreshing analytics component {component_id} for user {user_info.get('loginname')} (workspace_id: {workspace_id})")
        if conditions:
            logger.info(f"📝 With conditions: {conditions}")
        
        # Search MySQL dashboard_templates for the component
        try:
            import os
            import mysql.connector
            # Connect to MySQL database
            connection = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST'),
                user=os.getenv('MYSQL_USER'),
                password=os.getenv('MYSQL_PASSWORD'),
                database=os.getenv('MYSQL_DATABASE')
            )
            
            cursor = connection.cursor(dictionary=True)
            
            # Find component by ID (treating component_id as template_id)
            query = """
            SELECT SQL_QUERY, COMPONENT_TYPE, WORKSPACE_ID ,X_NAME, Y_NAME, UNIT, METRIC_LABEL
            FROM dashboard_templates 
            WHERE ID = %s AND DASHBOARD_TYPE = 2
            """
            cursor.execute(query, (component_id,))
            document = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if not document:
                return jsonify({
                    "success": False,
                    "error": "Analytics component not found or access denied"
                }), 404
            
            # Verify workspace access
            # if document.get("WORKSPACE_ID") != workspace_id:
            #     return jsonify({
            #         "success": False,
            #         "error": "Access denied: component belongs to different workspace"
            #     }), 403
            
            # Extract required data from document
            original_sql = document.get("SQL_QUERY")
            component_type = document.get("COMPONENT_TYPE")
            x_name = document.get("X_NAME")
            y_name = document.get("Y_NAME")
            unit = document.get("UNIT")
            metric_label = document.get("METRIC_LABEL")
            
            if not original_sql or not component_type:
                return jsonify({
                    "success": False,
                    "error": "Incomplete component data found"
                }), 400
            
            logger.info(f"📊 Original SQL: {original_sql}")
            
        except Exception as e:
            logger.error(f"MySQL lookup error: {e}")
            return jsonify({
                "success": False,
                "error": "Database lookup failed"
            }), 500
        
        # Determine final SQL query
        if not conditions or not any(conditions.values()):
            # Mode 1: No conditions - use original SQL (like /chat/forms/refresh)
            final_sql = original_sql
            logger.info(f"🔄 Mode 1: Re-executing original SQL")
        else:
            # Mode 2: Apply conditions to modify SQL
            try:
                final_sql = modify_sql_with_conditions(original_sql, conditions, workspace_id)
                logger.info(f"🔧 Mode 2: Modified SQL: {final_sql}")
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Failed to modify SQL query: {str(e)}"
                }), 400
        
        # Write workspace_id to middle.json before calling voice analytics server functions
        try:
            import json
            import os
            import sys
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            middle_json_path = os.path.join(current_dir, "middle.json")
            
            # Write workspace_id to middle.json so voice analytics server can read it
            middle_data = {"workspace_id": workspace_id}
            with open(middle_json_path, "w") as f:
                json.dump(middle_data, f)
            logger.info(f"📝 Workspace ID {workspace_id} written to middle.json for voice analytics server")
            
        except Exception as e:
            logger.error(f"Failed to write workspace_id to middle.json: {e}")
            return jsonify({
                "success": False,
                "error": "Failed to initialize workspace context for voice analytics server"
            }), 500

        # Generate component using appropriate function from voice_analytics_server
        try:
            # Add current directory to Python path to import voice_analytics_server functions
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            # Import the component generation functions
            if component_type == "pie_chart":
                from voice_analytics_server import generate_pie_chart_component
                result = generate_pie_chart_component(final_sql)
            elif component_type == "bar_graph":
                if not x_name or not y_name:
                    return jsonify({
                        "success": False,
                        "error": "Missing x_name or y_name for bar graph component"
                    }), 400
                from voice_analytics_server import generate_bar_graph_component
                result = generate_bar_graph_component(final_sql, x_name, y_name)
            elif component_type == "line_chart":
                if not x_name or not y_name:
                    return jsonify({
                        "success": False,
                        "error": "Missing x_name or y_name for line chart component"
                    }), 400
                from voice_analytics_server import generate_line_chart_component
                result = generate_line_chart_component(final_sql, x_name, y_name)
            elif component_type == "table":
                from voice_analytics_server import generate_table_component
                result = generate_table_component(final_sql)
            elif component_type == "metric":
                if not unit or not metric_label:
                    return jsonify({
                        "success": False,
                        "error": "Missing unit or metric_label for metric component"
                    }), 400
                from voice_analytics_server import generate_metric_component
                result = generate_metric_component(final_sql, unit, metric_label)
            else:
                return jsonify({
                    "success": False,
                    "error": f"Unknown component type: {component_type}"
                }), 400
            
            # Check if result contains an error (functions return error strings when they fail)
            if result and (result.startswith("<p>❌ Error:") or result.startswith("<div><p>❌ Error:")):
                # Function returned an error
                response_data = {
                    "success": False,
                    "component_id": component_id,
                    "component_html": None,
                    "component_type": component_type,
                    "sql_used": final_sql,
                    "analytics_type": "voice_refresh",
                    "error": result,
                    "workspace_id": workspace_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            else:
                # Function succeeded
                response_data = {
                    "success": True,
                    "component_id": component_id,  # Keep original component_id
                    "component_html": result,
                    "component_type": component_type,
                    "sql_used": final_sql,
                    "analytics_type": "voice_refresh",
                    "error": None,
                    "workspace_id": workspace_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "user_prompt": f"Refresh component with conditions: {conditions}" if conditions else "Refresh component with latest data"
                }
            
            # Add x_name and y_name only if they exist (for bar_graph and line_chart)
            if x_name is not None:
                response_data["x_name"] = x_name
            if y_name is not None:
                response_data["y_name"] = y_name
            
            # Note: Skip storing refreshed response to any database as per requirements
            # The updated component is only returned in API response, not stored
            logger.info(f"✅ Analytics component refreshed - returning in response only (not stored to database)")
            
            # 🧹 CRITICAL: Clear middle.json after component generation to prevent cross-request contamination
            try:
                with open(middle_json_path, "w") as f:
                    json.dump({}, f)  # Clear the file completely
                logger.info("🧹 middle.json cleared after analytics component refresh")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clear middle.json: {cleanup_error}")
            
            logger.info(f"✅ Analytics component {component_id} refreshed successfully")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Component refresh error: {e}")
            return jsonify({
                "success": False,
                "error": f"Component refresh failed: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.error(f"Error in refresh_analytics_component endpoint: {e}")
        from datetime import datetime
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

@app.route('/chat/analytics/display-all', methods=['POST'])
def display_all_analytics():
    """
    Batch display analytics components for a given agent_id and list of component_ids.
    Headers:
        token: User session token for authentication
    Request Body:
    {
        "agent_id": 123,
        "component_id_list": ["id1", "id2", ...]
    }
    Returns:
    {
        "success": true,
        "results": [ ... responses from /chat/analytics/refresh with dashboard_name added ... ],
        "count": <number>,
        "timestamp": ...
    }
    """
    from datetime import datetime
    try:
        # Get token from headers
        token = request.headers.get('token') or request.headers.get('Token')
        if not token:
            return jsonify({"success": False, "error": "Authentication token is required in headers"}), 401

        # Authenticate user token
        try:
            user_info = asyncio.run(verify_user_session_token(token))
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({"success": False, "error": "Authentication service error"}), 500

        # Parse request body
        data = request.get_json()
        if not data or 'agent_id' not in data or 'component_id_list' not in data:
            return jsonify({"success": False, "error": "agent_id and component_id_list are required in body"}), 400
        agent_id = data['agent_id']
        component_id_list = data['component_id_list']
        if not isinstance(component_id_list, list) or not component_id_list:
            return jsonify({"success": False, "error": "component_id_list must be a non-empty array"}), 400

        # Set dashboard_names to None since dashboard_name is not stored in MySQL dashboard_templates yet
        dashboard_names = {}
        for component_id in component_id_list:
            dashboard_names[component_id] = None
        
        logger.info(f"📊 Dashboard names set to None for {len(dashboard_names)} components (not stored in MySQL yet)")

        # Prepare requests to /chat/analytics/refresh
        results = []
        # Use localhost for internal API calls to avoid DNS resolution issues on deployed servers
        refresh_url = 'http://localhost:8001/chat/analytics/refresh'
        headers = {"token": token, "Content-Type": "application/json"}
        payload_template = {"conditions": {"where": {"AGENT_ID": agent_id}}}

        # Use httpx for async requests
        async def fetch_all():
            async with httpx.AsyncClient() as client:
                tasks = []
                for component_id in component_id_list:
                    payload = payload_template.copy()
                    payload["component_id"] = component_id
                    tasks.append(client.post(refresh_url, headers=headers, json=payload))
                responses = await asyncio.gather(*tasks)
                return [resp.json() for resp in responses]

        results = asyncio.run(fetch_all())

        # Add dashboard_name to each result
        for i, result in enumerate(results):
            if i < len(component_id_list):
                component_id = component_id_list[i]
                result["dashboard_name"] = dashboard_names.get(component_id)
                logger.debug(f"Added dashboard_name '{dashboard_names.get(component_id)}' to component {component_id}")

        return jsonify({
            "success": True,
            "results": results,
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    except Exception as e:
        logger.error(f"Error in display_all_analytics endpoint: {e}")
        from datetime import datetime
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

def get_mongodb_connection():
    """
    Get MongoDB connection with flexible credential handling
    Supports both authenticated (local) and non-authenticated (server) environments
    """
    try:
        # Get MongoDB credentials from environment - using the actual env var names
        mongo_uri = os.getenv('MONGODB_URI')
        mongo_host = os.getenv('MONGODB_HOST')
        mongo_database = os.getenv('MONGODB_DB_NAME')
        mongo_username = os.getenv('MONGODB_USERNAME')
        mongo_password = os.getenv('MONGODB_PASSWORD')
        
        # If full URI is provided, use it directly (both local and server have this)
        if mongo_uri:
            client = MongoClient(mongo_uri)
            # Extract database name from URI or use env variable
            if mongo_database:
                db = client[mongo_database]
            else:
                # Try to extract database from URI or default to masterDB
                db = client['masterDB']
        # If username and password are provided, use authenticated connection
        elif mongo_username and mongo_password and mongo_host and mongo_database:
            connection_string = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}/{mongo_database}"
            client = MongoClient(connection_string)
            db = client[mongo_database]
        # If only host is provided, use simple connection (server environment)
        elif mongo_host and mongo_database:
            connection_string = f"mongodb://{mongo_host}/{mongo_database}"
            client = MongoClient(connection_string)
            db = client[mongo_database]
        else:
            return None, "MongoDB connection credentials not found in environment"
        
        # Test the connection
        client.admin.command('ismaster')
        
        return db, "MongoDB connection successful"
        
        return db, "MongoDB connection successful"
        
    except Exception as e:
        return None, f"MongoDB connection failed: {str(e)}"

def store_chat_history(user_prompt, bot_response, workspace_id, ip_address, user_agent):
    """
    Store chat interaction in MongoDB
    
    Args:
        user_prompt: The user's input/question
        bot_response: Dict with form_id, component_html, error
        workspace_id: Current workspace ID
        ip_address: Client IP address
        user_agent: Browser/device info
    """
    try:
        db, connection_msg = get_mongodb_connection()
        if db is None:
            logger.error(f"Failed to connect to MongoDB: {connection_msg}")
            return False, connection_msg
        
        # Create the document
        document = {
            "user_prompt": user_prompt,
            "bot_response": bot_response,
            "timestamp": datetime.utcnow(),
            "workspace_id": workspace_id,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        # Insert into the collection
        collection = db["dashboard_bot_chat_history"]
        result = collection.insert_one(document)
        
        logger.info(f"✅ Chat history stored with ID: {result.inserted_id}")
        return True, f"Chat history stored successfully with ID: {result.inserted_id}"
        
    except Exception as e:
        error_msg = f"Failed to store chat history: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def store_analytics_agent_response(response_data):
    """
    Store analytics agent API response in MongoDB
    
    Args:
        response_data: Complete API response dictionary to store
    """
    try:
        db, connection_msg = get_mongodb_connection()
        if db is None:
            logger.error(f"Failed to connect to MongoDB: {connection_msg}")
            return False, connection_msg
        
        # Add MongoDB storage timestamp (in addition to API response timestamp)
        document = response_data.copy()
        document["mongodb_timestamp"] = datetime.utcnow()
        
        # Insert into the analytics_agent_response collection
        collection = db["analytics_agent_response"]
        result = collection.insert_one(document)
        
        logger.info(f"✅ Analytics agent response stored with ID: {result.inserted_id}")
        return True, f"Analytics agent response stored successfully with ID: {result.inserted_id}"
        
    except Exception as e:
        error_msg = f"Failed to store analytics agent response: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_recent_user_prompts(workspace_id: int, limit: int = 3) -> List[str]:
    """
    Retrieve the most recent user prompts for chat history context
    
    Args:
        workspace_id: Current workspace ID
        limit: Number of recent prompts to retrieve (default 3)
    
    Returns:
        List of recent user prompts, ordered by timestamp (newest first)
    """
    try:
        db, connection_msg = get_mongodb_connection()
        if db is None:
            logger.warning(f"Failed to connect to MongoDB for chat history: {connection_msg}")
            return []
        
        # Query for recent chats in this workspace
        collection = db["dashboard_bot_chat_history"]
        cursor = collection.find(
            {"workspace_id": workspace_id},
            {"user_prompt": 1, "timestamp": 1, "_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        # Extract user prompts
        user_prompts = []
        for doc in cursor:
            if doc.get("user_prompt"):
                user_prompts.append(doc["user_prompt"])
        
        logger.info(f"� Retrieved {len(user_prompts)} recent user prompts for workspace {workspace_id}")
        return user_prompts
        
    except Exception as e:
        logger.error(f"Failed to retrieve chat history: {str(e)}")
        return []

# combine_prompts_with_history function removed - conversation context now handled 
# directly in the main dashboard generation LLM for better performance

if __name__ == '__main__':
    print("🚀 Starting Dashboard Bot Version 4 API Server...")
    print("📊 MCP-based Architecture with Intelligent Agent + Optimized Polling + Token Tracking")
    print()
    print("📋 Available endpoints:")
    print("   GET  /chat/forms/health      - Health check and system status")
    print("   GET  /chat/forms/list        - List available forms")
    print("   POST /chat/forms/generate    - Generate components using MCP agent")
    print("   POST /chat/forms/refresh     - Refresh component with latest data")
    print("   POST /chat/analytics/voice  - Generate voice analytics components")
    print("   POST /chat/analytics/refresh      - Refresh analytics with conditions")
    print()
    print("💰 Token Usage Tracking:")
    print("   • OpenAI API usage tracking for billing")
    print("   • Per-workspace token accumulation")
    print("   • Request count tracking")
    print("   • Automatic database updates")
    print()
    
    app.run(host='0.0.0.0', port=8001, debug=True) 
# directly in the main dashboard generation LLM for better performance
