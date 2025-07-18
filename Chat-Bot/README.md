# MCP Multi-Agent ChatBot System

An adv## 🆕 Latest Updates (June 2025)

### 🔗 **Multi-User Concurrency Support (June 18, 2025)**
- **Per-Connection MCP Managers**: Each WebSocket connection gets its own isolated MCP manager instance
- **True Multi-User Support**: Multiple agents can connect and chat simultaneously without interference
- **Concurrent Connection Fix**: Resolved issue where Agent 93 and Agent 188 couldn't connect simultaneously
- **Enhanced Session Isolation**: Each connection maintains independent tool access and agent context
- **Improved Scalability**: Unlimited concurrent users supported with proper resource management
- **Backward Compatibility**: All existing features preserved while adding concurrency support

### 🚀 **New MCP Server Integrations**
- **HubSpot CRM Integration**: Complete CRM management with contacts, companies, deals, and engagement tracking
- **Google Forms Integration**: Create, manage, and analyze Google Forms with response handling
- **Airtable Integration**: Full database operations including table management, record CRUD, and data analysis
- **Streamlined Deployment**: All new servers cleaned up to runtime-only essentials (no source code, docs, or dev files)
- **Environment Variable Management**: Standardized configuration using access tokens and API keys-powered multi-agent chatbot built on the Model Context Protocol (MCP) architecture. Features intelligent agent routing, vectorized knowledge base integration, real-time WebSocket communication, seamless multi-service connectivity, and robust multi-tenant support with age### 🌐 Enhanced WebSocket Real-Time Features

### Real-Time Streaming Chat with Multi-User Concurrency
The WebSocket server provides advanced real-time communication capabilities with enhanced security and concurrency:

- **🔄 Live Response Streaming** - AI responses appear in real-time as they're generated
- **⚡ Instant Communication** - No polling needed, true bidirectional communication  
- **👥 Multi-User Support** - Unlimited concurrent connections with per-connection MCP managers
- **🔄 Session Isolation** - Each connection gets its own isolated MCP manager and tool access
- **📊 Enhanced Connection Management** - Automatic tracking of active connections with session metadata
- **🎨 Interactive Interface** - Built-in HTML frontend with full session ID display and copy functionality
- **💬 Persistent Sessions** - Maintain conversation context across WebSocket connections with UUID tracking
- **💾 Auto-Save Chat History** - All conversations automatically stored in MongoDB with enhanced metadata
- **📚 Session Continuity** - Chat history preserved across disconnections and reconnections
- **🔐 Token Authentication** - Secure access with agent token validation and proper error handling
- **🏗️ Agent Context Management** - Proper multi-tenant isolation with agent-specific initialization

### WebSocket Usage Example
**Test via Enhanced HTML Interface:**
1. Start the WebSocket server: `python websocket_server.py`
2. Open browser to: `http://localhost:8001/chat/ws/test`
3. Enter your agent authentication token
4. Type messages and see real-time AI responses streaming with full session ID displaylization.

## 🚀 Key Features

- **🎯 Smart Agent Routing**: Automatically routes queries to specialized sub-agents with token-based authentication
- **🤖 Multi-Agent System**: Developer, Writer, Sales, and General purpose agents with knowledge base integration
- **🧠 Knowledge Base Integration**: Self-contained vector database with 116+ documents and AI-powered semantic search
- **🔗 Multi-Service Integration**: Mathematical operations, knowledge base, and extensible MCP server architecture
- **⚡ Triple Deployment Modes**: REST API server + WebSocket server + Interactive command-line client
- **🔄 Real-time Processing**: Async communication via stdio transport with streaming responses
- **🌐 WebSocket Support**: Real-time bidirectional communication with streaming AI responses and authentication
- **� Multi-User Concurrency**: Per-connection MCP managers enable unlimited simultaneous users
- **�📡 Live Updates**: Real-time message streaming, connection management, and session tracking
- **💾 Persistent Chat History**: Enhanced MongoDB integration with multiple authentication methods
- **📚 Conversation Memory**: Maintains chat context across sessions with structured storage
- **🔐 Multi-Tenant Architecture**: Agent-specific initialization with proper isolation and S3 path management
- **🛠️ Robust Error Handling**: Enhanced connection management, retry logic, and graceful fallbacks
- **🔗 CORS Enabled**: Full CORS support for seamless frontend integration

## 🆕 Latest Updates (June 2025)

### � **New MCP Server Integrations**
- **HubSpot CRM Integration**: Complete CRM management with contacts, companies, deals, and engagement tracking
- **Google Forms Integration**: Create, manage, and analyze Google Forms with response handling
- **Airtable Integration**: Full database operations including table management, record CRUD, and data analysis
- **Streamlined Deployment**: All new servers cleaned up to runtime-only essentials (no source code, docs, or dev files)
- **Environment Variable Management**: Standardized configuration using access tokens and API keys

### �🔧 **MCP Initialization Order Fix**
- **Fixed Agent Context Issue**: Resolved initialization order problem where MCP tools loaded before authentication
- **Lazy Initialization**: MCP servers now initialize after authentication with correct agent context
- **Agent-Specific S3 Paths**: Knowledge base server correctly receives agent_id for proper multi-tenant file isolation
- **Enhanced Session Management**: Full session ID display with click-to-copy functionality

