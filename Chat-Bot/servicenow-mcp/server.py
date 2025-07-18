#!/usr/bin/env python3
"""
Standalone ServiceNow MCP Server

A simplified, self-contained MCP server for ServiceNow integration.
"""

import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# ServiceNow configuration
SERVICENOW_INSTANCE_URL = os.getenv("SERVICENOW_INSTANCE_URL")
SERVICENOW_USERNAME = os.getenv("SERVICENOW_USERNAME")
SERVICENOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD")
SERVICENOW_AUTH_TYPE = os.getenv("SERVICENOW_AUTH_TYPE", "basic")
SERVICENOW_DEBUG = os.getenv("SERVICENOW_DEBUG", "false").lower() == "true"
SERVICENOW_TIMEOUT = int(os.getenv("SERVICENOW_TIMEOUT", "30"))

# Initialize FastMCP server
mcp = FastMCP("ServiceNow")

class ServiceNowClient:
    """Simple ServiceNow API client."""
    
    def __init__(self):
        if not all([SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD]):
            raise ValueError("ServiceNow credentials not configured properly")
        
        self.base_url = f"{SERVICENOW_INSTANCE_URL}/api/now"
        self.auth = (SERVICENOW_USERNAME, SERVICENOW_PASSWORD)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to ServiceNow API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(
                url, 
                auth=self.auth, 
                headers=self.headers, 
                params=params,
                timeout=SERVICENOW_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"GET request failed: {e}")
            raise
    
    def post(self, endpoint: str, data: Dict) -> Dict:
        """Make POST request to ServiceNow API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(
                url,
                auth=self.auth,
                headers=self.headers,
                json=data,
                timeout=SERVICENOW_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"POST request failed: {e}")
            raise
    
    def put(self, endpoint: str, data: Dict) -> Dict:
        """Make PUT request to ServiceNow API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.put(
                url,
                auth=self.auth,
                headers=self.headers,
                json=data,
                timeout=SERVICENOW_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"PUT request failed: {e}")
            raise

# Initialize ServiceNow client
client = ServiceNowClient()

# Pydantic models for parameters
class CreateIncidentParams(BaseModel):
    short_description: str = Field(..., description="Short description of the incident")
    description: Optional[str] = Field(None, description="Detailed description of the incident")
    caller_id: Optional[str] = Field(None, description="User who reported the incident")
    category: Optional[str] = Field(None, description="Category of the incident")
    priority: Optional[str] = Field(None, description="Priority (1-5)")
    impact: Optional[str] = Field(None, description="Impact (1-3)")
    urgency: Optional[str] = Field(None, description="Urgency (1-3)")

class UpdateIncidentParams(BaseModel):
    incident_id: str = Field(..., description="Incident ID or sys_id")
    short_description: Optional[str] = Field(None, description="Short description")
    description: Optional[str] = Field(None, description="Detailed description")
    state: Optional[str] = Field(None, description="State (1-7)")
    work_notes: Optional[str] = Field(None, description="Work notes")
    close_notes: Optional[str] = Field(None, description="Close notes")

class ListIncidentsParams(BaseModel):
    limit: Optional[int] = Field(10, description="Number of incidents to return")
    state: Optional[str] = Field(None, description="Filter by state")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user")

class CreateChangeRequestParams(BaseModel):
    short_description: str = Field(..., description="Short description of the change")
    description: Optional[str] = Field(None, description="Detailed description")
    type: str = Field("normal", description="Type of change (normal, standard, emergency)")
    risk: Optional[str] = Field(None, description="Risk level")
    impact: Optional[str] = Field(None, description="Impact (1-3)")

class ListChangeRequestsParams(BaseModel):
    limit: Optional[int] = Field(10, description="Number of change requests to return")
    state: Optional[str] = Field(None, description="Filter by state")

class GetUserParams(BaseModel):
    user_id: str = Field(..., description="User ID, sys_id, or username")

class ListUsersParams(BaseModel):
    limit: Optional[int] = Field(10, description="Number of users to return")
    active: Optional[bool] = Field(True, description="Filter by active status")

