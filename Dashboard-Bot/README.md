# Dashboard-Bot 🚀

AI-powered dashboard generator that creates interactive data visualizations from MySQL form data using OpenAI's GPT models. Transform your Unleashx form data into beautiful, functional dashboards with just a description of what you want to see.

## 📁 Current Project Status

**Version 4 (Current/Active)** - API-driven MCP Agent Architecture:
- ✅ `dashboard_client.py` - MCP client library classes (no CLI)
- ✅ `dashboard_server.py` - MCP server providing agent tools
- ✅ `api_server.py` - Flask REST API with authentication
- ✅ All CLI interactions removed - API-only architecture

**Development/Testing Utilities:**
- 🔧 `select_queries_testing.py` - Database testing utility (CLI for dev purposes)

**Legacy Versions** - Available for reference:
- 📄 `dashboard_generator.py` - Version 1 (Streamlit monolithic)
- 🔄 `dashboard_generator_frontend.py` + `dashboard_generator_backend.py` - Version 2 (Streamlit live renderer)
- 🌐 `api_test_frontend.html` - Version 3 (Simple HTML frontend)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Versions](#project-versions)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Dashboard-Bot analyzes your MySQL database containing form data and generates custom dashboards based on natural language descriptions. It supports multiple deployment approaches from simple code generation to real-time component rendering, API-based integrations, and advanced AI agent-driven workflows.

**Key Capabilities:**
- Automatic form schema analysis from MySQL databases
- AI-powered dashboard component generation using OpenAI GPT models
- Support for multiple data types (numeric, text, date, email)
- Interactive visualizations with Chart.js, Plotly and Streamlit
- Real-time component rendering
- API-first architecture for flexible integrations
- **Advanced MCP agent pattern for intelligent form discovery**
- **Autonomous AI decision-making with minimal user input**

## ✨ Features

- 🔍 **Intelligent Data Analysis**: Automatically analyzes form structures and data types
- 🤖 **AI Code Generation**: Uses OpenAI to generate complete dashboard code
- 📊 **Rich Visualizations**: Creates charts, metrics, tables, and interactive filters
- 🎨 **Modern UI**: Clean, responsive interfaces for all versions
- 🔌 **Database Integration**: Seamless MySQL connectivity with proper error handling
- 📱 **Multi-Format Output**: Code files, live components, and HTML exports
- 🚀 **Production Ready**: Includes caching, error handling, and performance optimizations

## 🔧 Project Versions

This project has evolved through three distinct versions, each with different capabilities and use cases:

### Version 1: Monolithic Code Generator 📄
**File:** `dashboard_generator.py`

**Purpose:** Original standalone Streamlit application that generates complete Python/Streamlit dashboard code files for download.

**Features:**
- Single-file Streamlit application
- Complete database analysis and schema detection
- AI-powered code generation using OpenAI GPT-4o-mini
- Downloadable Python files with complete dashboard code
- Built-in form browsing and database connection testing

**Use Case:** When you need standalone dashboard applications that can be deployed independently.

**Output:** Complete Python/Streamlit code files that users download and run separately.

**How to Run:**
```bash
streamlit run dashboard_generator.py
```

**Workflow:**
1. Connect to MySQL database
2. Select or browse available forms
3. Describe desired dashboard features
4. Generate complete dashboard code
5. Download and run the generated Python file

---

### Version 2: Live Component Renderer 🔄
**Files:** `dashboard_generator_frontend.py` + `dashboard_generator_backend.py`

**Purpose:** Split architecture that renders dashboard components in real-time within the same Streamlit interface.

**Features:**
- Separated frontend and backend logic
- Real-time component generation and display
- Live preview without file downloads
- Streamlit-embedded component rendering
- Shared backend classes for modularity

**Use Case:** When you want immediate visual feedback and don't need standalone applications.

**Output:** Live rendered components displayed directly in the Streamlit interface.

**How to Run:**
```bash
streamlit run dashboard_generator_frontend.py
```

**Architecture:**
- **Backend (`dashboard_generator_backend.py`)**: Contains `DatabaseAnalyzer`, `ComponentGenerator`, `DashboardBackend`, and `ComponentRenderer` classes
- **Frontend (`dashboard_generator_frontend.py`)**: Streamlit UI that calls backend classes and renders components in real-time

**Workflow:**
1. Connect to database through frontend
2. Select form and describe requirements
3. Backend generates components
4. Components render live in the same interface

---

### Version 3: API-First with HTML Output 🌐
**Files:** `api_server.py` + `api_test_frontend.html` + `dashboard_generator_backend.py`

**Purpose:** Modern API-driven architecture that provides both HTML code and live component graphics through REST endpoints.

**Features:**
- RESTful API architecture using Flask
- Modern HTML frontend with embedded CSS/JavaScript
- Dual output: HTML code + live component graphics
- Frontend-agnostic design (any client can use the API)
- Copy-paste ready HTML components
- Professional web interface

**Use Case:** When you need API integrations, want HTML output, or require frontend flexibility.

**Output:** Both HTML code AND live component visualizations with copy-paste functionality.

**Current Limitation:** Single component per request (`max_components: 1`)

**How to Run:**
```bash
# Start the API server
python api_server.py

# Open the test frontend
open api_test_frontend.html
```

**API Endpoints:**
- `GET /`: Health check endpoint
- `GET /api/forms`: List available forms
- `POST /api/generate-components`: Generate dashboard components

**Architecture:**
- **API Server (`api_server.py`)**: Flask REST API exposing component generation endpoints
- **Frontend (`api_test_frontend.html`)**: Modern HTML interface with AJAX calls to API
- **Backend (`dashboard_generator_backend.py`)**: Shared backend logic used by API

**Workflow:**
1. HTML frontend sends form data and requirements to API
2. API processes request using backend classes
3. Returns both HTML code and rendered component graphics
4. Frontend displays live preview and provides copy-paste HTML code

---

### Version 4: MCP Agent Pattern 🤖
**Files:** `dashboard_client.py` + `dashboard_server.py` + `api_server.py`

**Purpose:** Advanced AI agent-driven architecture using Model Context Protocol (MCP) for intelligent form discovery and chart generation with REST API endpoints.

**Features:**
- **MCP-Based Architecture**: Uses Model Context Protocol for tool communication
- **Intelligent Form Discovery**: AI agent automatically finds relevant forms using search patterns
- **Agent-Driven Workflow**: LangChain agent with OpenAI functions for autonomous decision making
- **Multiple Chart Types**: Support for pie charts, bar graphs, line charts, and metric cards with Chart.js
- **Automatic NULL Handling**: Built-in filtering of NULL/empty values for clean visualizations
- **Workspace-Based Filtering**: Forms filtered by workspace ID for multi-tenant support
- **REST API Only**: Fully API-driven architecture with no CLI or interactive modes
- **Real-Time Data Analysis**: Agent analyzes table structures and validates SQL queries
- **Model Flexibility**: Works with both GPT-4o and GPT-4o-mini models
- **Token Authentication**: Secure workspace access via UnleashX session tokens

**Use Case:** When you need intelligent, autonomous dashboard generation through REST API integration with secure workspace isolation.

**Output:** Clean HTML code with Chart.js visualizations, generated through intelligent form discovery and data analysis.

**Architecture:**
- **Client (`dashboard_client.py`)**: MCP client with LangChain agent library classes for the API server
- **Server (`dashboard_server.py`)**: MCP server exposing tools for form search, data analysis, and chart generation
- **API Server (`api_server.py`)**: Flask REST API providing endpoints for health checks, form listing, and component generation
- **Agent Pattern**: Uses the exact MCP pattern from `mcp_client_interactive.py` with `initialize_agent()` and `load_mcp_tools()`

**Available MCP Tools:**
- `search_exact_form_name(form_name)`: Search for forms by exact name match
- `search_matching_form_names(pattern)`: Search for forms using SQL LIKE patterns
- `get_table_sample_data(table_name)`: Get sample data from secondary tables to understand structure
- `execute_sql_query(query)`: Execute and validate SQL queries with automatic NULL handling
- `generate_pie_chart(labels_query, data_query)`: Generate pie chart HTML with Chart.js
- `generate_bar_graph(labels_query, data_query, x_name, y_name)`: Generate bar chart HTML
- `generate_line_chart(labels_query, data_query, x_name, y_name)`: Generate line chart HTML
- `generate_metric_component(value_query, label)`: Generate metric card HTML for KPIs and statistics

**How to Run:**

*API Server Mode (Recommended):*
```bash
# Terminal 1: Start MCP Dashboard Server
python dashboard_server.py

# Terminal 2: Start API Server
python api_server.py
```

**Available REST API Endpoints:**
- `GET /chat/forms/health` - Health check and system status
- `GET /chat/forms/list` - List available forms for authenticated workspace
- `GET /chat/forms/generate` - Generate components using MCP agent with user prompt

**Authentication:**
All endpoints require UnleashX session token in the `Authorization` header:
```
Authorization: Bearer <your-unleashx-token>
```

**Workflow:**
1. Initialize MCP agent with workspace-specific context
2. Agent uses form search tools to find relevant forms based on user query
3. Agent analyzes form data structure using sample data tools
4. Agent generates and validates SQL queries
5. Agent selects appropriate chart type and generates HTML visualization
6. Returns clean, ready-to-use HTML with Chart.js

**Key Advantages:**
- **Zero Manual Form Selection**: Agent intelligently discovers relevant forms
- **Autonomous Decision Making**: AI chooses chart types and handles edge cases
- **Robust Data Handling**: Automatic NULL/empty value filtering
- **Scalable Architecture**: MCP pattern allows easy addition of new tools
- **Model Agnostic**: Consistent performance across different GPT models

**Current Status:** ✅ **Complete and Production Ready**

## 🚀 Setup & Installation

### Prerequisites

- Python 3.8+
- MySQL database with form data
- OpenAI API key

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd Dashboard-Bot
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp .env.example .env  # Create .env file
```

Edit `.env` file with your credentials:
```env
# Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Version 4 MCP Configuration (optional)
MCP_WORKSPACE_ID=98  # Set by client automatically
```

### Database Schema Requirements

Your MySQL database should have the following structure:

**form_objects table:**
```sql
CREATE TABLE form_objects (
    OBJECT_NAME VARCHAR(255),
    SECONDARY_TABLE VARCHAR(255),
    STATUS INT DEFAULT 1
);
```

**Secondary tables (form data):**
```sql
CREATE TABLE your_form_data_table (
    FIELD_NAME VARCHAR(255),
    FIELD_VALUE LONGTEXT,
    -- other columns as needed
);
```

## 💻 Usage

### Version 1: Monolithic Generator

```bash
streamlit run dashboard_generator.py
```

1. Test database connection
2. Browse available forms or enter form name
3. Describe your dashboard requirements
4. Generate and download complete dashboard code

### Version 2: Live Renderer

```bash
streamlit run dashboard_generator_frontend.py
```

1. Connect to database
2. Select form and describe needs
3. View components rendered in real-time
4. Iterate and refine as needed

### Version 3: API + HTML Frontend

```bash
# Terminal 1: Start API server
python api_server.py

# Terminal 2: Open HTML frontend
open api_test_frontend.html
# or serve it with a local server:
python -m http.server 8080
```

1. Access the HTML interface
2. Enter form details and requirements
3. Generate components via API
4. Copy HTML code or view live graphics

### Version 4: MCP Agent Pattern

**API Server Mode:**
```bash
# Terminal 1: Start MCP Dashboard Server
python dashboard_server.py

# Terminal 2: Start API Server
python api_server.py
```

**Available REST API Endpoints:**
- `GET /chat/forms/health` - Health check and system status
- `GET /chat/forms/list` - List available forms for authenticated workspace
- `GET /chat/forms/generate` - Generate components using MCP agent

**Authentication:**
All endpoints require UnleashX session token in the `Authorization` header:
```bash
curl -H "Authorization: Bearer <your-token>" \
     "http://localhost:8001/chat/forms/health"
```

**Example API Usage:**
```bash
# Health check
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/chat/forms/health"

# List forms
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/chat/forms/list"

# Generate component
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8001/chat/forms/generate?prompt=Show%20user%20age%20distribution"
```

**Example Queries for Version 4:**
- "Show me user age distribution"
- "Create a pie chart of bank account types"  
- "Display sales data trends over time"
- "Analyze customer demographics by region"

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Version |
|----------|-------------|----------|---------|
| `MYSQL_HOST` | MySQL host address | Yes | All |
| `MYSQL_USER` | MySQL username | Yes | All |
| `MYSQL_PASSWORD` | MySQL password | Yes | All |
| `MYSQL_DATABASE` | MySQL database name | Yes | All |
| `OPENAI_API_KEY` | OpenAI API key | Yes | All |
| `MCP_WORKSPACE_ID` | Workspace ID for MCP server | Auto-set | V4 Only |

### API Configuration

The API server runs on `http://localhost:5000` by default. You can modify the host and port in `api_server.py`:

```python
if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)
```

## 📚 API Documentation

### Endpoints

#### GET /

Health check endpoint to verify API server status.

**Response:**
```json
{
    "status": "healthy",
    "service": "Dashboard Component Generator API",
    "version": "1.0.0",
    "backend_status": "connected"
}
```

#### GET /api/forms

Get list of available forms from the database.

**Response:**
```json
{
    "success": true,
    "forms": [
        {
            "OBJECT_NAME": "user_survey",
            "SECONDARY_TABLE": "user_survey_data"
        }
    ],
    "count": 1
}
```

#### POST /api/generate-components

Generate dashboard components based on form data and requirements.

**Request Body:**
```json
{
    "user_prompt": "Create analytics dashboard with user demographics",
    "form_name": "user_survey",
    "max_components": 4
}
```

**Parameters:**
- `user_prompt` (required): Description of the dashboard components you want to generate
- `form_name` (optional): Specific form to use. If not provided, the LLM will automatically select the most appropriate form based on your prompt
- `max_components` (optional): Maximum number of components to generate (default: 4)

**Response:**
```json
{
    "success": true,
    "selected_form": "user_survey",
    "components": [
        {
            "id": "component_1",
            "type": "chart",
            "title": "User Demographics",
            "description": "Distribution of user data",
            "html": "<div>...Chart.js HTML...</div>",
            "metadata": {
                "chart_type": "bar",
                "data_processing": {},
                "visualization": {},
                "data_shape": {
                    "rows": 150,
                    "columns": ["age", "gender", "location"]
                }
            },
            "data_summary": {
                "record_count": 150,
                "has_data": true,
                "render_success": true
            }
        }
    ],
    "form_info": {
        "total_fields": 5,
        "table_name": "user_survey_data"
    },
    "generation_time": 2.34,
    "generated_at": "2025-06-08 10:30:00",
    "total_components": 1
}
```

## 🔄 Evolution & Migration

### From Version 1 to Version 2
- Extract classes to `dashboard_generator_backend.py`
- Create new frontend in `dashboard_generator_frontend.py`
- Implement real-time rendering

### From Version 2 to Version 3
- Create Flask API in `api_server.py`
- Build HTML frontend with modern UI
- Add dual output capability (HTML + graphics)

### Choosing the Right Version

| Use Case | Recommended Version |
|----------|-------------------|
| Standalone dashboard applications | Version 1 |
| Quick prototyping with live preview | Version 2 |
| Integration with other systems | Version 3 |
| HTML component generation | Version 3 |
| API-based architecture | Version 3 |
| **Intelligent AI-driven dashboard generation** | **Version 4** |
| **Autonomous form discovery and analysis** | **Version 4** |
| **Advanced agent-based workflows** | **Version 4** |
| **Production-ready MCP architecture** | **Version 4** |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the database connection using the built-in test function
2. Verify your `.env` file configuration
3. Ensure your OpenAI API key has sufficient credits
4. Review the form data structure in your MySQL database

## 🚀 Future Enhancements

- Support for multiple database types (PostgreSQL, SQLite)
- Advanced chart types and customization options
- User authentication and session management
- Dashboard templates and themes
- Export to multiple formats (PDF, Excel, PowerPoint)
- Real-time data updates and streaming
- Multi-component support in API version
- Advanced AI prompt engineering for better code generation