### 🗄️ **Enhanced MongoDB Integration**
- **Dual-Environment Support**: Automatic detection of local (authenticated) vs production (IP-whitelisted) MongoDB connections
- **Multiple Authentication Methods**: Supports URI-based, admin auth, and database-specific authentication
- **Connection Diagnostics**: Built-in diagnostic tool for troubleshooting MongoDB connection issues
- **Improved Error Handling**: Better retry logic and graceful fallbacks when MongoDB is unavailable
- **Connection Status Monitoring**: Real-time connection health monitoring and automatic reconnection

### ⚙️ **AWS Configuration Improvements**
- **Region Support**: Added AWS_REGION configuration for proper S3 access
- **Enhanced Credentials**: Improved AWS credential handling and validation
- **Diagnostic Tools**: Built-in AWS connection testing and troubleshooting capabilities

### 🧹 **Code Cleanup & Optimization**
- **MCP Server Cleanup**: Removed development files, documentation, and source code from all MCP servers
- **Streamlined Dependencies**: Updated package configurations to use only access/refresh tokens
- **Removed Redundant Functions**: Cleaned up duplicate search functionality in knowledge base
- **Enhanced Documentation**: Updated system flow documentation and configuration guides

## Architecture

The system uses a **Model Context Protocol (MCP)** client-server architecture with intelligent agent routing, multi-tenant support, real-time WebSocket communication, and **per-connection concurrency**:

- **Master Agent**: Central orchestrator with token-based routing and authentication
- **Sub-Agents**: Specialized agents with agent-specific knowledge base access and context isolation
- **Per-Connection MCP Managers**: Each WebSocket connection gets its own isolated MCP manager instance
- **Knowledge Base Server**: Self-contained vector database with AI-powered semantic search
- **MCP Servers**: Mathematical operations and extensible service integrations
- **Authentication Layer**: Token-based authentication with agent context management
- **Multi-Tenant Support**: Agent-specific initialization and resource isolation
- **Concurrent Architecture**: Unlimited simultaneous users with independent tool access

