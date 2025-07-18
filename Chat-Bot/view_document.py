#!/usr/bin/env python3
"""
Script to view specific documents from the query engine storage.
Prioritizes S3-based agent-specific knowledge bases over local storage.
Usage: python view_document.py [document_id]
"""

import sys
import json
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv


load_dotenv(override=True)

# Global configuration
AGENT_ID = "93"  # Change this to view different agent's knowledge base

# Check if boto3 is available for S3 operations
try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    print("⚠️ boto3 not available. Falling back to local storage only.")

# Local fallback directory
LOCAL_PERSIST_DIR = Path(__file__).parent / "query-engine-storage"

def get_s3_client():
    """Initialize and return S3 client."""
    try:
        return boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name='ap-south-1'  # Adjust region as needed
        )
    except Exception as e:
        print(f"❌ Failed to initialize S3 client: {e}")
        return None

def get_agent_s3_path(agent_id):
    """Get the S3 path for agent's knowledge base."""
    return f"workspace/agent/{agent_id}/query-engine-storage"

def download_s3_knowledge_base(agent_id):
    """Download agent-specific knowledge base from S3 to temporary directory."""
    if not S3_AVAILABLE:
        print("❌ S3 not available")
        return None, False
    
    s3_client = get_s3_client()
    if not s3_client:
        return None, False
    
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    if not bucket_name:
        print("❌ AWS_BUCKET_NAME environment variable not set")
        return None, False
    
    try:
        s3_path = get_agent_s3_path(agent_id)
        print(f"🔍 Looking for Agent {agent_id}'s knowledge base in S3: s3://{bucket_name}/{s3_path}")
        
        # List objects in the S3 path to check if knowledge base exists
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=s3_path + "/",
            MaxKeys=1
        )
        
        if 'Contents' not in response:
            print(f"⚠️ No knowledge base found in S3 for agent {agent_id}")
            return None, False
        
        print(f"✅ Found S3 knowledge base for agent {agent_id}")
        
        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp(prefix=f"kb_agent_{agent_id}_")
        
        # List all objects in the knowledge base
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
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
            s3_client.download_file(bucket_name, s3_key, local_file_path)
            downloaded_files += 1
        
        print(f"📥 Downloaded {downloaded_files} files from S3 to: {temp_dir}")
        return temp_dir, True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"❌ S3 bucket not found: {bucket_name}")
        elif error_code == 'AccessDenied':
            print("❌ Access denied to S3 bucket")
        else:
            print(f"❌ S3 client error: {e}")
        return None, False
    except Exception as e:
        print(f"❌ Error downloading knowledge base from S3: {e}")
        return None, False

def get_knowledge_base_path():
    """Get knowledge base path, prioritizing S3 over local storage."""
    print(f"🔧 Using Agent ID: {AGENT_ID}")
    
    # Try S3 first
    if S3_AVAILABLE:
        temp_dir, success = download_s3_knowledge_base(AGENT_ID)
        if success:
            print(f"✅ Using S3-based knowledge base for agent {AGENT_ID}")
            return Path(temp_dir)
    
    # Fallback to local storage
    if LOCAL_PERSIST_DIR.exists():
        print(f"⚠️ Falling back to local storage: {LOCAL_PERSIST_DIR}")
        return LOCAL_PERSIST_DIR
    else:
        print(f"❌ Local storage directory not found: {LOCAL_PERSIST_DIR}")
        return None

