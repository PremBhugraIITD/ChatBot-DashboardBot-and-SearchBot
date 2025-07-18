import os
import json
from dotenv import load_dotenv
import logging

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Get the absolute path to the current directory (where this file is located)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Global agent context - to be set by mcp_client.py
_current_agent_id = None

# Global Gmail tokens - to be set by mcp_client.py (same pattern as agent_id)
_gmail_access_token = None
_gmail_refresh_token = None

# Global Google Sheets tokens - to be set by mcp_client.py 
_sheets_access_token = None
_sheets_refresh_token = None

# Global Google Docs tokens - to be set by mcp_client.py (same pattern as Gmail/Sheets)
_docs_access_token = None
_docs_refresh_token = None

# Global Google Calendar tokens - to be set by mcp_client.py (same pattern as Gmail/Sheets)
_calendar_access_token = None
_calendar_refresh_token = None

# Global WhatsApp Business tokens - to be set by mcp_client.py (same pattern as Gmail/Sheets)
_whatsapp_green_api_token = None
_whatsapp_green_api_instance_id = None

# Global YouTube and HeyGen API keys - to be set by mcp_client.py (same pattern as Gmail/Sheets)
_youtube_api_key = None
_heygen_api_key = None

# Global Airtable and Notion API keys - to be set by mcp_client.py (same pattern as Gmail/Sheets)
_airtable_api_key = None
_notion_api_key = None

# Global flags to track which special services are available for current agent
_gmail_available = False
_sheets_available = False
_docs_available = False
_calendar_available = False
_whatsapp_available = False
_playwright_available = False
_ocr_available = False
_captcha_solver_available = False
_youtube_available = False
_heygen_available = False
_airtable_available = False
_notion_available = False
_zendesk_available = False
_freshdesk_available = False
_salesforce_available = False
_pipedrive_available = False

# Global Asana access token - to be set by mcp_client.py
_asana_access_token = None

# Global Servicenow credentials - to be set by mcp_client.py
_servicenow_instance_url = None
_servicenow_username = None
_servicenow_password = None

# Global Zendesk credentials - to be set by mcp_client.py
_zendesk_email = None
_zendesk_api_key = None
_zendesk_subdomain = None

# Global Freshdesk credentials - to be set by mcp_client.py
_freshdesk_domain = None
_freshdesk_api_key = None

# Global Salesforce credentials - to be set by mcp_client.py
_salesforce_access_token = None
_salesforce_instance_url = None

# Global Pipedrive credentials - to be set by mcp_client.py
_pipedrive_api_token = None

def set_agent_context(agent_id):
    """Set the current agent ID for all MCP servers."""
    global _current_agent_id
    _current_agent_id = str(agent_id) if agent_id else None
    print(f"🔍 MCP Servers configuration loaded. Current agent ID: {_current_agent_id or 'None'}")

def set_gmail_context(gmail_tokens):
    """Set Gmail tokens for MCP server (same pattern as agent_id)."""
    global _gmail_access_token, _gmail_refresh_token, _gmail_available
    if gmail_tokens:
        _gmail_access_token = gmail_tokens.get("access_token")
        _gmail_refresh_token = gmail_tokens.get("refresh_token")
        _gmail_available = True
        print(f"🔑 Gmail tokens set for agent {_current_agent_id or 'Unknown'}")
    else:
        _gmail_access_token = None
        _gmail_refresh_token = None
        _gmail_available = False
        print(f"⚠️ No Gmail tokens available for agent {_current_agent_id or 'Unknown'}")

def set_sheets_context(sheets_tokens):
    """Set Google Sheets tokens for MCP server (same pattern as Gmail)."""
    global _sheets_access_token, _sheets_refresh_token, _sheets_available
    if sheets_tokens:
        _sheets_access_token = sheets_tokens.get("access_token")
        _sheets_refresh_token = sheets_tokens.get("refresh_token")
        _sheets_available = True
        print(f"🔑 Google Sheets tokens set for agent {_current_agent_id or 'Unknown'}")
    else:
        _sheets_access_token = None
        _sheets_refresh_token = None
        _sheets_available = False
        print(f"⚠️ No Google Sheets tokens available for agent {_current_agent_id or 'Unknown'}")

def set_docs_context(docs_tokens):
    """Set Google Docs tokens for MCP server (same pattern as Gmail/Sheets)."""
    global _docs_access_token, _docs_refresh_token, _docs_available
    if docs_tokens:
        _docs_access_token = docs_tokens.get("access_token")
        _docs_refresh_token = docs_tokens.get("refresh_token")
        _docs_available = True
        print(f"🔑 Google Docs tokens set for agent {_current_agent_id or 'Unknown'}")
    else:
        _docs_access_token = None
        _docs_refresh_token = None
        _docs_available = False
        print(f"⚠️ No Google Docs tokens available for agent {_current_agent_id or 'Unknown'}")

