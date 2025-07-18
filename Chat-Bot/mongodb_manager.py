"""
MongoDB Manager for Chat History Storage

This module handles MongoDB connections and operations for storing chat history
from the MCP multi-agent chatbot system.

Features:
- Dual-environment connection support (local with auth + production without auth)
- Connection management with proper error handling
- Chat history storage with structured schema
- Async operations for WebSocket integration
- Connection pooling and retry logic

Environment Detection:
- LOCAL: Uses authentication if MONGODB_USERNAME and MONGODB_PASSWORD are present
- PRODUCTION: Uses direct connection if credentials are missing (IP-whitelisted access)

Database Schema:
- Database: masterDB (or MONGODB_DB_NAME)
- Collection: chat_agent_chat_history
- Document: {
    session_id: str,
    user_prompt: str, 
    agent_response: str,
    agent_used: str,
    timestamp: datetime
  }

Environment Variables:
- MONGODB_URI: Full MongoDB connection string
- MONGODB_DB_NAME: Database name (default: masterDB)
- MONGODB_USERNAME: Username for authentication (local only)
- MONGODB_PASSWORD: Password for authentication (local only)
- MONGODB_HOST: MongoDB host with port (e.g., localhost:27017)
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import quote_plus
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv(override=True)

# Configure logging
logger = logging.getLogger(__name__)

class MongoDBManager:
    """Manages MongoDB connections and chat history operations."""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self.chat_collection = None
        self.is_connected = False
        
        # MongoDB configuration from environment
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.mongodb_db_name = os.getenv('MONGODB_DB_NAME')  # Default fallback
        self.mongodb_username = os.getenv('MONGODB_USERNAME')
        self.mongodb_password = os.getenv('MONGODB_PASSWORD')
        self.mongodb_host = os.getenv('MONGODB_HOST')
        
        # Log configuration for debugging (without sensitive info)
        logger.info("🔧 MongoDB Configuration loaded:")
        logger.info(f"   📊 Database: {self.mongodb_db_name}")
        logger.info(f"   🌐 URI: {self.mongodb_uri if self.mongodb_uri else 'Not set'}")
        logger.info(f"   🏠 Host: {self.mongodb_host if self.mongodb_host else 'Not set'}")
        logger.info(f"   👤 Username: {'Present' if self.mongodb_username else 'Not set'}")
        logger.info(f"   🔐 Password: {'Present' if self.mongodb_password else 'Not set'}")
        
        # Validate we have minimum required configuration
        if not self.mongodb_db_name:
            logger.warning("⚠️  MONGODB_DB_NAME not set, using default: masterDB")
            self.mongodb_db_name = 'masterDB'
            
        # Check if we have any connection method
        has_uri = bool(self.mongodb_uri)
        has_host = bool(self.mongodb_host)
        has_credentials = bool(self.mongodb_username and self.mongodb_password)
        
        if not (has_uri or has_host):
            logger.error("❌ No MongoDB connection method available! Set either MONGODB_URI or MONGODB_HOST")
        elif has_credentials:
            logger.info("✅ Authentication credentials detected - will use authenticated connection")
        else:
            logger.info("🔓 No authentication credentials - will use direct connection")
        
    def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        Supports both authenticated (local) and non-authenticated (production) connections.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Determine connection mode based on available credentials
            has_auth_credentials = (
                self.mongodb_username and 
                self.mongodb_password and 
                self.mongodb_username.strip() and 
                self.mongodb_password.strip()
            )
            
            if has_auth_credentials:
                # LOCAL ENVIRONMENT: Use authenticated connection
                logger.info("🔐 Using authenticated MongoDB connection (local environment)")
                
                # Remove quotes from password if they exist and URL encode
                password = self.mongodb_password.strip('"\'')
                username = self.mongodb_username.strip()
                
                # URL encode username and password for special characters
                encoded_username = quote_plus(username)
                encoded_password = quote_plus(password)
                
                # Construct authenticated connection string
                connection_string = f"mongodb://{encoded_username}:{encoded_password}@{self.mongodb_host}/{self.mongodb_db_name}?authSource=admin"
                logger.info(f"🔗 Connecting to: mongodb://{username}:***@{self.mongodb_host}/{self.mongodb_db_name}")
                
            else:
                # PRODUCTION ENVIRONMENT: Use non-authenticated connection
                logger.info("🌐 Using non-authenticated MongoDB connection (production environment)")
                
                if self.mongodb_uri:
                    connection_string = self.mongodb_uri
                    logger.info(f"🔗 Connecting to: {self.mongodb_uri}")
                else:
                    # Fallback: construct basic URI from host if available
                    if self.mongodb_host:
                        connection_string = f"mongodb://{self.mongodb_host}"
                        logger.info(f"🔗 Connecting to: {connection_string}")
                    else:
                        logger.error("❌ No MongoDB connection info available (neither credentials nor URI)")
                        return False
            
            # Create MongoDB client with connection timeout
            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000,
                maxPoolSize=10,
                retryWrites=True
            )
            
            # Test the connection
            self.client.admin.command('ping')
            
            # Get database and collection references
            self.db = self.client[self.mongodb_db_name]
            self.chat_collection = self.db['chat_agent_chat_history']
            self.activities_collection = self.db['agent_activities']  # NEW: Tool activities collection
            
            self.is_connected = True
            logger.info(f"✅ Successfully connected to MongoDB database: {self.mongodb_db_name}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected MongoDB connection error: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.is_connected = False
            logger.info("🔌 Disconnected from MongoDB")
    
    def store_message(
        self, 
        session_id: str, 
        message_content: str, 
        sender_type: str,
        agent_used: str,
        agent_id: int = None,
        workspace_id: int = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """
        Store an individual message in MongoDB.
        
        Args:
            session_id: WebSocket session UUID
            message_content: The message content (user query or bot response)
            sender_type: "user" or "bot"
            agent_used: Which agent handled it (developer/writer/sales/general)
            agent_id: ID from authentication API response (optional)
            workspace_id: Workspace ID from authentication API response (optional)
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        if not self.is_connected:
            logger.warning("⚠️  MongoDB not connected, attempting to reconnect...")
            if not self.connect():
                logger.error("❌ Failed to reconnect to MongoDB, skipping message storage")
                return False
        
        try:
            # Create document with required schema
            message_document = {
                "session_id": session_id,
                "message_content": message_content,
                "sender_type": sender_type,
                "agent_used": agent_used,
                "timestamp": datetime.utcnow()
            }
            
            # Add optional fields if provided
            if agent_id is not None:
                message_document["agent_id"] = agent_id
            if workspace_id is not None:
                message_document["workspace_id"] = workspace_id
            if ip_address is not None:
                message_document["ip_address"] = ip_address
            if user_agent is not None:
                message_document["user_agent"] = user_agent
            
            # Insert document into collection
            result = self.chat_collection.insert_one(message_document)
            
            if result.inserted_id:
                logger.info(f"✅ Message stored successfully: {sender_type} message | Session: {session_id[:8]}...")
                return True
            else:
                logger.error("❌ Failed to store message: No insertion ID returned")
                return False
                
        except Exception as e:
            logger.error(f"❌ MongoDB error during message storage: {e}")
            return False
    
    async def store_message_async(
        self, 
        session_id: str, 
        message_content: str, 
        sender_type: str,
        agent_used: str,
        agent_id: int = None,
        workspace_id: int = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """
        Async wrapper for storing individual messages.
        
        Args:
            session_id: WebSocket session UUID
            message_content: The message content (user query or bot response)
            sender_type: "user" or "bot"
            agent_used: Which agent handled it (developer/writer/sales/general)
            agent_id: ID from authentication API response (optional)
            workspace_id: Workspace ID from authentication API response (optional)
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        # Run the synchronous operation in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.store_message, 
            session_id, 
            message_content, 
            sender_type,
            agent_used,
            agent_id,
            workspace_id,
            ip_address,
            user_agent
        )

    async def store_chat_interaction_async(
        self, 
        session_id: str, 
        user_prompt: str, 
        agent_response: str, 
        agent_used: str,
        agent_id: int = None,
        workspace_id: int = None
    ) -> bool:
        """
        Async wrapper for storing chat interactions.
        
        Args:
            session_id: WebSocket session UUID
            user_prompt: User's message/question
            agent_response: Bot's response
            agent_used: Which agent handled it (developer/writer/sales/general)
            agent_id: ID from authentication API response (optional)
            workspace_id: Workspace ID from authentication API response (optional)
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        # Run the synchronous operation in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.store_chat_interaction, 
            session_id, 
            user_prompt, 
            agent_response, 
            agent_used,
            agent_id,
            workspace_id
        )
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> list:
        """
        Retrieve chat history for a session.
        
        Args:
            session_id: WebSocket session UUID
            limit: Maximum number of interactions to retrieve
            
        Returns:
            list: List of chat interaction documents
        """
        if not self.is_connected:
            logger.warning("⚠️  MongoDB not connected")
            return []
        
        try:
            # Query chat history for session, sorted by timestamp
            cursor = self.chat_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", 1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"❌ Error retrieving chat history: {e}")
            return []
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get MongoDB connection status information.
        
        Returns:
            dict: Connection status details
        """
        try:
            if self.is_connected and self.client:
                # Test connection
                self.client.admin.command('ping')
                return {
                    "connected": True,
                    "database": self.mongodb_db_name,
                    "collection": "chat_agent_chat_history",
                    "host": self.mongodb_host
                }
            else:
                return {
                    "connected": False,
                    "error": "Not connected to MongoDB"
                }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def test_connection(self) -> bool:
        """
        Test MongoDB connection for health checks.
        
        Returns:
            bool: True if connection is working, False otherwise
        """
        try:
            if not self.is_connected:
                # Try to reconnect if not connected
                if not self.connect():
                    return False
            
            # Test connection with ping command
            self.client.admin.command('ping')
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection test failed: {e}")
            return False

    # NEW: Tool Activity Tracking Methods
    def create_tool_activity(
        self,
        agent_id: int,
        workspace_id: int,
        tool_called: str,
        tool_input: dict
    ) -> Optional[str]:
        """
        Create a new tool activity document when a tool starts running.
        
        Args:
            agent_id: Agent ID
            workspace_id: Workspace ID
            tool_called: Name of the tool being called
            tool_input: Input parameters for the tool
            
        Returns:
            str: MongoDB document ID if successful, None otherwise
        """
        if not self.is_connected:
            logger.warning("⚠️  MongoDB not connected, attempting to reconnect...")
            if not self.connect():
                logger.error("❌ Failed to reconnect to MongoDB, skipping tool activity creation")
                return None
        
        try:
            # Create tool activity document
            activity_document = {
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "tool_called": tool_called,
                "tool_input": tool_input,
                "timestamp": datetime.utcnow(),
                "status": "running"
            }
            
            # Insert document into activities collection
            result = self.activities_collection.insert_one(activity_document)
            
            if result.inserted_id:
                logger.info(f"✅ Tool activity created: {tool_called} | Agent: {agent_id} | ID: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                logger.error("❌ Failed to create tool activity: No insertion ID returned")
                return None
                
        except Exception as e:
            logger.error(f"❌ MongoDB error during tool activity creation: {e}")
            return None

    def update_tool_activity(
        self,
        activity_id: str,
        tool_output: any,
        status: str = "completed"
    ) -> bool:
        """
        Update a tool activity document when the tool completes.
        
        Args:
            activity_id: MongoDB document ID from create_tool_activity
            tool_output: Output from the tool execution
            status: Status of the tool execution ("completed" or "failed")
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        if not self.is_connected:
            logger.warning("⚠️  MongoDB not connected, attempting to reconnect...")
            if not self.connect():
                logger.error("❌ Failed to reconnect to MongoDB, skipping tool activity update")
                return False
        
        try:
            from bson import ObjectId
            
            # Get the original document to calculate time_taken
            original_doc = self.activities_collection.find_one({"_id": ObjectId(activity_id)})
            if not original_doc:
                logger.error(f"❌ Tool activity document not found: {activity_id}")
                return False
            
            # Calculate time taken
            start_time = original_doc.get("timestamp")
            current_time = datetime.utcnow()
            time_taken = int((current_time - start_time).total_seconds() * 1000)  # milliseconds
            
            # Update document
            update_data = {
                "tool_output": tool_output,
                "timestamp": current_time,
                "status": status,
                "time_taken": time_taken
            }
            
            result = self.activities_collection.update_one(
                {"_id": ObjectId(activity_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Tool activity updated: {original_doc.get('tool_called')} | Status: {status} | Time: {time_taken}ms")
                return True
            else:
                logger.error(f"❌ Failed to update tool activity: {activity_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ MongoDB error during tool activity update: {e}")
            return False

    async def create_tool_activity_async(
        self,
        agent_id: int,
        workspace_id: int,
        tool_called: str,
        tool_input: dict
    ) -> Optional[str]:
        """Async version of create_tool_activity."""
        return self.create_tool_activity(agent_id, workspace_id, tool_called, tool_input)

    async def update_tool_activity_async(
        self,
        activity_id: str,
        tool_output: any,
        status: str = "completed"
    ) -> bool:
        """Async version of update_tool_activity."""
        return self.update_tool_activity(activity_id, tool_output, status)

# Global MongoDB manager instance
mongodb_manager = MongoDBManager()

# Initialize connection on module import
if not mongodb_manager.connect():
    logger.warning("⚠️  MongoDB connection failed during initialization")