```
┌─────────────────────────────────────────────────────────────┐
│                 AUTHENTICATED AGENT SYSTEM                  │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │ Token Auth &    │───►│    Agent-Specific Routing       │ │
│  │ Routing Engine  │    │  • Developer Bot (+ Agent KB)   │ │
│  │   (GPT-4)       │    │  • Writer Bot (+ Agent KB)      │ │
│  └─────────────────┘    │  • Sales Bot (+ Agent KB)       │ │
│                         │  • General Bot (+ Agent KB)     │ │
│                         └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                   │
                   ┌───────────────┼───────────────┐
                   │               │               │
         ┌─────────▼────┐ ┌────────▼────┐ ┌───────▼──────┐
         │ Knowledge    │ │   Math      │ │  MongoDB     │
         │ Base Server  │ │  Operations │ │  Chat        │
         │ (Agent-aware)│ │  Server     │ │  History     │
         │ (116+ docs)  │ │ (Python)    │ │ (Enhanced)   │
         │ (Python)     │ └─────────────┘ └──────────────┘
         └──────────────┘                                 
                │
         ┌──────┼──────────────────────────────────────┐
         │      │                                      │
    ┌────▼───┐ ┌▼─────────┐ ┌─────────────┐ ┌─────────▼──┐
    │HubSpot │ │Google    │ │  Airtable   │ │  Optional  │
    │  CRM   │ │ Forms    │ │ Database    │ │   MCP      │
    │(Node.js│ │(Node.js) │ │ (Node.js)   │ │  Servers   │
    │   MCP) │ └──────────┘ └─────────────┘ │ (Gmail,    │
    └────────┘                             │  Sheets,   │
                                          │  JIRA, etc)│
                                          └────────────┘                                 
                                   
┌─────────────────────────────────────────────────────────────┐
│              ENHANCED DEPLOYMENT ARCHITECTURE               │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   REST API      │    │      WebSocket Server           │ │
│  │   Server        │    │   (Per-Connection Managers)     │ │
│  │   (Port 8001)   │    │       (Port 8001)               │ │
│  │                 │    │                                 │ │
│  │ • HTTP Endpoints│    │ • Token Authentication          │ │
│  │ • Agent Routing │    │ • Multi-User Concurrency        │ │
│  │ • Tool Access   │    │ • Per-Connection MCP Managers   │ │
│  │ • Health Checks │    │ • Streaming Responses           │ │
│  └─────────────────┘    │ • Session Isolation             │ │
│           │              │ • Unlimited Concurrent Users   │ │
│           └─────────────┬┴─────────────────────────────────┘ │
│                         │                                   │
│             ┌───────────▼──────────┐                        │
│             │  Global MCP Manager  │                        │
│             │   (API Server Only)  │                        │
│             └──────────────────────┘                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           PER-CONNECTION CONCURRENCY MODEL              │ │
│  │                                                         │ │
│  │  Agent 93 ──► WebSocket ──► Dedicated MCP Manager ──►  │ │
│  │  Connection    Session      (Isolated Tools & Context) │ │
│  │                                                         │ │
│  │  Agent 188 ──► WebSocket ──► Dedicated MCP Manager ──► │ │
│  │  Connection     Session      (Isolated Tools & Context)│ │
│  │                                                         │ │
│  │  Agent N ──► WebSocket ──► Dedicated MCP Manager ──►   │ │
│  │  Connection   Session      (Isolated Tools & Context)  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📁 File Structure

The system is organized into clean, modular components with separated concerns:

### Core Server Files
- **`api_server.py`** - FastAPI REST API server (Port 8001) - HTTP endpoints only
- **`websocket_server.py`** - FastAPI WebSocket server (Port 8001) - Real-time communication
- **`websocket_frontend.html`** - Interactive WebSocket test interface
- **`mcp_client.py`** - Shared MCP client manager, agent initialization, and routing logic
- **`mcp_servers_list.py`** - Centralized configuration for all MCP servers
- **`mongodb_manager.py`** - MongoDB connection and chat history storage manager

### Interface Files
- **`mcp_client_interactive.py`** - Interactive command-line interface
- **`knowledge_base_server.py`** - Self-contained knowledge base MCP server

### Supporting Files
- **`requirements.txt`** - Python dependencies with Node.js MCP server documentation
- **`README.md`** - Comprehensive documentation with latest updates
- **`view_document.py`** - Document viewer utility with AWS configuration
- **`test_mongodb_dual_env.py`** - MongoDB dual-environment connection testing

### New MCP Server Integrations (Node.js)
- **`hubspot-mcp-server/`** - HubSpot CRM integration with contact, company, and deal management
- **`google-forms-mcp/`** - Google Forms creation, management, and response analysis
- **`airtable-mcp/`** - Airtable database operations and record management

### Existing MCP Servers
- **`google-workspace-mcp-server/`** - Google services integration (Node.js) [Enabled]
- **`mcp-google-sheets/`** - Google Sheets integration (Python) [Enabled]
- **`mcp-bigquery-server/`** - Google BigQuery integration (Node.js) [Enabled]
- **`jira-mcp-server/`** - JIRA project management integration (Node.js) [Enabled]

### Optional/Disabled Services
- **`whatsapp-mcp/`** - WhatsApp messaging integration (Python) [Disabled]  
- **`storage/`** - Local file storage and processing utilities

## 🤖 Sub-Agent Specializations

### 👨‍💻 Developer Bot
**Expertise**: Programming, coding, technical solutions
- Clean, efficient code in multiple languages
- Debugging and troubleshooting
- Algorithm explanations and data structures
- Best practices and code optimization
- Knowledge base integration and vector search implementations
- Technical documentation lookup via knowledge base
- Automated code sharing via WhatsApp/Email

### ✍️ Writer Bot  
**Expertise**: Content creation, writing, documentation
- Engaging and compelling content
- Clear, concise documentation
- Creative stories and articles
- Editing and proofreading
- Tone adaptation for different audiences
- Research and fact-checking using knowledge base
- Information gathering for writing projects

### 💼 Sales Bot
**Expertise**: Sales, business development, outreach
- Persuasive sales pitches and proposals
- Lead generation and customer outreach
- Market analysis and competitive research
- Customer relationship management
- Value-driven solution development
- Product knowledge and documentation research
- Pricing details and company policy lookup

### 🔧 General Bot
**Expertise**: Versatile assistant for various tasks
- Multi-service coordination
- General inquiries and support
- Cross-platform integrations
- Fallback for uncategorized queries
- Comprehensive knowledge base system access
- Information retrieval and status checks

## 🛠️ Available Tools & Integrations

### 🆕 **New CRM & Productivity Integrations**
#### HubSpot CRM Tools
- `search_contacts` - Search and filter HubSpot contacts with advanced criteria
- `get_contact` - Retrieve detailed contact information by ID
- `create_contact` - Create new contacts with comprehensive property support
- `update_contact` - Update existing contact properties and information
- `search_companies` - Search and filter companies in HubSpot CRM
- `get_company` - Retrieve detailed company information and associations
- `create_company` - Create new companies with custom properties
- `update_company` - Update company information and properties
- `get_deals` - Retrieve deals with filtering and association options
- `get_recent_activities` - Get recent engagement activities and interactions

#### Google Forms Tools  
- `create_form` - Create new Google Forms with custom questions and settings
- `get_form` - Retrieve form structure, questions, and metadata
- `update_form` - Modify existing forms, questions, and configurations
- `delete_form` - Remove forms from Google Drive
- `list_forms` - List all accessible Google Forms with filtering options
- `get_responses` - Retrieve and analyze form responses with export options
- `create_watch` - Set up real-time notifications for new form responses

#### Airtable Database Tools
- `list_bases` - List all accessible Airtable bases and workspaces
- `get_base_schema` - Retrieve base structure, tables, and field definitions
- `list_tables` - List all tables within a specific Airtable base
- `get_table_schema` - Get detailed table structure and field configurations
- `list_records` - Query and filter records with advanced search capabilities
- `get_record` - Retrieve specific record details with linked record data
- `create_record` - Create new records with field validation and type checking
- `update_record` - Modify existing records with conflict resolution
- `delete_record` - Remove records with cascade options for linked data

### 🧠 Knowledge Base Tools (Agent-Aware)
- `query_knowledge_base` - AI-powered semantic search with agent-specific context and configurable results
- `get_knowledge_base_status` - Check system health, document count, storage status, and agent configuration

### 🔢 Math Tools
- `add` - Add two integers
- `multiply` - Multiply two integers  
- `subtract` - Subtract two integers
- `modulo` - Calculate modulo of two integers
- `premOper` - Custom mathematical operation (a + 2*b)
- `yatiOp` - Additional mathematical operation

### 🔌 Extensible MCP Architecture
The system supports easy integration of additional MCP servers:
- **Math Server**: Provides mathematical operations and calculations
- **Knowledge Base Server**: Agent-aware document storage and retrieval
- **HubSpot Server**: Comprehensive CRM management and automation (Node.js)
- **Google Forms Server**: Form creation, management, and response analysis (Node.js)  
- **Airtable Server**: Database operations and record management (Node.js)
- **Custom Servers**: Easy addition of new MCP servers through `mcp_servers_list.py`

### 🚫 Disabled Integrations
The following integrations are available but currently disabled for simplified deployment:
- **Google Workspace Tools**: Gmail, Calendar, Google Sheets (Node.js server)
- **WhatsApp Tools**: Messaging, file sharing, contact management (Python server)
- **Custom Integrations**: Additional MCP servers can be enabled as needed

## 💾 Chat History & MongoDB Integration

### Persistent Conversation Storage
The system features robust chat history management with MongoDB integration, ensuring all conversations are preserved and accessible across sessions.

### 🗄️ Enhanced MongoDB Chat Storage
- **Database**: `masterDB`
- **Collection**: `chat_agent_chat_history`
- **Auto-Storage**: Every chat interaction is automatically stored
- **Session Tracking**: Each conversation session has a unique identifier with full UUID display
- **Agent Attribution**: Records which specialized agent handled each query
- **Multiple Auth Methods**: Supports URI-based, admin auth, and database-specific authentication
- **Connection Diagnostics**: Built-in diagnostic tools for troubleshooting connection issues
- **Enhanced Error Handling**: Graceful fallbacks and automatic reconnection logic

### 📚 Enhanced Chat History Schema
Each stored conversation includes:
```json
{
  "session_id": "full-uuid-string",
  "user_prompt": "User's message/question", 
  "agent_response": "AI agent's response",
  "agent_used": "developer|writer|sales|general",
  "agent_id": 123,
  "workspace_id": 456,
  "ip_address": "192.168.1.1",
  "user_agent": "browser/version",
  "timestamp": "2025-06-08T10:30:00Z"
}
```

### 🔄 Enhanced Chat History Features
- **Automatic Storage**: All interactions stored without user intervention
- **Session Continuity**: Maintain conversation context across WebSocket reconnections with full session ID display
- **Agent Routing History**: Track which agents handle different types of queries with enhanced metadata
- **Timestamp Tracking**: Full audit trail of conversation timing and user context
- **Scalable Architecture**: MongoDB provides robust, scalable chat storage with multiple authentication methods
- **Async Operations**: Non-blocking chat storage for optimal performance
- **Connection Diagnostics**: Built-in tools for troubleshooting MongoDB connectivity issues
- **Multi-Tenant Support**: Agent-aware storage with proper isolation and context management

### 🛠️ Enhanced Chat History Management
- **Multiple Connection Methods**: URI-based, admin auth, and database-specific authentication
- **Connection Pooling**: Efficient MongoDB connection management with retry logic
- **Error Handling**: Graceful fallback if MongoDB is unavailable with detailed error logging
- **Automatic Reconnection**: Smart reconnection logic with multiple authentication attempts
- **Performance Optimized**: Async storage operations don't block chat responses
- **Diagnostic Tools**: MongoDB connection diagnostic utility (`mongodb_diagnostic.py`) for troubleshooting

## 🚀 Deployment Modes

### 1. REST API Server Mode (`api_server.py`)
**HTTP endpoints for integration (Port 8001):**

- `POST /chat/api/query` - Smart routing to appropriate sub-agent
- `POST /chat/api/query/direct` - Direct agent access (no routing)
- `POST /chat/api/query/agent/{agent_type}` - Specific sub-agent access
- `GET /chat/api/agents` - List available agents
- `GET /chat/api/tools/{server_id}` - List tools by MCP server
- `GET /health` - Server health check and status

**Start the REST API server:**
```bash
python api_server.py
```

### 2. WebSocket Server Mode (`websocket_server.py`)
**Real-time communication server (Port 8001) with Token Authentication:**

- `WS /chat/ws?token=your_agent_token` - Main WebSocket endpoint for real-time chat with streaming responses (requires authentication)
- `GET /chat/ws/test` - Interactive HTML test interface for WebSocket functionality with token input
- `GET /chat/ws/health` - WebSocket server health check with connection statistics

**🔐 Enhanced Authentication Features:**
- **Token-based Authentication** - All WebSocket connections require valid agent tokens from authentication API
- **Secure Connection Management** - Invalid tokens are rejected with proper error messages and connection closure
- **Session Tracking** - Authenticated users get unique session IDs for conversation history with full UUID display
- **Agent Context Management** - Proper agent context setting for multi-tenant isolation
- **MCP Initialization Order** - Fixed lazy initialization to ensure MCP tools load after authentication with correct agent context

**Enhanced Features:**
- **Real-time streaming responses** - AI responses stream in real-time as they're generated
- **🔐 Robust Token Authentication** - Secure access using agent tokens with proper validation
- **Connection management** - Automatic connection tracking, cleanup, and session management
- **Interactive frontend** - Built-in HTML interface for testing WebSocket functionality with enhanced session display
- **Bidirectional communication** - Full duplex communication between client and server
- **Full Session ID Display** - Complete UUID session IDs with click-to-copy functionality

**Start the WebSocket server:**
```bash
python websocket_server.py
```

**Test the WebSocket interface:**
Open your browser to `http://localhost:8001/chat/ws/test` for an interactive chat interface with enhanced token authentication and full session ID display.