def set_calendar_context(calendar_tokens):
    """Set Google Calendar tokens for MCP server (same pattern as Gmail/Sheets)."""
    global _calendar_access_token, _calendar_refresh_token, _calendar_available
    if calendar_tokens:
        _calendar_access_token = calendar_tokens.get("access_token")
        _calendar_refresh_token = calendar_tokens.get("refresh_token")
        _calendar_available = True
        print(f"🔑 Google Calendar tokens set for agent {_current_agent_id or 'Unknown'}")
    else:
        _calendar_access_token = None
        _calendar_refresh_token = None
        _calendar_available = False
        print(f"⚠️ No Google Calendar tokens available for agent {_current_agent_id or 'Unknown'}")

def set_whatsapp_context(whatsapp_tokens):
    """Set WhatsApp Business tokens for MCP server (same pattern as Gmail/Sheets)."""
    global _whatsapp_green_api_token, _whatsapp_green_api_instance_id, _whatsapp_available
    if whatsapp_tokens:
        _whatsapp_green_api_token = whatsapp_tokens.get("green_api_token")
        _whatsapp_green_api_instance_id = whatsapp_tokens.get("green_api_instance_id")
        _whatsapp_available = True
        print(f"📱 WhatsApp Business tokens set for agent {_current_agent_id or 'Unknown'}")
    else:
        _whatsapp_green_api_token = None
        _whatsapp_green_api_instance_id = None
        _whatsapp_available = False
        print(f"⚠️ No WhatsApp Business tokens available for agent {_current_agent_id or 'Unknown'}")

def set_playwright_context(playwright_enabled):
    """Set Playwright availability for MCP server (same pattern as other special servers)."""
    global _playwright_available
    if playwright_enabled:
        _playwright_available = True
        print(f"🎭 Playwright enabled for agent {_current_agent_id or 'Unknown'}")
    else:
        _playwright_available = False
        print(f"⚠️ Playwright not available for agent {_current_agent_id or 'Unknown'}")

def set_ocr_context(ocr_enabled):
    """Set OCR availability for MCP server (same pattern as other special servers)."""
    global _ocr_available
    if ocr_enabled:
        _ocr_available = True
        print(f"👁️ OCR enabled for agent {_current_agent_id or 'Unknown'}")
    else:
        _ocr_available = False
        print(f"⚠️ OCR not available for agent {_current_agent_id or 'Unknown'}")

def set_captcha_solver_context(captcha_solver_enabled):
    """Set CAPTCHA solver availability for MCP server (same pattern as other special servers)."""
    global _captcha_solver_available
    if captcha_solver_enabled:
        _captcha_solver_available = True
        print(f"🔐 CAPTCHA solver enabled for agent {_current_agent_id or 'Unknown'}")
    else:
        _captcha_solver_available = False
        print(f"⚠️ CAPTCHA solver not available for agent {_current_agent_id or 'Unknown'}")

def set_youtube_context(youtube_data):
    """Set YouTube API key for MCP server (same pattern as Gmail/Sheets but for API key)."""
    global _youtube_api_key, _youtube_available
    if youtube_data:
        _youtube_api_key = youtube_data.get("api_key")
        _youtube_available = True
        print(f"📺 YouTube API key set for agent {_current_agent_id or 'Unknown'}")
    else:
        _youtube_api_key = None
        _youtube_available = False
        print(f"⚠️ No YouTube API key available for agent {_current_agent_id or 'Unknown'}")

def set_heygen_context(heygen_data):
    """Set HeyGen API key for MCP server (same pattern as Gmail/Sheets but for API key)."""
    global _heygen_api_key, _heygen_available
    if heygen_data:
        _heygen_api_key = heygen_data.get("api_key")
        _heygen_available = True
        print(f"🎬 HeyGen API key set for agent {_current_agent_id or 'Unknown'}")
    else:
        _heygen_api_key = None
        _heygen_available = False
        print(f"⚠️ No HeyGen API key available for agent {_current_agent_id or 'Unknown'}")

def set_airtable_context(airtable_data):
    """Set Airtable API key for MCP server (same pattern as Gmail/Sheets but for API key)."""
    global _airtable_api_key, _airtable_available
    if airtable_data:
        _airtable_api_key = airtable_data.get("api_key")
        _airtable_available = True
        print(f"📊 Airtable API key set for agent {_current_agent_id or 'Unknown'}")
    else:
        _airtable_api_key = None
        _airtable_available = False
        print(f"⚠️ No Airtable API key available for agent {_current_agent_id or 'Unknown'}")

