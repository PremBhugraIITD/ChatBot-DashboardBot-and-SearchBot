#!/usr/bin/env python3
"""
Knowledge Base MCP Server

This server provides knowledge base integration capabilities for the MCP API server.
It uses the query engine storage located within the aiagent directory.

Note: To create or update the knowledge base, you need to populate the 
'query-engine-storage' directory within this aiagent folder with your vector store files.

Usage:
    python knowledge_base_server.py
"""

import os
import sys
import json
import logging
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Import MCP server components
from mcp.server.fastmcp import FastMCP

# S3 integration
try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    logging.warning("boto3 not available - S3 operations will be disabled")

# Import LlamaIndex components for vector store operations
try:
    from llama_index.core import (
        VectorStoreIndex,
        SimpleDirectoryReader,
        StorageContext,
        Document,
        load_index_from_storage
    )
    from llama_index.core.settings import Settings
    from llama_index.embeddings.openai import OpenAIEmbedding
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    logging.warning("LlamaIndex not available - vector operations will be disabled")

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Knowledge Base")

# Get agent ID from environment variable (passed from mcp_servers_list.py)
AGENT_ID = os.getenv("AGENT_ID", "default")
logger.info(f"🔧 Knowledge Base Server initialized for Agent ID: {AGENT_ID}")

# S3 Configuration
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

# Global variables for knowledge base storage
PERSIST_DIR = None
TEMP_KB_DIR = None  # For S3 downloads

def get_s3_client():
    """Initialize and return S3 client."""
    if not S3_AVAILABLE:
        return None
    
    try:
        return boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=AWS_REGION
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize S3 client: {e}")
        return None

def get_agent_s3_path(agent_id):
    """Get the S3 path for agent's knowledge base."""
    return f"workspace/agent/{agent_id}/query-engine-storage"

def download_s3_knowledge_base(agent_id):
    """Download agent-specific knowledge base from S3 to temporary directory."""
    if not S3_AVAILABLE:
        logger.error("❌ S3 not available")
        return None, False
    
    s3_client = get_s3_client()
    if not s3_client:
        return None, False
    
    if not AWS_BUCKET_NAME:
        logger.error("❌ AWS_BUCKET_NAME environment variable not set")
        return None, False
    
    try:
        s3_path = get_agent_s3_path(agent_id)
        logger.info(f"🔍 Looking for Agent {agent_id}'s knowledge base in S3: s3://{AWS_BUCKET_NAME}/{s3_path}")
        
        # List objects in the S3 path to check if knowledge base exists
        response = s3_client.list_objects_v2(
            Bucket=AWS_BUCKET_NAME,
            Prefix=s3_path + "/",
            MaxKeys=1
        )
        
        if 'Contents' not in response:
            logger.warning(f"⚠️ No knowledge base found in S3 for agent {agent_id}")
            return None, False
        
        logger.info(f"✅ Found S3 knowledge base for agent {agent_id}")
        
        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp(prefix=f"kb_agent_{agent_id}_")
        
        # List all objects in the knowledge base
        response = s3_client.list_objects_v2(
            Bucket=AWS_BUCKET_NAME,
            Prefix=s3_path + "/"
        )
        
        downloaded_files = 0
        for obj in response.get('Contents', []):
            s3_key = obj['Key']
            # Skip directory markers
            if s3_key.endswith('/'):
                continue
            
            # Get filename from S3 key
            filename = os.path.basename(s3_key)
            local_file_path = os.path.join(temp_dir, filename)
            
            # Download file
            s3_client.download_file(AWS_BUCKET_NAME, s3_key, local_file_path)
            downloaded_files += 1
        
        logger.info(f"📥 Downloaded {downloaded_files} files from S3 to: {temp_dir}")
        return temp_dir, True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"❌ S3 bucket not found: {AWS_BUCKET_NAME}")
        elif error_code == 'AccessDenied':
            logger.error("❌ Access denied to S3 bucket")
        else:
            logger.error(f"❌ S3 client error: {e}")
        return None, False
    except Exception as e:
        logger.error(f"❌ Error downloading knowledge base from S3: {e}")
        return None, False

