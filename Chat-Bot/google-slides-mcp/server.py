#!/usr/bin/env python3
import os
import json
import asyncio
import sys
from typing import Dict, Any, List
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load environment variables from .env file
load_dotenv()

# Environment variables for authentication
ACCESS_TOKEN = os.getenv("GSLIDES_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("GSLIDES_REFRESH_TOKEN")

def get_slides_service():
    """Initialize and return the Google Slides service."""
    # Check if we have the required tokens
    if not ACCESS_TOKEN or not REFRESH_TOKEN:
        print("Warning: GSLIDES_ACCESS_TOKEN and GSLIDES_REFRESH_TOKEN not set - using mock service", file=sys.stderr)
        return None
    
    try:
        # Create credentials using only access and refresh tokens
        credentials = Credentials(
            token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=['https://www.googleapis.com/auth/presentations']
        )
        return build("slides", "v1", credentials=credentials)
    except Exception as e:
        print(f"Warning: Failed to initialize Google Slides service: {e}", file=sys.stderr)
        return None

def create_presentation(title: str) -> Dict[str, Any]:
    """Create a new Google Slides presentation."""
    try:
        service = get_slides_service()
        if not service:
            return {"success": False, "error": "Google Slides service not available - please configure OAuth credentials"}
        
        presentation = service.presentations().create(
            body={"title": title}
        ).execute()
        return {"success": True, "data": presentation}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_presentation(presentation_id: str) -> Dict[str, Any]:
    """Get details about a Google Slides presentation."""
    try:
        service = get_slides_service()
        if not service:
            return {"success": False, "error": "Google Slides service not available - please configure OAuth credentials"}
        
        presentation = service.presentations().get(
            presentationId=presentation_id
        ).execute()
        return {"success": True, "data": presentation}
    except Exception as e:
        return {"success": False, "error": str(e)}

def batch_update_presentation(presentation_id: str, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply a batch of updates to a Google Slides presentation."""
    try:
        service = get_slides_service()
        if not service:
            return {"success": False, "error": "Google Slides service not available - please configure OAuth credentials"}
        
        response = service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()
        return {"success": True, "data": response}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_page(presentation_id: str, page_object_id: str) -> Dict[str, Any]:
    """Get details about a specific page (slide) in a presentation."""
    try:
        service = get_slides_service()
        if not service:
            return {"success": False, "error": "Google Slides service not available - please configure OAuth credentials"}
        
        presentation = service.presentations().get(
            presentationId=presentation_id
        ).execute()
        
        # Find the specific page
        page = next(
            (p for p in presentation.get("slides", []) if p.get("objectId") == page_object_id),
            None
        )
        
        if not page:
            return {"success": False, "error": f"Page with ID {page_object_id} not found"}
        
        return {"success": True, "data": page}
    except Exception as e:
        return {"success": False, "error": str(e)}

def summarize_presentation(presentation_id: str, include_notes: bool = False) -> Dict[str, Any]:
    """Extract text content from all slides in a presentation."""
    try:
        service = get_slides_service()
        if not service:
            return {"success": False, "error": "Google Slides service not available - please configure OAuth credentials"}
        
        presentation = service.presentations().get(
            presentationId=presentation_id
        ).execute()
        
        summary = {
            "title": presentation.get("title", "Untitled"),
            "slides": []
        }
        
        for slide in presentation.get("slides", []):
            slide_content = {
                "objectId": slide.get("objectId"),
                "text": []
            }
            
            # Extract text from text boxes and shapes
            for element in slide.get("pageElements", []):
                if "shape" in element and "text" in element["shape"]:
                    text_content = element["shape"]["text"].get("textElements", [])
                    for text_element in text_content:
                        if "textRun" in text_element:
                            slide_content["text"].append(text_element["textRun"].get("content", ""))
            
            # Include speaker notes if requested
            if include_notes and "slideProperties" in slide and "notesPage" in slide["slideProperties"]:
                notes_page = slide["slideProperties"]["notesPage"]
                if "pageElements" in notes_page:
                    for element in notes_page["pageElements"]:
                        if "shape" in element and "text" in element["shape"]:
                            text_content = element["shape"]["text"].get("textElements", [])
                            for text_element in text_content:
                                if "textRun" in text_element:
                                    slide_content["text"].append(
                                        f"[Speaker Note]: {text_element['textRun'].get('content', '')}"
                                    )
            
            summary["slides"].append(slide_content)
        
        return {"success": True, "data": summary}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP requests."""
    method = request.get("method")
    params = request.get("params", {})
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "google-slides-mcp",
                    "version": "0.1.0"
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "create_presentation",
                        "description": "Create a new Google Slides presentation",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "The title of the presentation."
                                }
                            },
                            "required": ["title"]
                        }
                    },
                    {
                        "name": "get_presentation",
                        "description": "Get details about a Google Slides presentation",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "presentationId": {
                                    "type": "string",
                                    "description": "The ID of the presentation to retrieve."
                                }
                            },
                            "required": ["presentationId"]
                        }
                    },
                    {
                        "name": "batch_update_presentation",
                        "description": "Apply a batch of updates to a Google Slides presentation",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "presentationId": {
                                    "type": "string",
                                    "description": "The ID of the presentation to update."
                                },
                                "requests": {
                                    "type": "array",
                                    "description": "A list of update requests to apply.",
                                    "items": {"type": "object"}
                                }
                            },
                            "required": ["presentationId", "requests"]
                        }
                    },
                    {
                        "name": "get_page",
                        "description": "Get details about a specific page (slide) in a presentation",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "presentationId": {
                                    "type": "string",
                                    "description": "The ID of the presentation."
                                },
                                "pageObjectId": {
                                    "type": "string",
                                    "description": "The object ID of the page (slide) to retrieve."
                                }
                            },
                            "required": ["presentationId", "pageObjectId"]
                        }
                    },
                    {
                        "name": "summarize_presentation",
                        "description": "Extract text content from all slides in a presentation",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "presentationId": {
                                    "type": "string",
                                    "description": "The ID of the presentation to summarize."
                                },
                                "include_notes": {
                                    "type": "boolean",
                                    "description": "Optional. Whether to include speaker notes in the summary."
                                }
                            },
                            "required": ["presentationId"]
                        }
                    }
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "create_presentation":
            result = create_presentation(arguments.get("title", "Untitled"))
        elif tool_name == "get_presentation":
            result = get_presentation(arguments.get("presentationId"))
        elif tool_name == "batch_update_presentation":
            result = batch_update_presentation(
                arguments.get("presentationId"),
                arguments.get("requests", [])
            )
        elif tool_name == "get_page":
            result = get_page(
                arguments.get("presentationId"),
                arguments.get("pageObjectId")
            )
        elif tool_name == "summarize_presentation":
            result = summarize_presentation(
                arguments.get("presentationId"),
                arguments.get("include_notes", False)
            )
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {tool_name}"
                }
            }
        
        if result["success"]:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result["data"], indent=2)
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32000,
                    "message": result["error"]
                }
            }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

def main():
    """Main function to run the MCP server."""
    # Check required environment variables
    if not all([ACCESS_TOKEN, REFRESH_TOKEN]):
        print("Warning: Missing Google OAuth tokens - server will run in mock mode", file=sys.stderr)
        print("To enable full functionality, set: GSLIDES_ACCESS_TOKEN, GSLIDES_REFRESH_TOKEN", file=sys.stderr)
    
    # Simple stdio-based MCP server
    while True:
        try:
            line = input()
            if not line.strip():
                continue
            
            request = json.loads(line)
            response = handle_mcp_request(request)
            print(json.dumps(response))
            
        except EOFError:
            break
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }))

if __name__ == "__main__":
    main() 