"""
Search Bot Application with Token-based Security

SECURITY CRITICAL: This application implements multi-tenant data isolation using token-based authentication.
Users must provide a valid session token in headers which is verified against UnleashX API.
workspace_id is extracted from the authenticated token response to ensure secure data access.
"""

from flask import Flask, render_template, request, jsonify
from search_bot import SearchBot
from mongo_manager import MongoDBManager
import os
import httpx
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables with override
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get UnleashX URL from environment
UNLEASHX_URL = os.getenv("UNLEASHX_URL")
if not UNLEASHX_URL:
    raise ValueError("UNLEASHX_URL environment variable is required")

app = Flask(__name__, template_folder='.')
mongodb_manager = MongoDBManager()
search_bot = SearchBot(mongodb_manager)

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
                f"{UNLEASHX_URL}/api/getuser",
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

@app.route('/chat/pages/')
def index():
    return render_template('index.html')

@app.route('/chat/pages/test-database-connections')
def test_database_connections():
    """
    Test both MySQL and MongoDB connections
    """
    try:
        results = {
            "mysql": {"status": "unknown", "message": "Not tested"},
            "mongodb": {"status": "unknown", "message": "Not tested"}
        }
        
        # Test MySQL connection
        try:
            mysql_connection = search_bot.db.get_connection()
            if mysql_connection and mysql_connection.is_connected():
                mysql_connection.close()
                results["mysql"] = {
                    "status": "success",
                    "message": "MySQL connected successfully"
                }
            else:
                results["mysql"] = {
                    "status": "failed",
                    "message": "MySQL connection failed"
                }
        except Exception as e:
            results["mysql"] = {
                "status": "failed",
                "message": f"MySQL error: {str(e)}"
            }
        
        # Test MongoDB connection
        results["mongodb"] = mongodb_manager.test_connection()
        
        return jsonify({
            "success": True,
            "connections": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error testing connections: {str(e)}"
        }), 500

@app.route('/chat/pages/search', methods=['POST'])
def search():
    try:
        # Get token from headers
        token = request.headers.get('token') or request.headers.get('Token') or request.headers.get('Authorization')
        
        # Handle Authorization header format (Bearer token)
        if token and token.startswith('Bearer '):
            token = token[7:]  # Remove 'Bearer ' prefix
        
        if not token:
            return jsonify({'error': 'Authentication token is required in headers'}), 401
        
        # Get query from request body
        data = request.get_json()
        user_query = data.get('query', '').strip() if data else ''
        
        # Mandatory field validation
        if not user_query:
            return jsonify({'error': 'Please provide a search query'}), 400
        
        # Verify token and get user data (including workspace_id)
        try:
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                user_data = loop.run_until_complete(verify_user_session_token(token))
            finally:
                loop.close()
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            return jsonify({'error': f'Authentication error: {str(e)}'}), 500
        
        # Extract workspace_id and company_id from authenticated user data
        workspace_id = user_data.get('workspace_id')
        company_id = user_data.get('company_id')
        
        if not workspace_id:
            return jsonify({'error': 'No workspace associated with this user'}), 403
        
        # Get client IP address and user agent for chat history
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        user_agent = request.headers.get('User-Agent', 'unknown')
        
        # Store user message in MongoDB chat history
        mongodb_manager.store_chat_message(
            message_content=user_query,
            sender_type="user",
            workspace_id=workspace_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Get answer from search bot with authenticated workspace_id and company_id
        search_result = search_bot.search_and_answer(user_query, workspace_id, company_id)
        
        # Extract answer and referenced pages from the result
        if isinstance(search_result, dict):
            answer = search_result.get('answer', 'No answer received')
            referenced_pages_info = search_result.get('referenced_pages_info', [])
            usage_info = search_result.get('usage_info')
        else:
            # Backward compatibility in case it returns a string
            answer = str(search_result)
            referenced_pages_info = []
            usage_info = None
        
        answer = '\n'.join([line for line in answer.splitlines() if not line.strip().startswith('PAGES_USED:')])

        # Store bot response in MongoDB chat history
        mongodb_manager.store_chat_message(
            message_content=answer,
            sender_type="bot",
            workspace_id=workspace_id,
            ip_address=client_ip,
            user_agent=user_agent,
            referenced_pages_info=referenced_pages_info
        )
        
        response_data = {
            'success': True,
            'query': user_query,
            'workspace_id': workspace_id,
            'workspace_name': user_data.get('workspace_name'),
            'user': user_data.get('loginname'),
            'answer': answer,
            'referenced_pages_info': referenced_pages_info
        }
        
        # Include usage info in response if available (for debugging/monitoring)
        if usage_info:
            response_data['usage_info'] = usage_info
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

@app.route('/chat/pages/summary')
def summary():
    try:
        # Get token from headers
        token = request.headers.get('token') or request.headers.get('Token') or request.headers.get('Authorization')
        
        # Handle Authorization header format (Bearer token)
        if token and token.startswith('Bearer '):
            token = token[7:]  # Remove 'Bearer ' prefix
        
        if not token:
            return jsonify({'error': 'Authentication token is required in headers'}), 401
        
        # Verify token and get user data (including workspace_id)
        try:
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                user_data = loop.run_until_complete(verify_user_session_token(token))
            finally:
                loop.close()
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            return jsonify({'error': f'Authentication error: {str(e)}'}), 500
        
        # Extract workspace_id from authenticated user data
        workspace_id = user_data.get('workspace_id')
        if not workspace_id:
            return jsonify({'error': 'No workspace associated with this user'}), 403
        
        # Get summary with authenticated workspace_id
        summary_text = search_bot.get_knowledge_base_summary(workspace_id)
        
        return jsonify({
            'success': True,
            'workspace_id': workspace_id,
            'workspace_name': user_data.get('workspace_name'),
            'user': user_data.get('loginname'),
            'summary': summary_text
        })
        
    except Exception as e:
        return jsonify({'error': f'Error getting summary: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