def set_notion_context(notion_data):
    """Set Notion API key for MCP server (same pattern as Gmail/Sheets but for API key)."""
    global _notion_api_key, _notion_available
    if notion_data:
        _notion_api_key = notion_data.get("api_key")
        _notion_available = True
        print(f"📝 Notion API key set for agent {_current_agent_id or 'Unknown'}")
    else:
        _notion_api_key = None
        _notion_available = False
        print(f"⚠️ No Notion API key available for agent {_current_agent_id or 'Unknown'}")

def set_subagents_context(subagents_data):
    """Set sub-agents mapping for delegation by writing to middle.json."""
    try:
        if subagents_data and len(subagents_data) > 0:
            mapping = {
                str(subagent["id"]): {  # Convert ID to string explicitly
                    "token": subagent["token"],
                    "name": subagent["name"],
                    "tools": subagent["tools"]
                }
                for subagent in subagents_data
            }
            # Write to middle.json
            with open(os.path.join(CURRENT_DIR, "middle.json"), "w") as f:
                json.dump({"subagents_mapping": mapping}, f, indent=2)
            print(f"🎯 Sub-agents mapping saved to middle.json for agent {_current_agent_id or 'Unknown'}: {len(mapping)} sub-agents")
            logger.info(f"🎯 Sub-agents mapping saved to middle.json for agent {_current_agent_id or 'Unknown'}: {len(mapping)} sub-agents")
            # Debug: Log the actual IDs being set
            sub_agent_ids = list(mapping.keys())
            print(f"🔍 Debug: Sub-agent IDs in mapping: {sub_agent_ids}")
            for subagent_id, info in mapping.items():
                token_preview = info["token"][:20] if info["token"] else "No token"
                print(f"🔍 Debug: Sub-agent {subagent_id} ({info['name']}) - Token preview: {token_preview}...")
        else:
            # If no sub-agents, clear the middle.json file to ensure subagents server doesn't load
            try:
                middle_json_path = os.path.join(CURRENT_DIR, "middle.json")
                if os.path.exists(middle_json_path):
                    os.remove(middle_json_path)
                    print(f"🧹 Cleared middle.json file - no subagents for agent {_current_agent_id or 'Unknown'}")
                else:
                    print(f"✅ No middle.json file to clear for agent {_current_agent_id or 'Unknown'}")
            except Exception as clear_error:
                logger.warning(f"⚠️ Could not clear middle.json file: {clear_error}")
            
            print(f"⚠️ No sub-agents data provided for agent {_current_agent_id or 'Unknown'}")
            print(f"🔍 Debug: subagents_data = {subagents_data}")
    except Exception as e:
        logger.error(f"❌ Error in set_subagents_context: {str(e)}")

def get_subagents_mapping():
    """Get the current sub-agents mapping from middle.json."""
    try:
        with open(os.path.join(CURRENT_DIR, "middle.json"), "r") as f:
            content = f.read().strip()  # Remove any trailing whitespace/characters
            data = json.loads(content)  # Use loads instead of load
            mapping = data.get("subagents_mapping", {})
            logger.info(f"🔍 Debug: Loaded sub-agents mapping from middle.json = {mapping}")
            return mapping
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"⚠️ Error reading middle.json: {e}")
        return {}

def set_asana_context(asana_data):
    """Set Asana access token for MCP server (from API response)."""
    global _asana_access_token, _asana_available
    if asana_data and asana_data.get("ASANA_ACCESS_TOKEN"):
        _asana_access_token = asana_data["ASANA_ACCESS_TOKEN"]
        _asana_available = True
        print(f"\u2705 Asana access token set for agent {_current_agent_id or 'Unknown'}")
    else:
        _asana_access_token = None
        _asana_available = False
        print(f"\u26a0\ufe0f No Asana access token available for agent {_current_agent_id or 'Unknown'}")


def set_servicenow_context(servicenow_data):
    """Set Servicenow credentials for MCP server (from API response)."""
    global _servicenow_instance_url, _servicenow_username, _servicenow_password, _servicenow_available
    if servicenow_data and all(k in servicenow_data for k in ("SERVICENOW_INSTANCE_URL", "SERVICENOW_USERNAME", "SERVICENOW_PASSWORD")):
        _servicenow_instance_url = servicenow_data["SERVICENOW_INSTANCE_URL"]
        _servicenow_username = servicenow_data["SERVICENOW_USERNAME"]
        _servicenow_password = servicenow_data["SERVICENOW_PASSWORD"]
        _servicenow_available = True
        print(f"\u2705 Servicenow credentials set for agent {_current_agent_id or 'Unknown'}")
    else:
        _servicenow_instance_url = None
        _servicenow_username = None
        _servicenow_password = None
        _servicenow_available = False
        print(f"\u26a0\ufe0f No Servicenow credentials available for agent {_current_agent_id or 'Unknown'}")