def initialize_knowledge_base(agent_id=None):
    """Initialize knowledge base for the specified agent."""
    global PERSIST_DIR, TEMP_KB_DIR
    
    # Use provided agent_id or fallback to environment variable
    target_agent_id = agent_id or AGENT_ID
    
    logger.info(f"🔧 Initializing knowledge base for Agent ID: {target_agent_id}")
    
    # Clean up any previous temporary directory
    if TEMP_KB_DIR and os.path.exists(TEMP_KB_DIR):
        try:
            shutil.rmtree(TEMP_KB_DIR)
            logger.info(f"🧹 Cleaned up previous temporary directory: {TEMP_KB_DIR}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup previous temp directory: {e}")
    
    # Try to download from S3 (S3-only approach as requested)
    if S3_AVAILABLE:
        temp_dir, success = download_s3_knowledge_base(target_agent_id)
        if success:
            PERSIST_DIR = Path(temp_dir)
            TEMP_KB_DIR = temp_dir
            logger.info(f"✅ Using S3-based knowledge base for agent {target_agent_id}")
            return True
    
    # If S3 is not available or download failed
    logger.error(f"❌ Failed to load knowledge base for agent {target_agent_id} from S3")
    PERSIST_DIR = None
    TEMP_KB_DIR = None
    return False

# Initialize knowledge base on server startup
initialize_knowledge_base()

# Constants (keeping for backward compatibility)
CURRENT_DIR = Path(__file__).parent
QUERY_ENGINE_STORAGE = CURRENT_DIR / "query-engine-storage"

@mcp.tool()
def query_knowledge_base(query: str, top_k: int = 3, agent_id: str = None) -> Dict[str, Any]:
    """
    Query the knowledge base using the vector store index.
    
    Args:
        query: The question or search query
        top_k: Number of top results to return (default: 3)
        agent_id: Agent ID to use (defaults to server's AGENT_ID)
    
    Returns:
        Dictionary containing the answer and source information
    """
    if not LLAMA_INDEX_AVAILABLE:
        return {
            "error": "LlamaIndex not available",
            "message": "Vector operations are disabled"
        }
    
    # Use provided agent_id or default to server's AGENT_ID
    target_agent_id = agent_id or AGENT_ID
    
    # Initialize knowledge base for the target agent if different from current
    if agent_id and agent_id != AGENT_ID:
        success = initialize_knowledge_base(target_agent_id)
        if not success:
            return {
                "error": f"Failed to load knowledge base for agent {target_agent_id}",
                "message": "Knowledge base not found in S3"
            }
    
    if not PERSIST_DIR or not PERSIST_DIR.exists():
        return {
            "error": f"No knowledge base found for agent {target_agent_id}",
            "message": "Vector store index not found. Please create or sync the knowledge base first."
        }
    
    try:
        # Load the vector index
        logger.info(f"Loading vector index from {PERSIST_DIR} for agent {target_agent_id}")
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        index = load_index_from_storage(storage_context)
        
        # Create a query engine
        query_engine = index.as_query_engine(similarity_top_k=top_k)
        
        # Execute the query
        logger.info(f"Executing query: '{query}' for agent {target_agent_id}")
        response = query_engine.query(query)
        
        # Extract source information
        sources = []
        if hasattr(response, 'source_nodes'):
            for i, node in enumerate(response.source_nodes):
                sources.append({
                    "rank": i + 1,
                    "file_name": node.metadata.get('file_name', 'Unknown'),
                    "score": float(node.score) if hasattr(node, 'score') else 0.0,
                    "text_preview": node.text[:200] + "..." if len(node.text) > 200 else node.text
                })
        
        return {
            "success": True,
            "answer": str(response),
            "query": query,
            "agent_id": target_agent_id,
            "sources": sources,
            "total_sources": len(sources)
        }
        
    except Exception as e:
        logger.error(f"Error querying knowledge base for agent {target_agent_id}: {str(e)}")
        return {
            "error": f"Query failed: {str(e)}",
            "success": False,
            "agent_id": target_agent_id
        }