### 3. Both Servers (Recommended)
**Run both servers simultaneously for full functionality:**

```bash
# Terminal 1 - REST API Server
python api_server.py

# Terminal 2 - WebSocket Server  
python websocket_server.py
```

### 4. Interactive Command-Line Mode (`mcp_client_interactive.py`)
**Terminal-based interaction with enhanced menu system:**

- 🎯 Smart Query (Auto-route to appropriate agent with knowledge base access)
- 👨‍💻 Developer Agent (Direct access with enhanced knowledge base tools)
- ✍️ Writer Agent (Direct access with research capabilities)
- 💼 Sales Agent (Direct access with product information lookup)  
- 🔧 General Agent (Direct access with comprehensive knowledge base)
- 🚀 Direct Agent (No routing, raw MCP access)
- 📋 List Available Agents
- 🛠️ List Tools by Server

**Start the interactive client:**
```bash
python mcp_client_interactive.py
```

## 🌐 WebSocket Real-Time Features

### Real-Time Streaming Chat
The WebSocket server provides advanced real-time communication capabilities:

- **🔄 Live Response Streaming** - AI responses appear in real-time as they're generated
- **⚡ Instant Communication** - No polling needed, true bidirectional communication
- **📊 Connection Management** - Automatic tracking of active connections
- **🎨 Interactive Interface** - Built-in HTML frontend for easy testing and demos
- **💬 Persistent Sessions** - Maintain conversation context across WebSocket connections
- **💾 Auto-Save Chat History** - All conversations automatically stored in MongoDB
- **📚 Session Continuity** - Chat history preserved across disconnections and reconnections