# MCP Tools
@mcp.tool()
def create_incident(params: CreateIncidentParams) -> Dict[str, Any]:
    """Create a new incident in ServiceNow."""
    try:
        data = {
            "short_description": params.short_description,
            "description": params.description,
            "caller_id": params.caller_id,
            "category": params.category,
            "priority": params.priority,
            "impact": params.impact,
            "urgency": params.urgency
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        result = client.post("table/incident", data)
        return {"success": True, "incident": result["result"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def update_incident(params: UpdateIncidentParams) -> Dict[str, Any]:
    """Update an existing incident in ServiceNow."""
    try:
        data = {
            "short_description": params.short_description,
            "description": params.description,
            "state": params.state,
            "work_notes": params.work_notes,
            "close_notes": params.close_notes
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        result = client.put(f"table/incident/{params.incident_id}", data)
        return {"success": True, "incident": result["result"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def list_incidents(params: ListIncidentsParams) -> Dict[str, Any]:
    """List incidents from ServiceNow."""
    try:
        query_params = {
            "sysparm_limit": params.limit,
            "sysparm_fields": "sys_id,number,short_description,state,priority,assigned_to,caller_id,opened_at,updated_at"
        }
        
        filters = []
        if params.state:
            filters.append(f"state={params.state}")
        if params.assigned_to:
            filters.append(f"assigned_to={params.assigned_to}")
        
        if filters:
            query_params["sysparm_query"] = "^".join(filters)
        
        result = client.get("table/incident", query_params)
        return {"success": True, "incidents": result["result"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def create_change_request(params: CreateChangeRequestParams) -> Dict[str, Any]:
    """Create a new change request in ServiceNow."""
    try:
        data = {
            "short_description": params.short_description,
            "description": params.description,
            "type": params.type,
            "risk": params.risk,
            "impact": params.impact
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        result = client.post("table/change_request", data)
        return {"success": True, "change_request": result["result"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def list_change_requests(params: ListChangeRequestsParams) -> Dict[str, Any]:
    """List change requests from ServiceNow."""
    try:
        query_params = {
            "sysparm_limit": params.limit,
            "sysparm_fields": "sys_id,number,short_description,state,type,risk,impact,requested_by,opened_at"
        }
        
        if params.state:
            query_params["sysparm_query"] = f"state={params.state}"
        
        result = client.get("table/change_request", query_params)
        return {"success": True, "change_requests": result["result"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def get_user(params: GetUserParams) -> Dict[str, Any]:
    """Get user information from ServiceNow."""
    try:
        # Try to get user by sys_id first, then by user_name
        result = client.get(f"table/sys_user/{params.user_id}")
        if result.get("result"):
            return {"success": True, "user": result["result"]}
        
        # If not found by sys_id, try by user_name
        query_params = {
            "sysparm_query": f"user_name={params.user_id}",
            "sysparm_limit": 1
        }
        result = client.get("table/sys_user", query_params)
        
        if result.get("result") and len(result["result"]) > 0:
            return {"success": True, "user": result["result"][0]}
        else:
            return {"success": False, "error": "User not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def list_users(params: ListUsersParams) -> Dict[str, Any]:
    """List users from ServiceNow."""
    try:
        query_params = {
            "sysparm_limit": params.limit,
            "sysparm_fields": "sys_id,user_name,first_name,last_name,email,active,title,department"
        }
        
        if params.active is not None:
            query_params["sysparm_query"] = f"active={str(params.active).lower()}"
        
        result = client.get("table/sys_user", query_params)
        return {"success": True, "users": result["result"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def get_servicenow_config() -> Dict[str, Any]:
    """Get ServiceNow MCP server configuration."""
    return {
        "instance_url": SERVICENOW_INSTANCE_URL,
        "auth_type": SERVICENOW_AUTH_TYPE,
        "debug": SERVICENOW_DEBUG,
        "timeout": SERVICENOW_TIMEOUT,
        "username": SERVICENOW_USERNAME if SERVICENOW_USERNAME else "Not configured"
    }

def main():
    """Main entry point for the ServiceNow MCP server."""
    logger.info("Starting ServiceNow MCP server")
    
    # Validate configuration
    if not all([SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD]):
        logger.error("ServiceNow configuration incomplete. Please set SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, and SERVICENOW_PASSWORD")
        return
    
    # Run the server
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