@mcp.tool()
def get_knowledge_base_status(agent_id: str = None) -> Dict[str, Any]:
    """
    Get the current status of the knowledge base including index information.
    
    Args:
        agent_id: Agent ID to check status for (defaults to server's AGENT_ID)
    
    Returns:
        Dictionary containing status information
    """
    # Use provided agent_id or default to server's AGENT_ID
    target_agent_id = agent_id or AGENT_ID
    
    # Initialize knowledge base for the target agent if different from current
    if agent_id and agent_id != AGENT_ID:
        success = initialize_knowledge_base(target_agent_id)
        if not success:
            return {
                "error": f"Failed to load knowledge base for agent {target_agent_id}",
                "message": "Knowledge base not found in S3",
                "agent_id": target_agent_id
            }
    
    status = {
        "agent_id": target_agent_id,
        "persist_dir": str(PERSIST_DIR) if PERSIST_DIR else None,
        "index_exists": False,
        "llama_index_available": LLAMA_INDEX_AVAILABLE,
        "s3_available": S3_AVAILABLE,
        "storage_type": "S3" if TEMP_KB_DIR else "Local",
        "aws_bucket": AWS_BUCKET_NAME
    }
    
    if PERSIST_DIR and PERSIST_DIR.exists():
        status["index_exists"] = True
        
        # Check for index files
        index_files = list(PERSIST_DIR.glob("*"))
        status["index_files"] = [f.name for f in index_files]
        status["file_count"] = len(index_files)
        
        # Try to get index stats if possible
        if LLAMA_INDEX_AVAILABLE:
            try:
                storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
                index = load_index_from_storage(storage_context)
                
                # Get docstore info
                docstore_path = PERSIST_DIR / "docstore.json"
                if docstore_path.exists():
                    with open(docstore_path, 'r') as f:
                        docstore_data = json.load(f)
                        status["document_count"] = len(docstore_data.get("docstore/data", {}))
                
                status["index_loaded_successfully"] = True
                
            except Exception as e:
                status["index_load_error"] = str(e)
                status["index_loaded_successfully"] = False
    
    return status

@mcp.tool()
def list_knowledge_sources(agent_id: str = None) -> Dict[str, Any]:
    """
    List all documents and sources in the knowledge base.
    
    Args:
        agent_id: Agent ID to list sources for (defaults to server's AGENT_ID)
    
    Returns:
        Dictionary containing information about all indexed documents
    """
    # Use provided agent_id or default to server's AGENT_ID
    target_agent_id = agent_id or AGENT_ID
    
    # Initialize knowledge base for the target agent if different from current
    if agent_id and agent_id != AGENT_ID:
        success = initialize_knowledge_base(target_agent_id)
        if not success:
            return {
                "error": f"Failed to load knowledge base for agent {target_agent_id}",
                "documents": [],
                "agent_id": target_agent_id
            }
    
    if not PERSIST_DIR or not PERSIST_DIR.exists():
        return {
            "error": f"No knowledge base found for agent {target_agent_id}",
            "documents": [],
            "agent_id": target_agent_id
        }
    
    documents = []
    
    try:
        # Read docstore.json to get document information
        docstore_path = PERSIST_DIR / "docstore.json"
        if docstore_path.exists():
            with open(docstore_path, 'r') as f:
                docstore_data = json.load(f)
                
            doc_data = docstore_data.get("docstore/data", {})
            
            for doc_id, doc_info in doc_data.items():
                doc_entry = {
                    "id": doc_id,
                    "metadata": doc_info.get("__data__", {}).get("metadata", {}),
                    "text_length": len(doc_info.get("__data__", {}).get("text", "")),
                    "type": doc_info.get("__type__", "unknown")
                }
                
                # Extract useful metadata
                metadata = doc_entry["metadata"]
                doc_entry["file_name"] = metadata.get("file_name", "Unknown")
                doc_entry["file_path"] = metadata.get("file_path", "Unknown")
                
                documents.append(doc_entry)
        
        return {
            "success": True,
            "agent_id": target_agent_id,
            "document_count": len(documents),
            "documents": documents
        }
        
    except Exception as e:
        logger.error(f"Error listing knowledge sources for agent {target_agent_id}: {str(e)}")
        return {
            "error": f"Failed to list sources: {str(e)}",
            "documents": [],
            "agent_id": target_agent_id
        }

# Knowledge base management is handled within this aiagent directory
# To update the knowledge base, populate the query-engine-storage folder with your vector store files

def cleanup_temp_directories():
    """Clean up temporary directories on server shutdown."""
    global TEMP_KB_DIR
    if TEMP_KB_DIR and os.path.exists(TEMP_KB_DIR):
        try:
            shutil.rmtree(TEMP_KB_DIR)
            logger.info(f"🧹 Cleaned up temporary directory: {TEMP_KB_DIR}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup temp directory: {e}")

if __name__ == "__main__":
    logger.info(f"Starting Knowledge Base MCP Server for Agent {AGENT_ID}...")
    
    # Check initial status
    status = get_knowledge_base_status()
    logger.info(f"Knowledge base status: {status}")
    
    try:
        # Run the MCP server
        print("🔧 Starting Knowledge Base MCP Server...")
        # print(list_knowledge_sources(agent_id=93))
        mcp.run(transport="stdio")
    finally:
        # Cleanup on exit
        cleanup_temp_directories()