### WebSocket Usage Example
**Test via HTML Interface:**
1. Start the WebSocket server: `python websocket_server.py`
2. Open browser to: `http://localhost:8001/test`
3. Type messages and see real-time AI responses streaming

## Prerequisites

- Python 3.11+
- Node.js 18+ (for HubSpot, Google Forms, and Airtable MCP servers)
- OpenAI API key
- MongoDB (for chat history storage - enhanced connection support)
- AWS credentials (for knowledge base S3 storage)

### 🔑 **Required API Keys & Credentials**
#### Core Services
- **OpenAI API Key**: For AI-powered responses and knowledge base search
- **MongoDB**: For persistent chat history (local or cloud)
- **AWS S3**: For agent-specific knowledge base storage

#### New MCP Server Integrations
- **HubSpot Access Token**: For CRM operations and contact management
- **Google Forms Access/Refresh Tokens**: For form creation and response management  
- **Airtable API Key**: For database operations and record management

#### Optional Services
- **Google Workspace Tokens**: For Gmail and Google Sheets (currently disabled)
- **JIRA API Credentials**: For project management integration (if enabled)
- **BigQuery Tokens**: For data analytics (if enabled)

## Environment Setup

Create `.env` file with enhanced configuration:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# MongoDB Configuration (Enhanced - for Chat History)
MONGODB_URI=mongodb://localhost:27017/masterDB
MONGODB_DB_NAME=masterDB
MONGODB_USERNAME=your_mongodb_username
MONGODB_PASSWORD=your_mongodb_password
MONGODB_HOST=localhost:27017

# AWS Configuration (Required for Knowledge Base)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_BUCKET_NAME=your_s3_bucket_name
AWS_REGION=your_aws_region
AWS_URL=https://your_bucket.s3.region.amazonaws.com/

# Server Configuration
PORT=8001
UNLEASHX_URL=https://your-auth-api.com

# New MCP Server Integrations
# HubSpot CRM Integration
HUBSPOT_ACCESS_TOKEN=your_hubspot_access_token

# Google Forms Integration
GFORMS_ACCESS_TOKEN=your_google_forms_access_token
GFORMS_REFRESH_TOKEN=your_google_forms_refresh_token

# Airtable Integration
AIRTABLE_API_KEY=your_airtable_api_key

# Optional: Google Workspace Configuration (Disabled by default)
# GMAIL_ACCESS_TOKEN=your_gmail_access_token
# GMAIL_REFRESH_TOKEN=your_gmail_refresh_token
# GSHEETS_ACCESS_TOKEN=your_gsheets_access_token
# GSHEETS_REFRESH_TOKEN=your_gsheets_refresh_token
# DRIVE_FOLDER_ID=your_drive_folder_id

# Optional: BigQuery Configuration (Disabled by default)
# BIGQUERY_ACCESS_TOKEN=your_bigquery_access_token
# BIGQUERY_REFRESH_TOKEN=your_bigquery_refresh_token
# GOOGLE_CLOUD_PROJECT_ID=your_project_id