def set_zendesk_context(zendesk_data):
    """Set Zendesk credentials for MCP server (from API response)."""
    global _zendesk_email, _zendesk_api_key, _zendesk_subdomain, _zendesk_available
    if zendesk_data and all(k in zendesk_data for k in ("ZENDESK_EMAIL", "ZENDESK_API_KEY", "ZENDESK_SUBDOMAIN")):
        _zendesk_email = zendesk_data["ZENDESK_EMAIL"]
        _zendesk_api_key = zendesk_data["ZENDESK_API_KEY"]
        _zendesk_subdomain = zendesk_data["ZENDESK_SUBDOMAIN"]
        _zendesk_available = True
        print(f"\u2705 Zendesk credentials set for agent {_current_agent_id or 'Unknown'}")
    else:
        _zendesk_email = None
        _zendesk_api_key = None
        _zendesk_subdomain = None
        _zendesk_available = False
        print(f"\u26a0\ufe0f No Zendesk credentials available for agent {_current_agent_id or 'Unknown'}")

def set_freshdesk_context(freshdesk_data):
    """Set Freshdesk credentials for MCP server (from API response)."""
    global _freshdesk_domain, _freshdesk_api_key, _freshdesk_available
    if freshdesk_data and all(k in freshdesk_data for k in ("FRESHDESK_DOMAIN", "FRESHDESK_API_KEY")):
        _freshdesk_domain = freshdesk_data["FRESHDESK_DOMAIN"]
        _freshdesk_api_key = freshdesk_data["FRESHDESK_API_KEY"]
        _freshdesk_available = True
        print(f"\u2705 Freshdesk credentials set for agent {_current_agent_id or 'Unknown'}")
    else:
        _freshdesk_domain = None
        _freshdesk_api_key = None
        _freshdesk_available = False
        print(f"\u26a0\ufe0f No Freshdesk credentials available for agent {_current_agent_id or 'Unknown'}")

def set_salesforce_context(salesforce_data):
    """Set Salesforce credentials for MCP server (from API response)."""
    global _salesforce_access_token, _salesforce_instance_url, _salesforce_available
    if salesforce_data and all(k in salesforce_data for k in ("SALESFORCE_ACCESS_TOKEN", "SALESFORCE_INSTANCE_URL")):
        _salesforce_access_token = salesforce_data["SALESFORCE_ACCESS_TOKEN"]
        _salesforce_instance_url = salesforce_data["SALESFORCE_INSTANCE_URL"]
        _salesforce_available = True
        print(f"\u2705 Salesforce credentials set for agent {_current_agent_id or 'Unknown'}")
    else:
        _salesforce_access_token = None
        _salesforce_instance_url = None
        _salesforce_available = False
        print(f"\u26a0\ufe0f No Salesforce credentials available for agent {_current_agent_id or 'Unknown'}")

def set_pipedrive_context(pipedrive_data):
    """Set Pipedrive credentials for MCP server (from API response)."""
    global _pipedrive_api_token, _pipedrive_available
    if pipedrive_data and pipedrive_data.get("PIPEDRIVE_API_TOKEN"):
        _pipedrive_api_token = pipedrive_data["PIPEDRIVE_API_TOKEN"]
        _pipedrive_available = True
        print(f"\u2705 Pipedrive credentials set for agent {_current_agent_id or 'Unknown'}")
    else:
        _pipedrive_api_token = None
        _pipedrive_available = False
        print(f"\u26a0\ufe0f No Pipedrive credentials available for agent {_current_agent_id or 'Unknown'}")