def list_documents():
    """List all document IDs with their basic info."""
    persist_dir = get_knowledge_base_path()
    if not persist_dir:
        print("❌ No knowledge base found (neither S3 nor local)")
        return
    
    try:
        docstore_path = persist_dir / "docstore.json"
        
        if not docstore_path.exists():
            print(f"❌ docstore.json not found in: {persist_dir}")
            return
        
        with open(docstore_path, 'r', encoding='utf-8') as f:
            docstore_data = json.load(f)
        
        if 'docstore/data' in docstore_data:
            docs = docstore_data['docstore/data']
            print(f"Found {len(docs)} documents in storage:\n")
            
            for i, (doc_id, doc_data) in enumerate(docs.items(), 1):
                # Get metadata
                metadata = None
                if isinstance(doc_data, dict):
                    if '__data__' in doc_data and 'metadata' in doc_data['__data__']:
                        metadata = doc_data['__data__']['metadata']
                    elif 'metadata' in doc_data:
                        metadata = doc_data['metadata']
                
                file_name = "Unknown"
                if metadata and 'file_name' in metadata:
                    file_name = metadata['file_name']
                
                print(f"{i:3d}. {doc_id} - {file_name}")
            
            print(f"\nTo view a specific document: python {sys.argv[0]} <document_id>")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up temporary directory if it was downloaded from S3
        if S3_AVAILABLE and persist_dir != LOCAL_PERSIST_DIR:
            try:
                import shutil
                shutil.rmtree(persist_dir)
                print(f"🧹 Cleaned up temporary directory: {persist_dir}")
            except Exception as e:
                print(f"⚠️ Failed to clean up temporary directory: {e}")

def view_document(doc_id):
    """View the full content of a specific document."""
    persist_dir = get_knowledge_base_path()
    if not persist_dir:
        print("❌ No knowledge base found (neither S3 nor local)")
        return
    
    try:
        docstore_path = persist_dir / "docstore.json"
        
        if not docstore_path.exists():
            print(f"❌ docstore.json not found in: {persist_dir}")
            return
        
        with open(docstore_path, 'r', encoding='utf-8') as f:
            docstore_data = json.load(f)
        
        if 'docstore/data' in docstore_data:
            docs = docstore_data['docstore/data']
            
            if doc_id in docs:
                doc_data = docs[doc_id]
                
                print("=" * 80)
                print(f"DOCUMENT: {doc_id}")
                print("=" * 80)
                
                # Get metadata
                metadata = None
                if isinstance(doc_data, dict):
                    if '__data__' in doc_data and 'metadata' in doc_data['__data__']:
                        metadata = doc_data['__data__']['metadata']
                    elif 'metadata' in doc_data:
                        metadata = doc_data['metadata']
                
                if metadata:
                    print("METADATA:")
                    for key, value in metadata.items():
                        print(f"  {key}: {value}")
                    print()
                
                # Get text content
                text_content = None
                if isinstance(doc_data, dict):
                    if '__data__' in doc_data and 'text' in doc_data['__data__']:
                        text_content = doc_data['__data__']['text']
                    elif 'text' in doc_data:
                        text_content = doc_data['text']
                    elif 'content' in doc_data:
                        text_content = doc_data['content']
                
                if text_content:
                    print("CONTENT:")
                    print("-" * 40)
                    print(text_content)
                    print("-" * 40)
                    print(f"Total characters: {len(text_content)}")
                else:
                    print("No text content found.")
                
                print("=" * 80)
            else:
                print(f"Document ID '{doc_id}' not found.")
                print("Use the script without arguments to see available document IDs.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up temporary directory if it was downloaded from S3
        if S3_AVAILABLE and persist_dir != LOCAL_PERSIST_DIR:
            try:
                import shutil
                shutil.rmtree(persist_dir)
                print(f"🧹 Cleaned up temporary directory: {persist_dir}")
            except Exception as e:
                print(f"⚠️ Failed to clean up temporary directory: {e}")

def main():
    if len(sys.argv) == 1:
        # No arguments - list all documents
        list_documents()
    elif len(sys.argv) == 2:
        # One argument - view specific document
        doc_id = sys.argv[1]
        view_document(doc_id)
    else:
        print("Usage:")
        print(f"  {sys.argv[0]}           - List all documents")
        print(f"  {sys.argv[0]} <doc_id>  - View specific document")

if __name__ == "__main__":
    main()