# Optional: JIRA Configuration (Disabled by default)
# JIRA_URL=your_jira_instance_url
# JIRA_API_MAIL=your_jira_email
# JIRA_API_KEY=your_jira_api_key
```

### 🔧 Configuration Notes
- **MongoDB Authentication**: System supports multiple authentication methods (URI, admin, database-specific)
- **AWS Credentials**: Required for agent-specific knowledge base storage in S3
- **Authentication API**: Configure UNLEASHX_URL for token validation in WebSocket connections
- **New MCP Servers**: HubSpot, Google Forms, and Airtable require respective API credentials
- **Optional Services**: Google Workspace, BigQuery, and JIRA integrations are disabled by default for simplified setup

## Installation

1. **Install Node.js** (required for new MCP servers):
   ```bash
   # macOS (using Homebrew)
   brew install node
   
   # Verify installation
   node --version  # Should be 18.0 or higher
   npm --version
   ```

2. **Install MongoDB** (for enhanced chat history storage):
   ```bash
   # macOS (using Homebrew)
   brew tap mongodb/brew
   brew install mongodb-community
   brew services start mongodb/brew/mongodb-community
   
   # Or use MongoDB Atlas (cloud) and update MONGODB_URI accordingly
   # The system supports multiple authentication methods automatically
   ```

3. **Install Python dependencies:**
   ```bash
   cd /Users/prembhugra/Desktop/aiagent
   pip install -r requirements.txt
   ```

4. **Install Node.js dependencies for MCP servers:**
   ```bash
   # Install HubSpot MCP server dependencies
   cd /Users/prembhugra/Desktop/aiagent/hubspot-mcp-server
   npm install
   
   # Install Google Forms MCP server dependencies
   cd /Users/prembhugra/Desktop/aiagent/google-forms-mcp
   npm install
   
   # Install Airtable MCP server dependencies
   cd /Users/prembhugra/Desktop/aiagent/airtable-mcp
   npm install
   
   # Return to main directory
   cd /Users/prembhugra/Desktop/aiagent
   ```

5. **Configure AWS credentials** (required for knowledge base):
   ```bash
   # Ensure AWS credentials are configured in .env file
   # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_BUCKET_NAME
   ```

6. **Test MongoDB connection** (optional diagnostic):
   ```bash
   # Run diagnostic tool to test MongoDB connectivity
   python test_mongodb_dual_env.py
   ```

7. **Verify MCP servers** (optional):
   ```bash
   # Test HubSpot server
   node hubspot-mcp-server/dist/index.js --version
   
   # Test Google Forms server  
   node google-forms-mcp/build/index.js --version
   
   # Test Airtable server
   node airtable-mcp/build/index.js --version
   ```

## Startup Procedures

### Option 1: Enhanced WebSocket + REST API Mode (Recommended)

1. **Start WebSocket Server** (Terminal 1):
   ```bash
   cd /Users/prembhugra/Desktop/aiagent
   python websocket_server.py
   ```
   - Available at: `ws://localhost:8001/chat/ws?token=your_token`
   - Test interface: `http://localhost:8001/chat/ws/test`
   - Features token authentication and full session ID display

2. **Start REST API Server** (Terminal 2):
   ```bash
   cd /Users/prembhugra/Desktop/aiagent
   python api_server.py
   ```
   - Available at: `http://localhost:8001`
   - HTTP endpoints for API integration

### Option 2: WebSocket Only (Real-time Chat)
```bash
cd /Users/prembhugra/Desktop/aiagent
python websocket_server.py
```
- Perfect for real-time chat applications
- Enhanced token authentication and session management
- Full session ID display with copy functionality

### Option 3: REST API Only (HTTP Integration)
```bash
cd /Users/prembhugra/Desktop/aiagent
python api_server.py
```
- Ideal for HTTP-based integrations
- RESTful endpoints for various agents

### Option 4: Interactive Command-Line Mode
```bash
cd /Users/prembhugra/Desktop/aiagent
python mcp_client_interactive.py
```
- Terminal-based interaction with enhanced menu system
- Direct access to all agents and knowledge base tools

## Usage Examples

### 💬 REST API Examples (Enhanced)
```bash
# Smart routing query with knowledge base access
curl -X POST "http://localhost:8001/chat/api/query" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is machine learning and how does it work?"}'

# Direct developer agent access with enhanced tools
curl -X POST "http://localhost:8001/chat/api/query/agent/developer" \
  -H "Content-Type: application/json" \
  -d '{"message": "How to implement a REST API in Python with FastAPI?"}'

# Math operations example
curl -X POST "http://localhost:8001/chat/api/query/agent/general" \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 25 + 37 and then multiply by 3"}'

# Knowledge base query example
curl -X POST "http://localhost:8001/chat/api/query/agent/general" \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for information about artificial intelligence"}'

# List available agents
curl "http://localhost:8001/chat/api/agents"

# Check server health
curl "http://localhost:8001/health"
```

### 🌐 Enhanced WebSocket Examples with Multi-User Support
```javascript
// ========================================
// MULTIPLE AGENTS CAN CONNECT SIMULTANEOUSLY
// ========================================

// Agent 93 Connection
const token93 = "agent_93_token_from_auth_api";
const ws93 = new WebSocket(`ws://localhost:8001/chat/ws?token=${encodeURIComponent(token93)}`);

// Agent 188 Connection (SIMULTANEOUS)
const token188 = "agent_188_token_from_auth_api";
const ws188 = new WebSocket(`ws://localhost:8001/chat/ws?token=${encodeURIComponent(token188)}`);

// Both connections work independently - no interference!
ws93.onopen = () => {
    console.log('✅ Agent 93 connected with dedicated MCP manager');
    ws93.send(JSON.stringify({
        query: "What is machine learning and how does it work?",
        agent_type: "general"
    }));
};

ws188.onopen = () => {
    console.log('✅ Agent 188 connected with separate MCP manager');
    ws188.send(JSON.stringify({
        query: "Create a Python REST API example",
        agent_type: "developer"
    }));
};