def get_standard_mcp_servers():
    """Get standard MCP servers that are always loaded regardless of agent configuration."""
    servers = [
        {
            "id": "math",
            "command": "python3",
            "args": [os.path.join(CURRENT_DIR, "math_server.py")],
            "env": {},
        },
        # {
        #     "id": "google-ads",
        #     "command": "python3",
        #     "args": [os.path.join(CURRENT_DIR, "mcp-google-ads", "google_ads_server.py")],
        #     "env": {
        #         "GADS_ACCESS_TOKEN": os.getenv("GADS_ACCESS_TOKEN"),
        #         "GADS_REFRESH_TOKEN": os.getenv("GADS_REFRESH_TOKEN"),
        #         "GOOGLE_ADS_DEVELOPER_TOKEN": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        #     },
        # },
        # {
        #     "id": "google-slides",
        #     "command": "python",
        #     "args": [os.path.join(CURRENT_DIR, "google-slides-mcp", "server.py")],
        #     "env": {
        #         "GSLIDES_ACCESS_TOKEN": os.getenv("GSLIDES_ACCESS_TOKEN"),
        #         "GSLIDES_REFRESH_TOKEN": os.getenv("GSLIDES_REFRESH_TOKEN"),
        #     },
        # },
        # {
        #     "id": "knowledge-base",
        #     "command": "python",
        #     "args": [os.path.join(CURRENT_DIR, "knowledge_base_server.py")],
        #     "env": {
        #         "AGENT_ID": _current_agent_id or "default",
        #         "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        #         "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
        #         "AWS_BUCKET_NAME": os.getenv("AWS_BUCKET_NAME"),
        #     },
        # },
        # {
        #     "id": "instantly",
        #     "command": "node",
        #     "args": [
        #         os.path.join(CURRENT_DIR, "Instantly-MCP", "dist", "index.js"),
        #         "--api-key",
        #         os.getenv("INSTANTLY_API_KEY")
        #     ],
        #     "env": {
        #         "NODE_ENV": os.getenv("NODE_ENV", "production"),
        #     },
        # },
        # {
        #     "id": "wordpress-local",
        #     "command": "node",
        #     "args": ["/usr/local/lib/node_modules/@automattic/mcp-wordpress-remote/dist/proxy.js"],
        #     "env": {
        #         "WP_API_URL": os.getenv("WP_API_URL"),
        #         "JWT_TOKEN": os.getenv("WORDPRESS_JWT_TOKEN"),
        #         "LOG_FILE": os.getenv("WORDPRESS_LOG_FILE", ""),
        #     },
        # },
        # {
        #     "id": "quickbooks-time",
        #     "command": "python",
        #     "args": [os.path.join(CURRENT_DIR, "quickbooks-time-mcp-server", "main.py")],
        #     "env": {
        #         "QB_TIME_ACCESS_TOKEN": os.getenv("QB_TIME_ACCESS_TOKEN"),
        #         "NODE_ENV": os.getenv("NODE_ENV", "development"),
        #     },
        # },
        # {
        #     "id": "teams",
        #     "command": "python",
        #     "args": [os.path.join(CURRENT_DIR, "mcp-teams-server", "__main__.py")],
        #     "env": {
        #         "PYTHONPATH": os.path.join(CURRENT_DIR, "mcp-teams-server"),
        #         "TEAMS_APP_ID": os.getenv("TEAMS_APP_ID"),
        #         "TEAMS_APP_PASSWORD": os.getenv("TEAMS_APP_PASSWORD"),
        #         "TEAMS_APP_TYPE": os.getenv("TEAMS_APP_TYPE", "SingleTenant"),
        #         "TEAMS_APP_TENANT_ID": os.getenv("TEAMS_APP_TENANT_ID"),
        #         "TEAM_ID": os.getenv("TEAM_ID"),
        #         "TEAMS_CHANNEL_ID": os.getenv("TEAMS_CHANNEL_ID"),
        #     },
        # },
        # {
        #     "id": "calendly",
        #     "command": "python3",
        #     "args": [os.path.join(CURRENT_DIR, "calendly-mcp", "server.py")],
        #     "env": {
        #         "CALENDLY_ACCESS_TOKEN": os.getenv("CALENDLY_ACCESS_TOKEN"),
        #         "AGENTR_API_KEY": os.getenv("AGENTR_API_KEY"),
        #         "AGENTR_BASE_URL": os.getenv("AGENTR_BASE_URL"),
        #     },
        # },
        # {
        #     "id": "intercom",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "mcp-server-for-intercom", "build", "index.js")],
        #     "env": {
        #         "INTERCOM_ACCESS_TOKEN": os.getenv("INTERCOM_ACCESS_TOKEN"),
        #     },
        # },
        # {
        #     "id": "clickup",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "clickup-mcp-server", "build", "index.js")],
        #     "env": {
        #         "CLICKUP_API_TOKEN": os.getenv("CLICKUP_API_TOKEN"),
        #     },
        # },
        # {
        #     "id": "zoho-books",
        #     "command": "python",
        #     "args": [os.path.join(CURRENT_DIR, "zoho-books-mcp", "mcp_server.py")],
        #     "env": {
        #         "ZOHO_CLIENT_ID": os.getenv("ZOHO_CLIENT_ID"),
        #         "ZOHO_CLIENT_SECRET": os.getenv("ZOHO_CLIENT_SECRET"),
        #         "ZOHO_REFRESH_TOKEN": os.getenv("ZOHO_REFRESH_TOKEN"),
        #         "ZOHO_ORGANIZATION_ID": os.getenv("ZOHO_ORGANIZATION_ID"),
        #         "ZOHO_REGION": os.getenv("ZOHO_REGION", "US"),
        #     },
        # },
        # {
        #     "id": "trello",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "mcp-server-trello", "build", "index.js")],
        #     "env": {
        #         "TRELLO_API_KEY": os.getenv("TRELLO_API_KEY"),
        #         "TRELLO_TOKEN": os.getenv("TRELLO_TOKEN"),
        #         "TRELLO_BOARD_ID": os.getenv("TRELLO_BOARD_ID"),
        #     },
        # },
        # {
        #     "id": "monday",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "mcp-monday", "monday-api-mcp", "dist", "index.js")],
        #     "env": {
        #         "MONDAY_TOKEN": os.getenv("MONDAY_TOKEN"),
        #     },
        # },
        # {
        #     "id": "google-maps",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "mcp-google-map", "dist", "index.cjs")],
        #     "env": {
        #         "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY"),
        #     },
        # },
        # {
        #     "id": "google-meet",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "google-meet-mcp-server", "src", "index.js")],
        #     "env": {
        #         "GOOGLE_MEET_ACCESS_TOKEN": os.getenv("GOOGLE_MEET_ACCESS_TOKEN"),
        #         "GOOGLE_MEET_REFRESH_TOKEN": os.getenv("GOOGLE_MEET_REFRESH_TOKEN"),
        #     },
        # },
        # {
        #     "id": "zoom",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "zoom-mcp-server", "dist", "index.js")],
        #     "env": {
        #         "ZOOM_ACCOUNT_ID": os.getenv("ZOOM_ACCOUNT_ID"),
        #         "ZOOM_CLIENT_ID": os.getenv("ZOOM_CLIENT_ID"),
        #         "ZOOM_CLIENT_SECRET": os.getenv("ZOOM_CLIENT_SECRET"),
        #     },
        # },
        # {
        #     "id": "whatsapp",
        #     "command": "python",
        #     "args": [os.path.join(CURRENT_DIR, "whatsapp-mcp", "whatsapp-mcp-server", "main.py")],
        #     "env": {},
        # },
        # {
        #     "id": "bigquery",
        #     "command": "node",
        #     "args": [
        #         os.path.join(CURRENT_DIR, "mcp-bigquery-server", "dist", "index.js"),
        #         "--project-id",
        #         os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        #     ],
        #     "env": {
        #         "BIGQUERY_ACCESS_TOKEN": os.getenv("BIGQUERY_ACCESS_TOKEN"),
        #         "BIGQUERY_REFRESH_TOKEN": os.getenv("BIGQUERY_REFRESH_TOKEN"),
        #     },
        # },
        # {
        #     "id": "jira",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "jira-mcp-server", "build", "index.js")],
        #     "env": {
        #         "JIRA_URL": os.getenv("JIRA_URL"),
        #         "JIRA_API_MAIL": os.getenv("JIRA_API_MAIL"),
        #         "JIRA_API_KEY": os.getenv("JIRA_API_KEY"),
        #     },
        # },
        # {
        #     "id": "hubspot",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "hubspot-mcp-server", "dist", "index.js")],
        #     "env": {
        #         "HUBSPOT_ACCESS_TOKEN": os.getenv("HUBSPOT_ACCESS_TOKEN"),
        #     },
        # },
        # {
        #     "id": "clay",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "clay-mcp", "index.js")],
        #     "env": {
        #         "CLAY_API_KEY": os.getenv("CLAY_API_KEY"),
        #     },
        # },
        # {
        #     "id": "sendgrid",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "sendgrid-mcp", "build", "index.js")],
        #     "env": {
        #         "SENDGRID_API_KEY": os.getenv("SENDGRID_API_KEY"),
        #     },
        # },
        # {
        #     "id": "elevenlabs",
        #     "command": "python3",
        #     "args": [os.path.join(CURRENT_DIR, "elevenlabs-mcp", "server.py")],
        #     "env": {
        #         "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
        #     },
        # },
        # {
        #     "id": "smallest-ai",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "MCP-smallest-ai", "dist", "index.js")],
        #     "env": {
        #         "SMALLEST_AI_API_KEY": os.getenv("SMALLEST_AI_API_KEY"),
        #     },
        # },
        # {
        #     "id": "slack",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "slack-mcp-server", "dist", "index.js")],
        #     "env": {
        #         "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
        #         "SLACK_TEAM_ID": os.getenv("SLACK_TEAM_ID"),
        #     },
        # },
        # {
        #     "id": "apollo-io",
        #     "command": "node",
        #     "args": [os.path.join(CURRENT_DIR, "apollo-io-mcp-server", "dist", "index.js")],
        #     "env": {
        #         "APOLLO_IO_API_KEY": os.getenv("APOLLO_IO_API_KEY"),
        #     },
        # },
    ]
    return servers

