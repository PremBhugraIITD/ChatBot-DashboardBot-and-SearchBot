"""
Integrated Server for AI Agent System

This module serves as the main integration point for all three applications:
- Chat-Bot: WebSocket and REST API endpoints for MCP multi-agent system
- Dashboard-Bot: Flask app for data visualization and dashboard generation
- Search-Bot: Flask app for AI-powered knowledge base search

All applications are served on the same base URL (localhost:8001) with proper routing.
"""

import os
import sys
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Dashboard-Bot Flask app
try:
    dashboard_bot_path = os.path.join(os.path.dirname(__file__), "Dashboard-Bot")
    if dashboard_bot_path not in sys.path:
        sys.path.insert(0, dashboard_bot_path)
    
    original_cwd = os.getcwd()
    os.chdir(dashboard_bot_path)
    
    from api_server import app as dashboard_flask_app
    
    os.chdir(original_cwd)
    
    logger.info("✅ Dashboard-Bot Flask app imported successfully")
    DASHBOARD_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ Failed to import Dashboard-Bot app: {e}")
    dashboard_flask_app = None
    DASHBOARD_AVAILABLE = False

# Import Search-Bot Flask app
try:
    search_bot_path = os.path.join(os.path.dirname(__file__), "Search-Bot")
    if search_bot_path not in sys.path:
        sys.path.insert(0, search_bot_path)
    
    original_cwd = os.getcwd()
    os.chdir(search_bot_path)
    
    from app import app as search_bot_flask_app
    
    os.chdir(original_cwd)
    
    logger.info("✅ Search-Bot Flask app imported successfully")
    SEARCH_BOT_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ Failed to import Search-Bot app: {e}")
    search_bot_flask_app = None
    SEARCH_BOT_AVAILABLE = False

# Import Chat-Bot FastAPI app
try:
    chat_bot_path = os.path.join(os.path.dirname(__file__), "Chat-Bot")
    if chat_bot_path not in sys.path:
        sys.path.insert(0, chat_bot_path)
    
    original_cwd = os.getcwd()
    os.chdir(chat_bot_path)
    
    from websocket_server import app as chat_bot_fastapi_app
    
    os.chdir(original_cwd)
    
    logger.info("✅ Chat-Bot FastAPI app imported successfully")
    CHAT_BOT_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ Failed to import Chat-Bot app: {e}")
    chat_bot_fastapi_app = None
    CHAT_BOT_AVAILABLE = False