// Each connection receives independent responses
ws93.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📦 Agent 93 received:', data);
    
    switch(data.type) {
        case 'status':
            if (data.message.includes('Authenticated')) {
                console.log('✅ Agent 93 authentication successful!');
                console.log('🆔 Agent 93 Session ID:', data.session_id);
            }
            break;
        case 'streaming':
            console.log('🔄 Agent 93 streaming:', data.content);
            break;
        case 'final_response':
            console.log('✅ Agent 93 Final Response:', data.content);
            console.log('🤖 Agent 93 Used:', data.agent);
            break;
        case 'error':
            console.log('❌ Agent 93 Error:', data.message);
            break;
    }
};

ws188.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📦 Agent 188 received:', data);
    
    switch(data.type) {
        case 'status':
            if (data.message.includes('Authenticated')) {
                console.log('✅ Agent 188 authentication successful!');
                console.log('🆔 Agent 188 Session ID:', data.session_id);
            }
            break;
        case 'streaming':
            console.log('🔄 Agent 188 streaming:', data.content);
            break;
        case 'final_response':
            console.log('✅ Agent 188 Final Response:', data.content);
            console.log('🤖 Agent 188 Used:', data.agent);
            break;
        case 'error':
            console.log('❌ Agent 188 Error:', data.message);
            break;
    }
};

// Handle authentication errors for both connections
ws93.onclose = (event) => {
    if (event.code === 1008) {
        console.log('❌ Agent 93 Authentication failed:', event.reason);
    } else {
        console.log('� Agent 93 Connection closed:', event.code, event.reason);
    }
};

ws188.onclose = (event) => {
    if (event.code === 1008) {
        console.log('❌ Agent 188 Authentication failed:', event.reason);
    } else {
        console.log('🔌 Agent 188 Connection closed:', event.code, event.reason);
    }
};

// Both agents can chat simultaneously without interference!
// Agent 93 can use HubSpot tools while Agent 188 uses Google Forms
```

**Enhanced Authentication Requirements:**
- All WebSocket connections require a valid agent token from your authentication API
- Token must be passed as query parameter: `?token=your_token`
- Invalid tokens result in immediate connection closure with error code 1008
- Contact your system administrator for token access
- Enhanced session tracking with full UUID display and copy functionality

### 💻 Enhanced Command Line Examples
```
# Mathematical operations
Enter your prompt: Calculate 25 + 37
🎯 Routing query to: general agent
🔢 Using math tools: add(25, 37) = 62

Enter your prompt: What is 15 * 8 + 42?
🎯 Routing query to: general agent  
🔢 Using math tools: multiply(15, 8) = 120, add(120, 42) = 162

# Knowledge base queries with AI-powered search
Enter your prompt: What is machine learning?
🎯 Routing query to: general agent
🧠 Using knowledge base: query_knowledge_base("machine learning")
📤 Response: [Comprehensive answer from knowledge base with AI-powered semantic search]

# HubSpot CRM operations
Enter your prompt: Find all contacts from Acme Corporation
🎯 Routing query to: sales agent
🏢 Using HubSpot: search_contacts(company="Acme Corporation")
📤 Response: [List of contacts with detailed information]

Enter your prompt: Create a new contact for John Smith at example@company.com
🎯 Routing query to: sales agent
👤 Using HubSpot: create_contact(email="example@company.com", firstname="John", lastname="Smith")
📤 Response: [Contact created successfully with ID and details]

# Google Forms management
Enter your prompt: Create a customer feedback form with rating questions
🎯 Routing query to: writer agent
📋 Using Google Forms: create_form(title="Customer Feedback", questions=[...])
📤 Response: [Form created with shareable link and question structure]

Enter your prompt: Get responses from our latest survey form
🎯 Routing query to: general agent
📊 Using Google Forms: get_responses(form_id="your_form_id")
📤 Response: [Summary of responses with analytics and insights]

# Airtable database operations
Enter your prompt: Show me all records from our customer database
🎯 Routing query to: sales agent  
🗃️ Using Airtable: list_records(base_id="your_base", table="Customers")
📤 Response: [Formatted table of customer records with pagination]

Enter your prompt: Add a new project record with status "In Progress"
🎯 Routing query to: developer agent
📝 Using Airtable: create_record(table="Projects", fields={"Status": "In Progress", ...})
📤 Response: [New record created with ID and field validation]
```

### 🧠 Enhanced Knowledge Base Queries
```
# Advanced knowledge base searches with semantic understanding
Enter your prompt: What are the latest developments in AI?
🎯 Routing query to: general agent
🧠 Knowledge base search: "AI developments, artificial intelligence advances"
📤 Response: [AI-powered semantic search through 116+ documents]

Enter your prompt: How does machine learning differ from traditional programming?
🎯 Routing query to: general agent  
🧠 Knowledge base search: "machine learning vs traditional programming"
📤 Response: [Comparative analysis from knowledge base]

Enter your prompt: What are the applications of deep learning?
🎯 Routing query to: general agent
🧠 Knowledge base search: "deep learning applications"
📤 Response: [Comprehensive overview from knowledge base documents]
```

### 🎯 Enhanced Agent-Specific Examples
```
# Developer queries with enhanced knowledge base access
Enter your prompt: How to implement a REST API in Python with FastAPI?
🎯 Routing query to: developer agent
🧠 Knowledge base + coding expertise
📤 Response: [Code examples and best practices from knowledge base]

# Writer queries with research capabilities  
Enter your prompt: Write an article about cloud computing trends
🎯 Routing query to: writer agent
🧠 Research using knowledge base + writing expertise
📤 Response: [Well-researched article using knowledge base information]