def get_special_mcp_servers():
    """Get special MCP servers that are conditionally loaded based on agent configuration."""
    special_servers = []
    
    # Gmail MCP server - only load if Gmail is available for this agent
    if _gmail_available:
        special_servers.append({
            "id": "gmail",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "google-workspace-mcp-server", "build", "index.js")],
            "env": {
                "GMAIL_ACCESS_TOKEN": _gmail_access_token or "",
                "GMAIL_REFRESH_TOKEN": _gmail_refresh_token or "",
            },
        })
        print(f"✅ Gmail MCP server will be loaded for agent {_current_agent_id}")
    
        # Google Sheets MCP server - only load if Sheets is available for this agent
    if _sheets_available:
        special_servers.append({
            "id": "google-sheets",
            "command": "python",
            "args": [os.path.join(CURRENT_DIR, "mcp-google-sheets", "server.py")],
            "env": {
                "GSHEETS_ACCESS_TOKEN": _sheets_access_token or "",
                "GSHEETS_REFRESH_TOKEN": _sheets_refresh_token or "",
            },
        })
        print(f"✅ Google Sheets MCP server will be loaded for agent {_current_agent_id}")

    # Google Docs MCP server - only load if Docs is available for this agent
    if _docs_available:
        special_servers.append({
            "id": "google-docs",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "google-docs-mcp", "dist", "server.js")],
            "env": {
                "GDOCS_ACCESS_TOKEN": _docs_access_token or "",
                "GDOCS_REFRESH_TOKEN": _docs_refresh_token or "",
            },
        })
        print(f"✅ Google Docs MCP server will be loaded for agent {_current_agent_id}")

    # Google Calendar MCP server - only load if Calendar is available for this agent
    if _calendar_available:
        special_servers.append({
            "id": "google-calendar",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "google-calendar-mcp", "build", "index.js")],
            "env": {
                "GCALENDAR_ACCESS_TOKEN": _calendar_access_token or "",
                "GCALENDAR_REFRESH_TOKEN": _calendar_refresh_token or "",
            },
        })
        print(f"✅ Google Calendar MCP server will be loaded for agent {_current_agent_id}")

    # WhatsApp Business MCP server - only load if WhatsApp is available for this agent
    if _whatsapp_available:
        special_servers.append({
            "id": "whatsapp-business",
            "command": "python3",
            "args": [os.path.join(CURRENT_DIR, "whatsapp-mcp-server", "main.py")],
            "env": {
                "GREENAPI_ID_INSTANCE": _whatsapp_green_api_instance_id or "",
                "GREENAPI_API_TOKEN": _whatsapp_green_api_token or "",
            },
        })
        print(f"✅ WhatsApp Business MCP server will be loaded for agent {_current_agent_id}")
    
    # Playwright MCP server - only load if Playwright is available for this agent
    if _playwright_available:
        special_servers.append({
            "id": "playwright",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "mcp-playwright", "dist", "index.js")],
            "env": {},
        })
        print(f"✅ Playwright MCP server will be loaded for agent {_current_agent_id}")
    
    # OpenAI OCR MCP server - only load if OCR is available for this agent
    if _ocr_available:
        special_servers.append({
            "id": "openai-ocr",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "openai-ocr-mcp", "dist", "ocr.js")],
            "env": {
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            },
        })
        print(f"✅ OpenAI OCR MCP server will be loaded for agent {_current_agent_id}")
    
    # CAPTCHA solver MCP server - only load if CAPTCHA solver is available for this agent
    if _captcha_solver_available:
        special_servers.append({
            "id": "captcha-solver",
            "command": "python",
            "args": [os.path.join(CURRENT_DIR, "captcha-solver-mcp", "server.py")],
            "env": {
                "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            },
        })
        print(f"✅ CAPTCHA solver MCP server will be loaded for agent {_current_agent_id}")
    
    # YouTube MCP server - only load if YouTube is available for this agent
    if _youtube_available:
        special_servers.append({
            "id": "youtube",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "youtube-mcp-server", "dist", "index.js")],
            "env": {
                "YOUTUBE_API_KEY": _youtube_api_key or "",
            },
        })
        print(f"✅ YouTube MCP server will be loaded for agent {_current_agent_id}")
    
    # HeyGen MCP server - only load if HeyGen is available for this agent
    if _heygen_available:
        special_servers.append({
            "id": "heygen",
            "command": "python",
            "args": [os.path.join(CURRENT_DIR, "heygen-mcp", "server.py")],
            "env": {
                "HEYGEN_API_KEY": _heygen_api_key or "",
            },
        })
        print(f"✅ HeyGen MCP server will be loaded for agent {_current_agent_id}")
    
    # Airtable MCP server - only load if Airtable is available for this agent
    if _airtable_available:
        special_servers.append({
            "id": "airtable",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "airtable-mcp", "build", "index.js")],
            "env": {
                "AIRTABLE_API_KEY": _airtable_api_key or "",
            },
        })
        print(f"✅ Airtable MCP server will be loaded for agent {_current_agent_id}")
    
    # Notion MCP server - only load if Notion is available for this agent
    if _notion_available:
        special_servers.append({
            "id": "notion",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "notion-server", "build", "index.js")],
            "env": {
                "NOTION_API_KEY": _notion_api_key or "",
            },
        })
        print(f"✅ Notion MCP server will be loaded for agent {_current_agent_id}")
    
    # Sub-agents server - only load if we have sub-agents data in middle.json
    try:
        with open(os.path.join(CURRENT_DIR, "middle.json"), "r") as f:
            data = json.load(f)
            subagents_mapping = data.get("subagents_mapping", {})
            if subagents_mapping:
                special_servers.append({
                    "id": "subagents",
                    "command": "python3",
                    "args": [os.path.join(CURRENT_DIR, "subagents_server.py")],
                    "env": {},
                })
                print(f"✅ Sub-agents MCP server will be loaded for agent {_current_agent_id}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"⚠️ Could not read middle.json for sub-agents check: {e}")
    
    # Asana MCP server - only load if Asana is available for this agent
    if '_asana_available' in globals() and _asana_available:
        special_servers.append({
            "id": "asana",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "mcp-server-asana", "dist", "index.js")],
            "env": {
                "ASANA_ACCESS_TOKEN": _asana_access_token or "",
            },
        })
        print(f"\u2705 Asana MCP server will be loaded for agent {_current_agent_id}")
    # Servicenow MCP server - only load if Servicenow is available for this agent
    if '_servicenow_available' in globals() and _servicenow_available:
        special_servers.append({
            "id": "servicenow",
            "command": "python",
            "args": [os.path.join(CURRENT_DIR, "servicenow-mcp", "server.py")],
            "env": {
                "SERVICENOW_INSTANCE_URL": _servicenow_instance_url or "",
                "SERVICENOW_USERNAME": _servicenow_username or "",
                "SERVICENOW_PASSWORD": _servicenow_password or "",
                "SERVICENOW_AUTH_TYPE": "basic",
            },
        })
        print(f"\u2705 Servicenow MCP server will be loaded for agent {_current_agent_id}")
    
    # Zendesk MCP server - only load if Zendesk is available for this agent
    if '_zendesk_available' in globals() and _zendesk_available:
        special_servers.append({
            "id": "zendesk",
            "command": "python",
            "args": [os.path.join(CURRENT_DIR, "zendesk-mcp-server", "server.py")],
            "env": {
                "ZENDESK_EMAIL": _zendesk_email or "",
                "ZENDESK_API_KEY": _zendesk_api_key or "",
                "ZENDESK_SUBDOMAIN": _zendesk_subdomain or "",
            },
        })
        print(f"\u2705 Zendesk MCP server will be loaded for agent {_current_agent_id}")
    # Freshdesk MCP server - only load if Freshdesk is available for this agent
    if '_freshdesk_available' in globals() and _freshdesk_available:
        special_servers.append({
            "id": "freshdesk",
            "command": "python",
            "args": [os.path.join(CURRENT_DIR, "freshdesk_mcp", "server.py")],
            "env": {
                "FRESHDESK_DOMAIN": _freshdesk_domain or "",
                "FRESHDESK_API_KEY": _freshdesk_api_key or "",
            },
        })
        print(f"\u2705 Freshdesk MCP server will be loaded for agent {_current_agent_id}")
    
    # Salesforce MCP server - only load if Salesforce is available for this agent
    if '_salesforce_available' in globals() and _salesforce_available:
        special_servers.append({
            "id": "salesforce",
            "command": "python",
            "args": [os.path.join(CURRENT_DIR, "MCP-Salesforce", "server.py")],
            "env": {
                "SALESFORCE_ACCESS_TOKEN": _salesforce_access_token or "",
                "SALESFORCE_INSTANCE_URL": _salesforce_instance_url or "",
            },
        })
        print(f"\u2705 Salesforce MCP server will be loaded for agent {_current_agent_id}")
    # Pipedrive MCP server - only load if Pipedrive is available for this agent
    if '_pipedrive_available' in globals() and _pipedrive_available:
        special_servers.append({
            "id": "pipedrive",
            "command": "node",
            "args": [os.path.join(CURRENT_DIR, "pipedrive-mcp-server", "build", "index.js")],
            "env": {
                "PIPEDRIVE_API_TOKEN": _pipedrive_api_token or "",
            },
        })
        print(f"\u2705 Pipedrive MCP server will be loaded for agent {_current_agent_id}")
    
    return special_servers

def get_mcp_servers():
    """Get MCP servers configuration with current agent context - combines standard and special servers."""
    # Get standard servers (always loaded)
    standard_servers = get_standard_mcp_servers()
    
    # Get special servers (conditionally loaded based on agent)
    special_servers = get_special_mcp_servers()
    
    # Combine both lists
    all_servers = standard_servers + special_servers
    
    print(f"🔧 Loading {len(standard_servers)} standard servers + {len(special_servers)} special servers for agent {_current_agent_id}")
    
    return all_servers

# For backward compatibility
MCP_SERVERS = get_mcp_servers()
