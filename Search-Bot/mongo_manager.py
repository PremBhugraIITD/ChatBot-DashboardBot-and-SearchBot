import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import logging
import urllib.parse

load_dotenv(override=True)

logger = logging.getLogger(__name__)

class MongoDBManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.chat_collection = None
        self._connect()
    
    def _connect(self):
        """
        Connect to MongoDB with flexible authentication
        Handles both local (with auth) and deployed (without auth) scenarios
        """
        try:
            # Get MongoDB credentials from environment
            username = os.getenv('MONGODB_USERNAME')
            password = os.getenv('MONGODB_PASSWORD')
            host = os.getenv('MONGODB_HOST', '43.204.206.231:27017')
            db_name = os.getenv('MONGODB_DB_NAME', 'masterDB')
            
            # Remove port from host if it's included
            if ':' in host:
                host_ip = host.split(':')[0]
                port = int(host.split(':')[1])
            else:
                host_ip = host
                port = int(os.getenv('MONGODB_PORT', 27017))
            
            # Determine connection string based on credentials availability
            if username and password and username.strip() and password.strip():
                # URL encode username and password for special characters
                encoded_username = urllib.parse.quote_plus(username)
                encoded_password = urllib.parse.quote_plus(password)
                
                # Local development with authentication
                connection_string = f"mongodb://{encoded_username}:{encoded_password}@{host_ip}:{port}/"
                logger.info("Connecting to MongoDB with authentication (local mode)")
            else:
                # Deployed server without authentication (IP whitelisted)
                connection_string = f"mongodb://{host_ip}:{port}/"
                logger.info("Connecting to MongoDB without authentication (deployed mode)")
            
            # Create MongoDB client
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.admin.command('ping')
            
            # Set database and collection
            self.db = self.client[db_name]
            self.chat_collection = self.db['search_bot_chat_history']
            
            logger.info(f"Successfully connected to MongoDB: {host_ip}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
            self.chat_collection = None
    
    def test_connection(self):
        """
        Test MongoDB connection and return status
        """
        try:
            if not self.client:
                return {
                    "status": "failed",
                    "message": "MongoDB client not initialized"
                }
            
            # Test with ping
            self.client.admin.command('ping')
            
            # Get server info
            server_info = self.client.server_info()
            
            return {
                "status": "success",
                "message": f"MongoDB connected successfully",
                "version": server_info.get('version', 'Unknown'),
                "database": self.db.name if self.db is not None else 'Unknown'
            }
            
        except Exception as e:
            logger.error(f"MongoDB connection test failed: {e}")
            return {
                "status": "failed",
                "message": f"MongoDB connection failed: {str(e)}"
            }
    
    def store_chat_message(self, message_content, sender_type, workspace_id, ip_address, user_agent, referenced_pages_info=None):
        """
        Store a chat message in MongoDB
        
        Args:
            message_content: The message text
            sender_type: "user" or "bot"
            workspace_id: Workspace ID from token verification
            ip_address: Client IP address
            user_agent: Client User-Agent string
            referenced_pages_info: List of dicts with page_id and page_title (optional)
        """
        try:
            if self.chat_collection is None:
                logger.error("MongoDB not connected - cannot store chat message")
                return False
            
            # Create document
            chat_document = {
                "message_content": message_content,
                "sender_type": sender_type,
                "timestamp": datetime.utcnow(),
                "workspace_id": workspace_id,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            # Add referenced pages info with IDs if provided
            if referenced_pages_info is not None:
                chat_document["referenced_pages_info"] = referenced_pages_info if isinstance(referenced_pages_info, list) else []
            
            # Insert document
            result = self.chat_collection.insert_one(chat_document)
            
            logger.info(f"Chat message stored with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store chat message: {e}")
            return False
    
    def get_chat_history(self, workspace_id, limit=50):
        """
        Retrieve chat history for a workspace
        
        Args:
            workspace_id: Workspace ID to filter by
            limit: Maximum number of messages to return
        """
        try:
            if self.chat_collection is None:
                logger.error("MongoDB not connected - cannot retrieve chat history")
                return []
            
            # Query chat history
            cursor = self.chat_collection.find(
                {"workspace_id": workspace_id}
            ).sort("timestamp", -1).limit(limit)
            
            # Convert to list and reverse to get chronological order
            messages = list(cursor)
            messages.reverse()
            
            # Convert ObjectId to string for JSON serialization
            for message in messages:
                message['_id'] = str(message['_id'])
                message['timestamp'] = message['timestamp'].isoformat()
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            return []
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