# Sales queries with HubSpot CRM integration
Enter your prompt: What deals are currently in the pipeline?
🎯 Routing query to: sales agent
🏢 HubSpot CRM + product knowledge base + sales expertise
📤 Response: [Current deals analysis with CRM data and sales insights]

# General queries with comprehensive tool access
Enter your prompt: Calculate the ROI of implementing AI solutions
🎯 Routing query to: general agent
🔢 Math calculations + 🧠 Knowledge base research
📤 Response: [Mathematical analysis combined with AI industry insights]
```

## 🔧 Troubleshooting & Diagnostics

### MongoDB Connection Issues
If you encounter MongoDB authentication failures:

1. **Run the diagnostic tool:**
   ```bash
   cd /Users/prembhugra/Desktop/aiagent
   python mongodb_diagnostic.py
   ```

2. **Common fixes:**
   - Remove quotes from MongoDB password in `.env`
   - Check MongoDB server status: `brew services list | grep mongodb`
   - Verify credentials and user permissions
   - Try different authentication methods (the system auto-detects the best method)

### AWS Configuration Issues
If knowledge base queries fail:

1. **Verify AWS credentials in `.env`:**
   ```env
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=your_region
   AWS_BUCKET_NAME=your_bucket
   ```

2. **Test AWS connectivity:**
   ```bash
   python view_document.py
   ```

### WebSocket Authentication Issues
If WebSocket connections fail:

1. **Verify token format and validity**
2. **Check authentication API endpoint in `.env`:**
   ```env
   UNLEASHX_URL=https://your-auth-api.com
   ```
3. **Monitor WebSocket server logs for authentication errors**

## 🎯 System Architecture Benefits

### 🔄 **MCP Initialization Order Fix**
- **Problem Solved**: MCP tools now load after authentication with correct agent context
- **Benefit**: Knowledge base server receives proper agent_id for multi-tenant S3 path isolation
- **Result**: Each agent has isolated document storage and retrieval

### 🗄️ **Enhanced MongoDB Integration**
- **Multiple Auth Methods**: Automatically tries URI, admin auth, and database-specific authentication
- **Connection Resilience**: Built-in retry logic and graceful fallbacks
- **Diagnostic Tools**: Easy troubleshooting with `mongodb_diagnostic.py`

### 🔐 **Robust Authentication**
- **Token Validation**: Secure WebSocket connections with proper token verification
- **Session Management**: Full UUID session tracking with enhanced display
- **Agent Context**: Proper multi-tenant isolation and context management

### 🧠 **AI-Powered Knowledge Base**
- **Semantic Search**: Advanced AI-powered search through 116+ documents
- **Agent-Specific Context**: Each agent has access to relevant knowledge base tools
- **Performance Optimized**: Efficient vector search with caching and optimization

## Notes

- **MongoDB connection is optional** - system works without it, but chat history won't be stored
- **AWS credentials are required** - for agent-specific knowledge base S3 storage
- **Authentication tokens required** - for WebSocket connections and agent context
- **Knowledge base is self-contained** - 116+ pre-loaded documents with AI-powered search
- **MCP architecture is extensible** - easy to add new tools and services
- **Multi-tenant support** - proper agent isolation and context management
- **Enhanced error handling** - comprehensive logging and diagnostic tools
- **Performance optimized** - async operations and efficient resource management
- **True multi-user concurrency** - unlimited simultaneous connections with per-connection isolation

### 🔧 **Concurrency Model**

**Per-Connection MCP Managers:**
- Each WebSocket connection creates its own dedicated `MCPClientManager` instance
- Multiple agents (93, 188, etc.) can connect simultaneously without interference
- No shared state between connections - complete isolation
- Unlimited concurrent users supported
- Resolves the "No tools loaded" error when multiple users connect

**Before (Shared Manager):**
- Agent 93 connects → starts initialization
- Agent 188 connects → cancels Agent 93's initialization  
- Agent 93 fails with "No tools loaded"

**After (Per-Connection Managers):**
- Agent 93 connects → gets dedicated manager → works independently
- Agent 188 connects → gets separate manager → works independently
- Both agents chat simultaneously without issues

---

## 🚀 **Latest Version Highlights (June 2025)**

✅ **Multi-User Concurrency Support** - Per-connection MCP managers enable unlimited simultaneous users  
✅ **Concurrent Connection Fix** - Resolved Agent 93/188 interference with dedicated isolation  
✅ **New MCP Server Integrations** - HubSpot CRM, Google Forms, and Airtable database management  
✅ **Streamlined Deployment** - All MCP servers cleaned to runtime-only essentials  
✅ **Dual-Environment MongoDB** - Automatic detection of local vs production connection modes  
✅ **Fixed MCP initialization order** - Agent context properly set before MCP server startup  
✅ **Enhanced MongoDB integration** - Multiple authentication methods with diagnostics  
✅ **Full session ID display** - Complete UUID tracking with copy functionality  
✅ **AWS configuration improvements** - Region support and credential validation  
✅ **Code cleanup** - Removed redundant functions and unused integrations  
✅ **Enhanced documentation** - Complete system flow and troubleshooting guides  
✅ **Robust error handling** - Graceful fallbacks and comprehensive logging  
✅ **Multi-tenant architecture** - Agent-specific isolation and resource management  
✅ **Node.js integration** - Comprehensive MCP server ecosystem with TypeScript support