def create_combined_flask_app():
    """Create a combined Flask application with both Dashboard-Bot and Search-Bot routes."""
    from flask import Flask
    
    combined_app = Flask(__name__)
    
    if SEARCH_BOT_AVAILABLE and search_bot_flask_app:
        search_bot_path = os.path.join(os.path.dirname(__file__), "Search-Bot")
        combined_app.template_folder = search_bot_path
        
        if hasattr(search_bot_flask_app, 'search_bot'):
            combined_app.search_bot = search_bot_flask_app.search_bot
        else:
            logger.warning("SearchBot instance not found in original app")
    
    if DASHBOARD_AVAILABLE and dashboard_flask_app:
        if hasattr(dashboard_flask_app, 'dashboard_backend'):
            combined_app.dashboard_backend = dashboard_flask_app.dashboard_backend
        else:
            logger.warning("Dashboard backend not found in original app")
            combined_app.dashboard_backend = None
            
        for rule in dashboard_flask_app.url_map.iter_rules():
            endpoint = rule.endpoint
            methods = list(rule.methods - {'HEAD', 'OPTIONS'})
            
            view_func = dashboard_flask_app.view_functions.get(endpoint)
            if view_func:
                combined_app.add_url_rule(
                    rule.rule,
                    endpoint=f"dashboard_{endpoint}",
                    view_func=view_func,
                    methods=methods
                )
        logger.info("🔧 Dashboard-Bot routes added to combined app")
    
    if SEARCH_BOT_AVAILABLE and search_bot_flask_app:
        for rule in search_bot_flask_app.url_map.iter_rules():
            endpoint = rule.endpoint
            methods = list(rule.methods - {'HEAD', 'OPTIONS'})
            
            view_func = search_bot_flask_app.view_functions.get(endpoint)
            if view_func:
                combined_app.add_url_rule(
                    rule.rule,
                    endpoint=f"search_{endpoint}",
                    view_func=view_func,
                    methods=methods
                )
        logger.info("🔧 Search-Bot routes added to combined app")
    
    return combined_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for the integrated server."""
    try:
        logger.info("🚀 Integrated server starting - Chat-Bot + Dashboard-Bot + Search-Bot")
        yield
    finally:
        logger.info("🛑 Integrated server shutting down")

app = FastAPI(
    lifespan=lifespan, 
    title="AI Agent Integrated Server", 
    description="Integrated server for Chat-Bot, Dashboard-Bot, and Search-Bot applications"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Chat-Bot FastAPI app first at root (it has /chat/* routes)
if CHAT_BOT_AVAILABLE and chat_bot_fastapi_app:
    try:
        # Add the Chat-Bot routes directly to the main FastAPI app
        for route in chat_bot_fastapi_app.routes:
            app.router.routes.append(route)
        logger.info("🔧 Chat-Bot FastAPI routes added to main app")
        logger.info("🔗 Chat-Bot endpoints available:")
        logger.info("   • WS   /chat/ws - Real-time chat with streaming responses")
        logger.info("   • GET  /chat/api/test - Interactive WebSocket test page")
        logger.info("   • GET  /chat/api/health - Health check with connection status")
        logger.info("   • POST /chat/api/query - Main chat endpoint with intelligent agent routing")
    except Exception as e:
        logger.error(f"❌ Failed to add Chat-Bot routes: {e}")

# Create and mount combined Flask app (handles /chat/forms/* and /chat/pages/*)
combined_flask_app = None
if DASHBOARD_AVAILABLE or SEARCH_BOT_AVAILABLE:
    try:
        combined_flask_app = create_combined_flask_app()
        logger.info("✅ Combined Flask app created successfully")
        
        app.mount("/", WSGIMiddleware(combined_flask_app))
        logger.info("🔧 Combined Flask app mounted at root")
        
        if DASHBOARD_AVAILABLE:
            logger.info("📊 Dashboard endpoints available:")
            logger.info("   • GET  /chat/forms/health - Dashboard health check")
            logger.info("   • GET  /chat/forms/list - List available forms")
            logger.info("   • POST /chat/forms/generate - Generate dashboard components")
            logger.info("   • POST /chat/forms/refresh - Refresh existing components")
        
        if SEARCH_BOT_AVAILABLE:
            logger.info("🔍 Search-Bot endpoints available:")
            logger.info("   • GET  /chat/pages/ - Search-Bot interface")
            logger.info("   • GET  /chat/pages/test-database-connections - Test database connectivity")
            logger.info("   • POST /chat/pages/search - Knowledge base search")
            logger.info("   • GET  /chat/pages/summary - Knowledge base summary")
            
    except Exception as e:
        logger.error(f"❌ Failed to create combined Flask app: {e}")
        combined_flask_app = None
else:
    logger.warning("⚠️ No Flask apps available - only Chat-Bot endpoints will work")

if __name__ == "__main__":
    print("🚀 Starting Integrated AI Agent Server...")
    print()
    
    if CHAT_BOT_AVAILABLE:
        print("📱 Chat-Bot WebSocket Endpoints:")
        print("   • WS   /chat/ws - Real-time chat with streaming responses")
        print()
        print("🔗 Chat-Bot API Endpoints:")
        print("   • GET  /chat/api/test - Interactive WebSocket test page")
        print("   • GET  /chat/api/health - Health check with connection status")
        print("   • POST /chat/api/query - Main chat endpoint with intelligent agent routing")
        print()
    else:
        print("⚠️ Chat-Bot Integration: DISABLED")
    
    if DASHBOARD_AVAILABLE:
        print("📊 Dashboard-Bot API Endpoints:")
        print("   • GET  /chat/forms/health - Dashboard health check")
        print("   • GET  /chat/forms/list - List available forms/tables")
        print("   • POST /chat/forms/generate - Generate dashboard components")
        print("   • POST /chat/forms/refresh - Refresh existing components")
        print()
    else:
        print("⚠️ Dashboard-Bot Integration: DISABLED")
    
    if SEARCH_BOT_AVAILABLE:
        print("🔍 Search-Bot API Endpoints:")
        print("   • GET  /chat/pages - Search-Bot interface")
        print("   • GET  /chat/pages/test-database-connections - Test database connectivity")
        print("   • POST /chat/pages/search - Knowledge base search with token auth")
        print("   • GET  /chat/pages/summary - Knowledge base summary with token auth")
        print()
    else:
        print("⚠️ Search-Bot Integration: DISABLED")
    
    print("🌐 Server starting on http://localhost:8001")
    if CHAT_BOT_AVAILABLE:
        print("📱 WebSocket URL: ws://localhost:8001/chat/ws?token=your_token")
    print()
    
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT")), reload=True)
