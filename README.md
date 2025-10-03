# 🤖 UnleashX AI Platform - Enterprise Bot Suite

> A comprehensive collection of three production-ready AI-powered systems built for UnleashX: Multi-agent ChatBot, Dashboard Generator, and Knowledge Base Search Bot. Each system leverages OpenAI's advanced models, multi-tenant architecture, and secure token-based authentication.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-purple.svg)](https://openai.com/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)](https://fastapi.tiangolo.com/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Platform Architecture](#-platform-architecture)
- [Project 1: Chat-Bot (MCP Multi-Agent System)](#-project-1-chat-bot---mcp-multi-agent-system)
- [Project 2: Dashboard-Bot (AI Dashboard Generator)](#-project-2-dashboard-bot---ai-dashboard-generator)
- [Project 3: Search-Bot (Knowledge Base Search)](#-project-3-search-bot---knowledge-base-search)
- [Technology Stack](#-technology-stack)
- [Quick Start](#-quick-start)
- [Common Features](#-common-features)
- [Environment Setup](#-environment-setup)
- [Security & Multi-Tenancy](#-security--multi-tenancy)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

The **UnleashX AI Platform** is an enterprise-grade suite of three interconnected AI-powered systems designed to provide comprehensive automation, intelligence, and productivity solutions. Built with modern Python and Node.js frameworks, these systems share a common foundation of security, multi-tenancy, and AI-driven capabilities.

### Platform Components

| System | Purpose | Key Technology | Port |
|--------|---------|---------------|------|
| **Chat-Bot** | Multi-agent conversational AI with MCP architecture | FastAPI + WebSocket + MCP | 8001 |
| **Dashboard-Bot** | Intelligent data visualization generator | Flask + MCP + Chart.js | 8001 |
| **Search-Bot** | AI-powered knowledge base search | Flask + OpenAI GPT-4o-mini | 5002 |

### Shared Infrastructure

- **Authentication**: Token-based authentication via UnleashX API
- **Database**: MongoDB (chat history) + MySQL (application data)
- **AI Engine**: OpenAI GPT-4o and GPT-4o-mini models
- **Storage**: AWS S3 (knowledge base and documents)
- **Architecture**: Multi-tenant with workspace isolation

---

## 🏗️ Platform Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNLEASHX AI PLATFORM                          │
│                   Token-Based Authentication                     │
└────────────┬────────────────────┬─────────────────┬─────────────┘
             │                    │                 │
    ┌────────▼────────┐  ┌───────▼──────┐  ┌──────▼──────┐
    │   CHAT-BOT      │  │ DASHBOARD-BOT │  │ SEARCH-BOT  │
    │  (Port 8001)    │  │  (Port 8001)  │  │ (Port 5002) │
    │                 │  │               │  │             │
    │ • REST API      │  │ • REST API    │  │ • REST API  │
    │ • WebSocket     │  │ • MCP Agent   │  │ • HTML UI   │
    │ • CLI Mode      │  │ • Chart Gen   │  │ • Search    │
    └────────┬────────┘  └───────┬───────┘  └──────┬──────┘
             │                   │                  │
    ┌────────▼───────────────────▼──────────────────▼──────┐
    │              SHARED INFRASTRUCTURE                    │
    │                                                       │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
    │  │ MongoDB  │  │  MySQL   │  │  AWS S3  │          │
    │  │  Chat    │  │  Pages   │  │Knowledge │          │
    │  │ History  │  │  Forms   │  │   Base   │          │
    │  └──────────┘  └──────────┘  └──────────┘          │
    │                                                       │
    │  ┌──────────────────────────────────────────┐       │
    │  │         OpenAI API (GPT-4o/mini)         │       │
    │  └──────────────────────────────────────────┘       │
    └───────────────────────────────────────────────────────┘
```

---

## 🤖 Project 1: Chat-Bot - MCP Multi-Agent System

### Overview

The **Chat-Bot** is an advanced multi-agent conversational AI system built on the **Model Context Protocol (MCP)** architecture. It features intelligent agent routing, vectorized knowledge base integration, real-time WebSocket communication, and seamless multi-service connectivity with robust multi-tenant support.

**Location**: `./Chat-Bot/`

### 🌟 Key Features

#### Advanced Multi-Agent System
- **🎯 Smart Agent Routing**: GPT-4 automatically routes queries to specialized sub-agents
- **🤖 4 Specialized Agents**: Developer, Writer, Sales, and General purpose bots
- **🧠 116+ Document Knowledge Base**: Self-contained vector database with AI-powered semantic search
- **👥 Multi-User Concurrency**: Per-connection MCP managers enable unlimited simultaneous users
- **🔗 Multi-Service Integration**: HubSpot CRM, Google Forms, Airtable, and 30+ MCP servers

#### Triple Deployment Architecture
- **⚡ REST API Server** - HTTP endpoints for integration (Port 8001)
- **🌐 WebSocket Server** - Real-time bidirectional communication with streaming responses
- **💻 Interactive CLI** - Terminal-based menu system for direct interaction

#### Real-Time WebSocket Capabilities
- **🔄 Live Response Streaming** - AI responses appear in real-time as they're generated
- **📊 Connection Management** - Automatic tracking of active connections with session metadata
- **🔐 Token Authentication** - Secure access with agent token validation
- **💾 Auto-Save Chat History** - All conversations stored in MongoDB with metadata
- **🎨 Interactive Interface** - Built-in HTML frontend with session ID display and copy functionality

### 🏗️ Chat-Bot Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              AUTHENTICATED AGENT ROUTING SYSTEM              │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │ Token Auth &    │───►│   Agent-Specific Routing        │ │
│  │ Routing Engine  │    │ • Developer Bot (+ Agent KB)    │ │
│  │   (GPT-4)       │    │ • Writer Bot (+ Agent KB)       │ │
│  └─────────────────┘    │ • Sales Bot (+ Agent KB)        │ │
│                         │ • General Bot (+ Agent KB)      │ │
│                         └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                   │
                   ┌───────────────┼───────────────┐
                   │               │               │
         ┌─────────▼────┐ ┌────────▼────┐ ┌───────▼──────┐
         │ Knowledge    │ │   Math      │ │  MongoDB     │
         │ Base Server  │ │ Operations  │ │  Chat        │
         │ (Agent-aware)│ │  Server     │ │  History     │
         │ (116+ docs)  │ │             │ │              │
         └──────┬───────┘ └─────────────┘ └──────────────┘
                │
         ┌──────┼──────────────────────────────────────┐
         │      │                                      │
    ┌────▼───┐ ┌▼─────────┐ ┌─────────────┐ ┌─────────▼──┐
    │HubSpot │ │Google    │ │  Airtable   │ │  30+ Other │
    │  CRM   │ │ Forms    │ │ Database    │ │    MCP     │
    │        │ │          │ │             │ │  Servers   │
    └────────┘ └──────────┘ └─────────────┘ └────────────┘
                                 
┌─────────────────────────────────────────────────────────────┐
│         PER-CONNECTION CONCURRENCY MODEL (June 2025)         │
│                                                              │
│  Agent 93 ──► WebSocket ──► Dedicated MCP Manager           │
│  Connection    Session      (Isolated Tools & Context)      │
│                                                              │
│  Agent 188 ──► WebSocket ──► Dedicated MCP Manager          │
│  Connection     Session      (Isolated Tools & Context)     │
│                                                              │
│  Agent N ──► WebSocket ──► Dedicated MCP Manager            │
│  Connection   Session      (Isolated Tools & Context)       │
└─────────────────────────────────────────────────────────────┘
```

### 🎯 Sub-Agent Specializations

#### 👨‍💻 Developer Bot
**Expertise**: Programming, coding, technical solutions
- Clean, efficient code in multiple languages
- Debugging and troubleshooting assistance
- Algorithm explanations and data structures
- Best practices and code optimization
- Knowledge base integration for technical documentation
- Automated code sharing capabilities

#### ✍️ Writer Bot  
**Expertise**: Content creation, writing, documentation
- Engaging and compelling content creation
- Clear, concise documentation writing
- Creative stories and articles
- Editing and proofreading services
- Tone adaptation for different audiences
- Research and fact-checking using knowledge base

#### 💼 Sales Bot
**Expertise**: Sales, business development, CRM
- Persuasive sales pitches and proposals
- Lead generation and customer outreach
- Market analysis and competitive research
- HubSpot CRM integration for contact/deal management
- Value-driven solution development
- Product knowledge and pricing lookup

#### 🔧 General Bot
**Expertise**: Versatile assistant for various tasks
- Multi-service coordination
- General inquiries and support
- Cross-platform integrations
- Comprehensive knowledge base access
- Fallback for uncategorized queries

### 🛠️ MCP Tools & Integrations

#### 🆕 New CRM & Productivity Integrations (June 2025)

**HubSpot CRM Tools** (10 tools):
- `search_contacts`, `get_contact`, `create_contact`, `update_contact`
- `search_companies`, `get_company`, `create_company`, `update_company`
- `get_deals`, `get_recent_activities`

**Google Forms Tools** (7 tools):
- `create_form`, `get_form`, `update_form`, `delete_form`
- `list_forms`, `get_responses`, `create_watch`

**Airtable Database Tools** (9 tools):
- `list_bases`, `get_base_schema`, `list_tables`, `get_table_schema`
- `list_records`, `get_record`, `create_record`, `update_record`, `delete_record`

#### 🧠 Knowledge Base Tools (Agent-Aware)
- `query_knowledge_base` - AI-powered semantic search with agent-specific context
- `get_knowledge_base_status` - System health and document count

#### 🔢 Math Tools
- `add`, `multiply`, `subtract`, `modulo`
- Custom operations: `premOper`, `yatiOp`

### 💾 Chat History & MongoDB Integration

**Enhanced Storage System:**
- Database: `masterDB`
- Collection: `chat_agent_chat_history`
- **Auto-storage** of all interactions
- **Dual-environment support**: Local (authenticated) / Production (IP whitelisted)
- **Multiple auth methods**: URI-based, admin auth, database-specific
- **Session tracking** with full UUID display

**Chat Document Schema:**
```json
{
  "session_id": "full-uuid-string",
  "user_prompt": "User's question",
  "agent_response": "AI agent's response",
  "agent_used": "developer|writer|sales|general",
  "agent_id": 123,
  "workspace_id": 456,
  "ip_address": "192.168.1.1",
  "user_agent": "browser/version",
  "timestamp": "2025-06-08T10:30:00Z"
}
```

### 🚀 Chat-Bot Deployment Modes

#### 1. REST API Server Mode
```bash
python api_server.py
```
**Endpoints:**
- `POST /chat/api/query` - Smart routing to appropriate sub-agent
- `POST /chat/api/query/direct` - Direct agent access
- `POST /chat/api/query/agent/{agent_type}` - Specific sub-agent
- `GET /chat/api/agents` - List available agents
- `GET /health` - Server health check

#### 2. WebSocket Server Mode (Recommended)
```bash
python websocket_server.py
```
**Features:**
- Real-time streaming responses
- Token-based authentication
- Per-connection MCP managers
- Unlimited concurrent users
- Test interface at `http://localhost:8001/chat/ws/test`

#### 3. Both Servers (Full Functionality)
```bash
# Terminal 1
python api_server.py

# Terminal 2
python websocket_server.py
```

#### 4. Interactive CLI Mode
```bash
python mcp_client_interactive.py
```
Enhanced menu system with direct access to all agents and tools.

### 🆕 Latest Updates (June 2025)

#### ✅ Multi-User Concurrency Support
- **Per-Connection MCP Managers**: Each WebSocket connection gets isolated MCP manager
- **True Multi-User Support**: Unlimited agents can connect simultaneously
- **Session Isolation**: Independent tool access and agent context per connection
- **Concurrent Connection Fix**: Resolved Agent 93/188 interference issue

#### ✅ Enhanced Features
- **MCP Initialization Fix**: Tools load after authentication with correct agent context
- **Dual-Environment MongoDB**: Automatic local/production connection detection
- **AWS Region Support**: Proper S3 configuration for knowledge base
- **Full Session ID Display**: Complete UUID tracking with copy functionality
- **Streamlined Deployment**: All MCP servers cleaned to runtime essentials

### 📁 Chat-Bot File Structure

```
Chat-Bot/
├── api_server.py                    # FastAPI REST API server
├── websocket_server.py              # FastAPI WebSocket server
├── websocket_frontend.html          # Interactive WebSocket UI
├── mcp_client.py                    # Shared MCP client manager
├── mcp_client_interactive.py        # Interactive CLI
├── mcp_servers_list.py              # MCP server configuration
├── mongodb_manager.py               # MongoDB connection manager
├── knowledge_base_server.py         # Vector database MCP server
├── math_server.py                   # Math operations server
├── subagents_server.py              # Sub-agent routing logic
├── hubspot-mcp-server/              # HubSpot CRM (Node.js)
├── google-forms-mcp/                # Google Forms (Node.js)
├── airtable-mcp/                    # Airtable DB (Node.js)
├── [30+ other MCP servers]/         # Additional integrations
└── README.md                        # Comprehensive documentation
```

### 🔧 Chat-Bot Prerequisites

- Python 3.11+
- Node.js 18+ (for MCP servers)
- OpenAI API key
- MongoDB (chat history)
- AWS S3 credentials (knowledge base)
- UnleashX authentication API access

### 💡 Chat-Bot Usage Examples

**REST API:**
```bash
curl -X POST "http://localhost:8001/chat/api/query" \
  -H "Content-Type: application/json" \
  -d '{"message": "How to implement a REST API in Python?"}'
```

**WebSocket (JavaScript):**
```javascript
const token = "your_agent_token";
const ws = new WebSocket(`ws://localhost:8001/chat/ws?token=${token}`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Response:', data.content);
};

ws.send(JSON.stringify({
    query: "What is machine learning?",
    agent_type: "general"
}));
```

---

## 📊 Project 2: Dashboard-Bot - AI Dashboard Generator

### Overview

The **Dashboard-Bot** is an AI-powered dashboard generator that creates interactive data visualizations from MySQL form data using OpenAI's GPT models. It transforms UnleashX form data into beautiful, functional dashboards through natural language descriptions.

**Location**: `./Dashboard-Bot/`

### 🌟 Key Features

#### Intelligent Dashboard Generation
- **🔍 Automatic Schema Analysis**: Analyzes MySQL database form structures and data types
- **🤖 AI Code Generation**: Uses OpenAI GPT-4o-mini to generate complete dashboard code
- **📊 Rich Visualizations**: Creates charts, metrics, tables with Chart.js and Plotly
- **🎨 Modern UI**: Clean, responsive interfaces across all versions
- **🔌 Database Integration**: Seamless MySQL connectivity with error handling
- **🚀 Production Ready**: Caching, error handling, and performance optimizations

#### Multi-Version Evolution
Dashboard-Bot has evolved through **4 distinct versions**, each with different capabilities:

1. **Version 1**: Monolithic Code Generator (Streamlit)
2. **Version 2**: Live Component Renderer (Streamlit split architecture)
3. **Version 3**: API-First with HTML Output (Flask REST API)
4. **Version 4**: MCP Agent Pattern (Advanced AI-driven) ⭐ **Current**

### 🏗️ Dashboard-Bot Architecture (Version 4)

```
┌─────────────────────────────────────────────────────────────┐
│           MCP AGENT-DRIVEN DASHBOARD GENERATION              │
│                                                              │
│  User Prompt: "Show user age distribution"                  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────┐                                       │
│  │  Flask REST API  │  (Port 8001)                          │
│  │   (api_server)   │                                       │
│  └────────┬─────────┘                                       │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────┐                                       │
│  │   MCP Client     │  (LangChain Agent + OpenAI)           │
│  │  (dashboard_     │                                       │
│  │   client.py)     │                                       │
│  └────────┬─────────┘                                       │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────────────────────────────────┐          │
│  │         MCP Dashboard Server Tools           │          │
│  │        (dashboard_server.py)                 │          │
│  │                                              │          │
│  │  • search_exact_form_name()                 │          │
│  │  • search_matching_form_names()             │          │
│  │  • get_table_sample_data()                  │          │
│  │  • execute_sql_query()                      │          │
│  │  • generate_pie_chart()                     │          │
│  │  • generate_bar_graph()                     │          │
│  │  • generate_line_chart()                    │          │
│  │  • generate_metric_component()              │          │
│  └──────────────┬───────────────────────────────┘          │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────┐                          │
│  │     MySQL Database           │                          │
│  │  • form_objects table        │                          │
│  │  • Form data tables          │                          │
│  │  • Workspace filtering       │                          │
│  └──────────────────────────────┘                          │
│                                                              │
│  Output: Clean HTML with Chart.js visualization             │
└─────────────────────────────────────────────────────────────┘
```

### 🤖 Version 4: MCP Agent Pattern (Current)

**Advanced Features:**
- **MCP-Based Architecture**: Model Context Protocol for tool communication
- **Intelligent Form Discovery**: AI automatically finds relevant forms using search patterns
- **Agent-Driven Workflow**: LangChain agent with OpenAI functions for autonomous decisions
- **Multiple Chart Types**: Pie charts, bar graphs, line charts, metric cards
- **Automatic NULL Handling**: Built-in filtering for clean visualizations
- **Workspace-Based Filtering**: Multi-tenant support with workspace ID isolation
- **REST API Only**: Fully API-driven, no CLI or interactive modes
- **Token Authentication**: Secure workspace access via UnleashX tokens

**Available MCP Tools:**
- `search_exact_form_name(form_name)` - Search by exact name match
- `search_matching_form_names(pattern)` - Search using SQL LIKE patterns
- `get_table_sample_data(table_name)` - Understand table structure
- `execute_sql_query(query)` - Execute and validate SQL with NULL handling
- `generate_pie_chart(labels, data)` - Generate pie chart HTML
- `generate_bar_graph(labels, data, x_name, y_name)` - Generate bar chart
- `generate_line_chart(labels, data, x_name, y_name)` - Generate line chart
- `generate_metric_component(value_query, label)` - Generate KPI metric card

### 🚀 Dashboard-Bot Deployment

**Version 4 (Current - MCP Agent):**
```bash
# Terminal 1: Start MCP Dashboard Server
python dashboard_server.py

# Terminal 2: Start API Server
python api_server.py
```

**REST API Endpoints:**
- `GET /chat/forms/health` - Health check and system status
- `GET /chat/forms/list` - List available forms (requires token)
- `GET /chat/forms/generate?prompt=<query>` - Generate dashboard component (requires token)

**Authentication:**
All endpoints require UnleashX session token:
```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/chat/forms/health"
```

### 📊 Version Comparison

| Feature | V1 Monolithic | V2 Live Renderer | V3 API HTML | V4 MCP Agent |
|---------|---------------|------------------|-------------|--------------|
| **Interface** | Streamlit | Streamlit | Flask API | Flask API |
| **Output** | Python files | Live preview | HTML code | HTML code |
| **Form Selection** | Manual | Manual | Manual | **Automatic** |
| **Chart Generation** | GPT-4o-mini | GPT-4o-mini | GPT-4o-mini | **MCP Tools** |
| **Intelligence** | Code gen | Live render | Dual output | **Agent-driven** |
| **Use Case** | Standalone apps | Quick prototype | API integration | **Production** |

### 💡 Dashboard-Bot Usage Examples

**Generate User Demographics Dashboard:**
```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/chat/forms/generate?prompt=Show%20user%20age%20distribution"
```

**Example Queries:**
- "Show me user age distribution"
- "Create a pie chart of bank account types"
- "Display sales data trends over time"
- "Analyze customer demographics by region"

**Response:**
```json
{
  "success": true,
  "component_html": "<div>...Chart.js HTML...</div>",
  "form_used": "user_survey",
  "chart_type": "pie_chart"
}
```

### 📁 Dashboard-Bot File Structure

```
Dashboard-Bot/
├── api_server.py                         # Flask REST API (Current)
├── dashboard_server.py                   # MCP server with tools (Current)
├── dashboard_client.py                   # MCP client library (Current)
├── dashboard_generator.py                # V1: Streamlit monolithic
├── dashboard_generator_frontend.py       # V2: Streamlit frontend
├── dashboard_generator_backend.py        # V2: Backend classes
├── api_test_frontend.html                # V3: HTML test frontend
├── select_queries_testing.py             # Database testing utility
└── README.md                             # Comprehensive documentation
```

### 🔧 Dashboard-Bot Prerequisites

- Python 3.8+
- MySQL database with form data
- OpenAI API key
- UnleashX authentication API

### 🗄️ Database Schema

**form_objects table:**
```sql
CREATE TABLE form_objects (
    OBJECT_NAME VARCHAR(255),
    SECONDARY_TABLE VARCHAR(255),
    WORKSPACE_ID INT,
    STATUS INT DEFAULT 1
);
```

**Form data tables:**
```sql
CREATE TABLE <form_data_table> (
    FIELD_NAME VARCHAR(255),
    FIELD_VALUE LONGTEXT,
    -- additional columns
);
```

---

## 🔍 Project 3: Search-Bot - Knowledge Base Search

### Overview

The **Search-Bot** is an AI-powered search application designed for UnleashX's frontend platform. It enables users to search through content written on their pages using natural language queries, leveraging OpenAI's GPT-4o-mini model for intelligent, context-aware answers.

**Location**: `./Search-Bot/`

### 🌟 Key Features

#### Intelligent Search Capabilities
- **🔐 Token-Based Authentication**: UnleashX API integration for secure access
- **🏢 Multi-Tenant Architecture**: Strict workspace isolation
- **🤖 AI-Powered Search**: Natural language queries with GPT-4o-mini
- **💬 Conversational Context**: Maintains chat history for follow-up questions
- **📊 Usage Tracking**: OpenAI API consumption monitoring per workspace
- **🎨 Modern UI**: Gradient design with real-time chat interface

#### Core Functionality
- **Intelligent Search**: Natural language queries across user-created pages
- **Contextual Conversations**: Maintains history for follow-up questions
- **Page Attribution**: Automatically identifies source pages used in answers
- **Knowledge Base Summary**: Quick overview of all available pages
- **Multi-Database Support**: MySQL (content) + MongoDB (chat history)

### 🏗️ Search-Bot Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SEARCH-BOT SYSTEM                         │
│                                                              │
│  Frontend (HTML/JS) ──► Token ──► Flask App                 │
│                                      │                       │
│                                      ▼                       │
│                          ┌─────────────────────┐            │
│                          │ Token Verification  │            │
│                          │  (UnleashX API)     │            │
│                          └──────────┬──────────┘            │
│                                     │                        │
│                          Extract workspace_id               │
│                                     │                        │
│                ┌────────────────────┼────────────────┐      │
│                ▼                    ▼                ▼      │
│         ┌──────────┐         ┌──────────┐    ┌──────────┐ │
│         │  MySQL   │         │ MongoDB  │    │ OpenAI   │ │
│         │  Pages   │         │   Chat   │    │ GPT-4o   │ │
│         │ Content  │         │ History  │    │   mini   │ │
│         └──────────┘         └──────────┘    └──────────┘ │
│                                                              │
│  Output: AI Answer + Referenced Pages + Usage Stats         │
└─────────────────────────────────────────────────────────────┘
```

### 🔐 Security Architecture

**Multi-Layered Security:**
1. **Authentication Layer**: Token verification via UnleashX API
2. **Authorization Layer**: workspace_id extraction from token
3. **Data Isolation Layer**: All queries filtered by workspace_id
4. **Validation Layer**: Mandatory workspace_id checks
5. **Audit Layer**: IP address and user agent tracking

### 🚀 Search-Bot Deployment

```bash
python app.py
```

**Access:** `http://localhost:5002/chat/pages/`

### 📡 API Endpoints

#### POST /chat/pages/search
Search through pages and get AI-powered answers.

**Request:**
```json
{
  "query": "What is the contact information for the project?"
}
```

**Response:**
```json
{
  "success": true,
  "query": "What is the contact information...",
  "workspace_id": 123,
  "workspace_name": "My Workspace",
  "answer": "The contact information is...",
  "referenced_pages_info": [
    {"page_id": 456, "page_title": "Contact Information"}
  ],
  "usage_info": {
    "prompt_tokens": 245,
    "completion_tokens": 89,
    "total_tokens": 334
  }
}
```

#### GET /chat/pages/summary
Get overview of all available pages in knowledge base.

#### GET /chat/pages/test-database-connections
Test MySQL and MongoDB connectivity.

### 🗄️ Search-Bot Database Schema

**MySQL - page_schema:**
```sql
CREATE TABLE page_schema (
    ID INT PRIMARY KEY,
    TITLE VARCHAR(255),
    WORKSPACE_ID INT,
    STATUS TINYINT
);
```

**MySQL - element_schema:**
```sql
CREATE TABLE element_schema (
    PAGE_ID INT,
    ELEMENT_TYPE VARCHAR(50),
    CONTENT TEXT,
    ELEMENT_INDEX INT,
    STATUS TINYINT
);
```

**MySQL - openai_usage:**
```sql
CREATE TABLE openai_usage (
    ID INT PRIMARY KEY AUTO_INCREMENT,
    COMPANY_ID INT,
    WORKSPACE_ID INT,
    MODEL VARCHAR(50),
    TOTAL_TOKENS_USED INT,
    PROMPT_TOKENS INT,
    COMPLETION_TOKENS INT,
    REQUEST_COUNT INT,
    CREATED_AT TIMESTAMP,
    UPDATED_AT TIMESTAMP
);
```

**MongoDB - search_bot_chat_history:**
```json
{
  "message_content": "string",
  "sender_type": "user|bot",
  "timestamp": "ISODate",
  "workspace_id": "number",
  "ip_address": "string",
  "user_agent": "string",
  "referenced_pages_info": [
    {"page_id": "number", "page_title": "string"}
  ]
}
```

### 📁 Search-Bot File Structure

```
Search-Bot/
├── app.py                  # Flask application & API routes
├── search_bot.py           # AI search engine core
├── database.py             # MySQL database manager
├── mongo_manager.py        # MongoDB manager
├── index.html              # Frontend chat interface
└── README.md               # Comprehensive documentation
```

### 🔧 Search-Bot Prerequisites

- Python 3.8+
- MySQL 8.0+
- MongoDB 6.0+
- OpenAI API key
- UnleashX API access

### 💡 Search-Bot Usage

**Web Interface:**
1. Open `http://localhost:5002/chat/pages/`
2. Enter authentication token
3. Ask questions about your pages
4. View AI-generated answers with source attribution

**Example Queries:**
- "What are the project deadlines?"
- "Show me all contact information"
- "What was discussed in the last meeting?"

---

## 🛠️ Technology Stack

### Backend Frameworks
- **FastAPI** - Modern async web framework (Chat-Bot, Dashboard-Bot)
- **Flask** - Lightweight web framework (Dashboard-Bot, Search-Bot)
- **Streamlit** - Dashboard visualization (Dashboard-Bot legacy versions)

### AI & Language Models
- **OpenAI GPT-4o** - Advanced reasoning (Chat-Bot routing)
- **OpenAI GPT-4o-mini** - Efficient responses (All projects)
- **LangChain** - Agent orchestration (Chat-Bot, Dashboard-Bot)
- **Model Context Protocol (MCP)** - Tool communication (Chat-Bot, Dashboard-Bot)

### Databases
- **MongoDB** - Chat history and document storage
- **MySQL** - Relational data (pages, forms, usage)
- **AWS S3** - Knowledge base and file storage

### Frontend
- **HTML5/CSS3** - Modern responsive design
- **JavaScript (Vanilla)** - Real-time interactions
- **WebSocket** - Bidirectional communication (Chat-Bot)
- **Chart.js** - Interactive visualizations (Dashboard-Bot)
- **Plotly** - Advanced charts (Dashboard-Bot)

### Infrastructure
- **Node.js 18+** - MCP server runtime
- **Python 3.8+** - Core application runtime
- **HTTPX** - Async HTTP client
- **PyMongo** - MongoDB driver
- **mysql-connector-python** - MySQL driver

---

## 🚀 Quick Start

### Prerequisites

1. **Install Python 3.8+**
2. **Install Node.js 18+** (for Chat-Bot and Dashboard-Bot MCP servers)
3. **Install MongoDB** (or use MongoDB Atlas)
4. **Install MySQL 8.0+**
5. **Obtain API Keys:**
   - OpenAI API key
   - AWS credentials (for Chat-Bot knowledge base)
   - UnleashX authentication API access

### Installation Steps

#### 1. Clone Repository
```bash
git clone <repository-url>
cd ChatBot-DashboardBot-and-SearchBot
```

#### 2. Set Up Chat-Bot
```bash
cd Chat-Bot
pip install -r requirements.txt

# Install Node.js dependencies for MCP servers
cd hubspot-mcp-server && npm install && cd ..
cd google-forms-mcp && npm install && cd ..
cd airtable-mcp && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start servers
python api_server.py          # Terminal 1
python websocket_server.py    # Terminal 2
```

#### 3. Set Up Dashboard-Bot
```bash
cd ../Dashboard-Bot
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start servers
python dashboard_server.py    # Terminal 1
python api_server.py          # Terminal 2
```

#### 4. Set Up Search-Bot
```bash
cd ../Search-Bot
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start server
python app.py
```

---

## 🔗 Common Features

### Shared Across All Projects

#### 🔐 Token-Based Authentication
All three systems use UnleashX API for secure token verification:
```bash
# Example authentication flow
Token → UnleashX API → User Data → workspace_id → Data Access
```

#### 🏢 Multi-Tenant Architecture
- **Workspace Isolation**: All data access scoped to authenticated workspace
- **Cross-Workspace Prevention**: Mandatory workspace_id validation
- **Audit Trail**: IP address and user agent tracking

#### 💾 MongoDB Chat History
- **Shared Collection Strategy**: Each bot uses its own collection
  - Chat-Bot: `chat_agent_chat_history`
  - Search-Bot: `search_bot_chat_history`
  - Dashboard-Bot: (API-only, no chat history)
- **Dual-Environment Support**: Local (authenticated) / Production (IP whitelisted)
- **Session Tracking**: UUID-based session management

#### 🤖 OpenAI Integration
- **Cost Optimization**: Uses GPT-4o-mini for most operations
- **Usage Tracking**: Per-workspace token consumption monitoring
- **Error Handling**: Graceful fallbacks and retry logic

#### 🛡️ Security Features
- Token verification on every request
- Workspace-based data isolation
- SQL injection prevention
- Rate limiting (configurable)
- Comprehensive logging

---

## ⚙️ Environment Setup

### Shared Environment Variables

Create `.env` file in each project directory:

```env
# OpenAI Configuration (All Projects)
OPENAI_API_KEY=your_openai_api_key

# MySQL Configuration (Dashboard-Bot, Search-Bot)
MYSQL_HOST=localhost
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

# MongoDB Configuration (Chat-Bot, Search-Bot)
MONGODB_URI=mongodb://localhost:27017/masterDB
MONGODB_DB_NAME=masterDB
MONGODB_USERNAME=your_username
MONGODB_PASSWORD=your_password
MONGODB_HOST=localhost:27017

# AWS Configuration (Chat-Bot only)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_BUCKET_NAME=your_s3_bucket
AWS_REGION=your_region

# UnleashX API (All Projects)
UNLEASHX_URL=https://your-unleashx-domain.com

# Project-Specific Ports
# Chat-Bot: 8001
# Dashboard-Bot: 8001
# Search-Bot: 5002
```

### Project-Specific Variables

**Chat-Bot Additional:**
```env
# HubSpot CRM
HUBSPOT_ACCESS_TOKEN=your_token

# Google Forms
GFORMS_ACCESS_TOKEN=your_token
GFORMS_REFRESH_TOKEN=your_refresh_token

# Airtable
AIRTABLE_API_KEY=your_api_key
```

---

## 🔒 Security & Multi-Tenancy

### Authentication Flow

```
User Request
    ↓
Extract Token from Headers
    ↓
Validate Token via UnleashX API
    ↓
Extract User Metadata (workspace_id, company_id)
    ↓
Apply Workspace Filters to All Queries
    ↓
Return Workspace-Isolated Data
```

### Security Best Practices

1. **Always Validate Tokens**: Never trust client-provided workspace_id
2. **Use HTTPS**: Enable SSL/TLS in production
3. **Rate Limiting**: Implement per-workspace rate limits
4. **Audit Logging**: Track all data access with IP/user agent
5. **Environment Variables**: Never commit credentials to git
6. **SQL Parameterization**: Prevent SQL injection attacks
7. **CORS Configuration**: Restrict allowed origins in production

### Multi-Tenant Isolation

| Component | Isolation Method |
|-----------|-----------------|
| **Database Queries** | WHERE workspace_id = ? |
| **S3 Storage** | Agent-specific prefixes |
| **Chat History** | workspace_id field filter |
| **API Responses** | Token-verified workspace data only |
| **WebSocket Connections** | Per-connection managers |

---

## 📊 System Comparison Matrix

| Feature | Chat-Bot | Dashboard-Bot | Search-Bot |
|---------|----------|---------------|------------|
| **Primary Purpose** | Multi-agent conversations | Data visualization | Knowledge base search |
| **AI Model** | GPT-4o + GPT-4o-mini | GPT-4o-mini | GPT-4o-mini |
| **Architecture** | MCP + WebSocket + REST | MCP + REST | REST API |
| **Deployment Modes** | 3 (API/WS/CLI) | 4 versions | 1 (API + UI) |
| **Database** | MongoDB + S3 | MySQL | MySQL + MongoDB |
| **Agents** | 4 specialized | 1 MCP agent | 1 search agent |
| **Real-Time** | Yes (WebSocket) | No | No |
| **Knowledge Base** | 116+ docs (S3) | Form data (MySQL) | Page content (MySQL) |
| **Concurrency** | Per-connection managers | N/A | Standard |
| **Port** | 8001 | 8001 | 5002 |
| **Complexity** | High | Medium | Low |
| **Use Case** | General chatbot | Dashboard generation | Page search |

---

## 🧪 Testing

### Chat-Bot Testing
```bash
# Health check
curl http://localhost:8001/health

# WebSocket test
# Open browser: http://localhost:8001/chat/ws/test

# REST API test
curl -X POST http://localhost:8001/chat/api/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What is machine learning?"}'
```

### Dashboard-Bot Testing
```bash
# Health check
curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/chat/forms/health

# List forms
curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/chat/forms/list

# Generate dashboard
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/chat/forms/generate?prompt=Show%20user%20stats"
```

### Search-Bot Testing
```bash
# Database connections
curl http://localhost:5002/chat/pages/test-database-connections

# Search query
curl -X POST http://localhost:5002/chat/pages/search \
  -H "Content-Type: application/json" \
  -H "token: your-token" \
  -d '{"query": "What are the project deadlines?"}'

# Summary
curl -H "token: your-token" \
     http://localhost:5002/chat/pages/summary
```

---

## 🤝 Contributing

We welcome contributions to any of the three projects!

### Contribution Guidelines

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Code Style

- **Python**: Follow PEP 8
- **JavaScript**: Use ESLint configuration
- **Documentation**: Add docstrings and comments
- **Security**: Include validation and error handling
- **Testing**: Add unit tests for new features

### Areas for Contribution

- **Chat-Bot**: New MCP server integrations, additional sub-agents
- **Dashboard-Bot**: New chart types, improved AI prompts
- **Search-Bot**: Enhanced search algorithms, new page element types
- **Documentation**: Tutorials, guides, examples
- **Testing**: Unit tests, integration tests, performance tests

---

## 📈 Performance Optimization

### Database Optimization
```sql
-- Recommended indexes for Search-Bot
CREATE INDEX idx_workspace ON page_schema(WORKSPACE_ID, STATUS);
CREATE INDEX idx_page_id ON element_schema(PAGE_ID, STATUS);

-- Recommended indexes for Dashboard-Bot
CREATE INDEX idx_workspace_forms ON form_objects(WORKSPACE_ID, STATUS);
```

### Caching Strategies
- **Chat-Bot**: Cache knowledge base embeddings
- **Dashboard-Bot**: Cache form schemas per workspace
- **Search-Bot**: Cache page content for 5 minutes

### Connection Pooling
```python
# MongoDB connection pooling
client = MongoClient(uri, maxPoolSize=50)

# MySQL connection pooling
connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=10,
    **config
)
```

---

## 🐛 Troubleshooting

### Common Issues

#### MongoDB Connection Failed
```bash
# Check MongoDB status
brew services list | grep mongodb

# Test connection
python mongodb_diagnostic.py

# Verify credentials in .env
MONGODB_USERNAME=correct_user
MONGODB_PASSWORD=correct_password  # No quotes!
```

#### OpenAI API Errors
```bash
# Verify API key
echo $OPENAI_API_KEY

# Check credits
# Visit: https://platform.openai.com/account/usage
```

#### Token Authentication Failed
```bash
# Verify UnleashX URL
curl https://your-unleashx-domain.com/api/getuser

# Check token format
# Should be raw token, not "Bearer <token>" in headers
```

#### Port Already in Use
```bash
# Find process using port
netstat -ano | findstr :8001

# Kill process (Windows)
taskkill /PID <process_id> /F

# Or change port in respective server file
```

---

## 📄 License

This project is proprietary software developed for UnleashX.

---

## 👨‍💻 Authors

**Prem Bhugra**  
IIT Delhi

---

## 🙏 Acknowledgments

- UnleashX team for platform integration support
- OpenAI for GPT-4o and GPT-4o-mini APIs
- Model Context Protocol (MCP) community
- Flask, FastAPI, and Python community
- Node.js and Chart.js communities

---

## 📞 Support

For issues, questions, or support:

### Project-Specific Issues
- **Chat-Bot**: See `./Chat-Bot/README.md`
- **Dashboard-Bot**: See `./Dashboard-Bot/README.md`
- **Search-Bot**: See `./Search-Bot/README.md`

### General Support
- Create an issue in the repository
- Contact the development team
- Check individual project documentation

---

## 🗺️ Roadmap

### Chat-Bot
- [ ] Additional MCP server integrations
- [ ] Voice interaction support
- [ ] Advanced analytics dashboard
- [ ] Multi-language support

### Dashboard-Bot
- [ ] Support for PostgreSQL and SQLite
- [ ] Advanced chart customization
- [ ] Dashboard templates library
- [ ] Real-time data streaming

### Search-Bot
- [ ] Advanced filtering and sorting
- [ ] Document upload and indexing
- [ ] Multi-language search support
- [ ] Search analytics dashboard

---

## 📚 Additional Resources

### Documentation
- [Chat-Bot Full Documentation](./Chat-Bot/README.md)
- [Dashboard-Bot Full Documentation](./Dashboard-Bot/README.md)
- [Search-Bot Full Documentation](./Search-Bot/README.md)

### External Links
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Flask Documentation](https://flask.palletsprojects.com)

---

**Built with ❤️ for UnleashX by Prem Bhugra**

---

## 📊 Quick Reference

### Service Ports
- **Chat-Bot**: 8001 (REST API + WebSocket)
- **Dashboard-Bot**: 8001 (REST API)
- **Search-Bot**: 5002 (REST API + Web UI)

### Startup Commands
```bash
# Chat-Bot
cd Chat-Bot && python api_server.py & python websocket_server.py

# Dashboard-Bot  
cd Dashboard-Bot && python dashboard_server.py & python api_server.py

# Search-Bot
cd Search-Bot && python app.py
```

### Health Check URLs
- Chat-Bot: `http://localhost:8001/health`
- Dashboard-Bot: `http://localhost:8001/chat/forms/health`
- Search-Bot: `http://localhost:5002/chat/pages/test-database-connections`

---

*Last Updated: October 3, 2025*
