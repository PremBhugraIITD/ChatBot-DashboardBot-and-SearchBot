# 🔍 Search Bot - AI-Powered Knowledge Base Search

> An enterprise-grade, multi-tenant search bot built for UnleashX that enables users to intelligently search through their page content using OpenAI's GPT-4o-mini.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-purple.svg)](https://openai.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-green.svg)](https://www.mongodb.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Security](#-security)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Usage](#-usage)
- [Database Schema](#-database-schema)
- [Project Structure](#-project-structure)
- [Technology Stack](#-technology-stack)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

**Search Bot** is a sophisticated AI-powered search application designed for UnleashX's frontend platform. It allows users to search through content written on their pages using natural language queries. The bot leverages OpenAI's GPT-4o-mini model to provide intelligent, context-aware answers while maintaining strict multi-tenant security and conversation history.

### Key Highlights

- 🔐 **Token-based Authentication** with UnleashX API integration
- 🏢 **Multi-tenant Architecture** with workspace isolation
- 🤖 **AI-Powered Search** using OpenAI GPT-4o-mini
- 💬 **Conversational Context** with chat history support
- 📊 **Usage Tracking** for OpenAI API consumption
- 🎨 **Modern UI** with gradient design and real-time chat interface

---

## ✨ Features

### Core Functionality

- **Intelligent Search**: Natural language queries across all user-created pages
- **Contextual Conversations**: Maintains conversation history for follow-up questions
- **Page Attribution**: Automatically identifies and references source pages used in answers
- **Knowledge Base Summary**: Quick overview of all available pages
- **Multi-database Support**: MySQL for content, MongoDB for chat history

### Security Features

- **Token Verification**: Every request validated against UnleashX API
- **Workspace Isolation**: Strict data separation between workspaces
- **IP & User Agent Tracking**: Audit trail for all interactions
- **Secure Headers**: Multiple authentication header formats supported

### Monitoring & Analytics

- **OpenAI Usage Tracking**: Per-workspace token consumption monitoring
- **Request Counting**: Tracks number of API calls per workspace
- **Database Health Checks**: Built-in connection testing endpoints
- **Detailed Logging**: Comprehensive error and info logging

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (HTML/JS)                   │
│              Modern Chat Interface with Token Auth           │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/REST
┌────────────────────────▼────────────────────────────────────┐
│                     Flask Application (app.py)               │
│         • Token Verification  • Request Routing              │
│         • Response Formatting • Error Handling               │
└─────┬──────────────────┬──────────────────┬─────────────────┘
      │                  │                  │
      │                  │                  │
┌─────▼──────┐   ┌──────▼──────┐   ┌──────▼──────────┐
│  UnleashX  │   │  SearchBot  │   │  MongoDBManager │
│    API     │   │ (AI Engine) │   │  (Chat History) │
│ (Token Auth)│   │             │   │                 │
└────────────┘   └──────┬──────┘   └─────────────────┘
                        │
                 ┌──────▼──────┐
                 │  Database   │
                 │  (MySQL)    │
                 │ Pages & Usage│
                 └──────┬──────┘
                        │
                 ┌──────▼──────┐
                 │  OpenAI API │
                 │ GPT-4o-mini │
                 └─────────────┘
```

### Data Flow

1. **User Request** → Frontend sends query with authentication token
2. **Token Verification** → Flask app validates token with UnleashX API
3. **Workspace Extraction** → workspace_id extracted from authenticated user data
4. **Data Retrieval** → Pages fetched from MySQL filtered by workspace_id
5. **Context Building** → Last 10 chat messages retrieved from MongoDB
6. **AI Processing** → OpenAI generates answer with page references
7. **Usage Tracking** → Token consumption recorded in MySQL
8. **Chat Storage** → User query and bot response saved to MongoDB
9. **Response Delivery** → Answer with referenced pages returned to user

---

## 🔐 Security

### Multi-layered Security Architecture

#### 1. Authentication Layer
- Token-based authentication via UnleashX API
- Supports multiple header formats: `token`, `Token`, `Authorization: Bearer`
- Invalid tokens result in immediate 401 Unauthorized response

#### 2. Authorization Layer
- `workspace_id` extracted from authenticated token response
- All data access scoped to authenticated workspace
- Cross-workspace data access prevention

#### 3. Data Isolation Layer
- **Mandatory workspace_id validation** on all database queries
- Explicit security checks with ValueError exceptions
- SQL queries filtered by `WORKSPACE_ID` column

#### 4. Audit Layer
- Client IP address tracking
- User agent logging
- Timestamp recording for all interactions
- Complete chat history with workspace attribution

### Security Validations

```python
# Example: Mandatory workspace_id check
if workspace_id is None:
    raise ValueError("SECURITY ERROR: workspace_id is mandatory")
```

---

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- MySQL 8.0+
- MongoDB 6.0+
- OpenAI API key
- Access to UnleashX API

### Step-by-Step Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Search-Bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize databases**
   - Ensure MySQL database exists with required tables
   - MongoDB connection will auto-initialize collections

6. **Run the application**
   ```bash
   python app.py
   ```

The application will start on `http://0.0.0.0:5002`

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=unleashx_db

# MongoDB Configuration
MONGODB_HOST=43.204.206.231:27017
MONGODB_PORT=27017
MONGODB_DB_NAME=masterDB
MONGODB_USERNAME=your_username  # Optional for deployed environments
MONGODB_PASSWORD=your_password  # Optional for deployed environments

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# UnleashX API Configuration
UNLEASHX_URL=https://your-unleashx-domain.com
```

### MongoDB Connection Modes

The system supports two connection modes:

- **Local Development**: Uses username/password authentication
- **Deployed Environment**: No authentication (relies on IP whitelisting)

The connection mode is automatically detected based on credential availability.

---

## 📡 API Documentation

### Base URL
```
http://localhost:5002
```

---

### 1. Search Endpoint

**POST** `/chat/pages/search`

Search through pages and get AI-powered answers.

#### Headers
```
Content-Type: application/json
token: <your-session-token>
```

#### Request Body
```json
{
  "query": "What is the contact information for the project?"
}
```

#### Success Response (200 OK)
```json
{
  "success": true,
  "query": "What is the contact information for the project?",
  "workspace_id": 123,
  "workspace_name": "My Workspace",
  "user": "user@example.com",
  "answer": "The contact information is...\n\nPAGES_USED: Contact Information",
  "referenced_pages_info": [
    {
      "page_id": 456,
      "page_title": "Contact Information"
    }
  ],
  "usage_info": {
    "prompt_tokens": 245,
    "completion_tokens": 89,
    "total_tokens": 334
  }
}
```

#### Error Responses
```json
// 401 Unauthorized
{
  "error": "Authentication token is required in headers"
}

// 400 Bad Request
{
  "error": "Please provide a search query"
}

// 403 Forbidden
{
  "error": "No workspace associated with this user"
}
```

---

### 2. Summary Endpoint

**GET** `/chat/pages/summary`

Get an overview of all available pages in the knowledge base.

#### Headers
```
token: <your-session-token>
```

#### Success Response (200 OK)
```json
{
  "success": true,
  "workspace_id": 123,
  "workspace_name": "My Workspace",
  "user": "user@example.com",
  "summary": "Knowledge Base Summary for Workspace 123 (5 pages):\n\n• Contact Information (ID: 456) - 3 content elements\n• Project Details (ID: 457) - 8 content elements\n..."
}
```

---

### 3. Database Test Endpoint

**GET** `/chat/pages/test-database-connections`

Test connectivity to MySQL and MongoDB.

#### Headers
None required (public endpoint)

#### Success Response (200 OK)
```json
{
  "success": true,
  "connections": {
    "mysql": {
      "status": "success",
      "message": "MySQL connected successfully"
    },
    "mongodb": {
      "status": "success",
      "message": "MongoDB connected successfully",
      "version": "6.0.5",
      "database": "masterDB"
    }
  }
}
```

---

### 4. Frontend Interface

**GET** `/chat/pages/`

Serves the HTML chat interface.

---

## 🎯 Usage

### Web Interface

1. **Open the application**
   ```
   http://localhost:5002/chat/pages/
   ```

2. **Enter authentication token**
   - Obtain session token from UnleashX
   - Paste into the "Authentication Token" field

3. **Ask questions**
   - Type natural language queries about your pages
   - Examples:
     - "What are the project deadlines?"
     - "Show me all contact information"
     - "What was discussed in the last meeting?"

4. **View responses**
   - AI-generated answers appear in chat bubbles
   - Referenced pages are tracked and stored

### Programmatic Usage

```python
import requests

# Authenticate and search
url = "http://localhost:5002/chat/pages/search"
headers = {
    "Content-Type": "application/json",
    "token": "your-session-token"
}
data = {
    "query": "What is the project timeline?"
}

response = requests.post(url, headers=headers, json=data)
result = response.json()

print(result['answer'])
print(f"Pages used: {result['referenced_pages_info']}")
```

---

## 🗄️ Database Schema

### MySQL Tables

#### `page_schema`
```sql
ID              INT PRIMARY KEY
TITLE           VARCHAR(255)
WORKSPACE_ID    INT (SECURITY CRITICAL)
STATUS          TINYINT (1 = active)
...
```

#### `element_schema`
```sql
PAGE_ID         INT (FK to page_schema.ID)
ELEMENT_TYPE    VARCHAR(50) (TEXT, HEADER1, HEADER2, HEADER3, 
                              NUMBERED_LIST, BULLET_LIST, TODO_LIST)
CONTENT         TEXT
ELEMENT_INDEX   INT
STATUS          TINYINT (1 = active)
...
```

#### `openai_usage`
```sql
ID                  INT PRIMARY KEY AUTO_INCREMENT
COMPANY_ID          INT
WORKSPACE_ID        INT (SECURITY CRITICAL)
MODEL               VARCHAR(50)
TOTAL_TOKENS_USED   INT
PROMPT_TOKENS       INT
COMPLETION_TOKENS   INT
REQUEST_TYPE        VARCHAR(20) ('text')
REQUEST_COUNT       INT
CREDENTIAL_USED     VARCHAR(50) ('internal')
CREATED_AT          TIMESTAMP
UPDATED_AT          TIMESTAMP
```

### MongoDB Collections

#### `search_bot_chat_history`
```javascript
{
  _id: ObjectId,
  message_content: String,
  sender_type: "user" | "bot",
  timestamp: ISODate,
  workspace_id: Number,
  ip_address: String,
  user_agent: String,
  referenced_pages_info: [
    {
      page_id: Number,
      page_title: String
    }
  ]  // Only for bot messages
}
```

---

## 📁 Project Structure

```
Search-Bot/
│
├── app.py                  # Flask application & API routes
├── search_bot.py           # AI search engine core logic
├── database.py             # MySQL database manager
├── mongo_manager.py        # MongoDB connection & operations
├── index.html              # Frontend chat interface
│
├── .env                    # Environment variables (create from .env.example)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### File Descriptions

| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `app.py` | Main application | Token verification, routing, request handling |
| `search_bot.py` | AI engine | OpenAI integration, page attribution, formatting |
| `database.py` | MySQL manager | Page retrieval, usage tracking |
| `mongo_manager.py` | MongoDB manager | Chat history storage and retrieval |
| `index.html` | Frontend UI | User interface, WebSocket-like real-time chat |

---

## 🛠️ Technology Stack

### Backend
- **Flask** - Lightweight web framework
- **OpenAI API** - GPT-4o-mini for intelligent search
- **MySQL Connector** - Database connectivity
- **PyMongo** - MongoDB Python driver
- **HTTPX** - Async HTTP client for token verification
- **python-dotenv** - Environment variable management

### Frontend
- **HTML5/CSS3** - Modern responsive design
- **Vanilla JavaScript** - No frameworks, pure JS
- **Fetch API** - Async HTTP requests
- **CSS Gradients** - Beautiful UI styling

### Databases
- **MySQL 8.0+** - Relational data (pages, elements, usage)
- **MongoDB 6.0+** - Document store (chat history)

### AI & APIs
- **OpenAI GPT-4o-mini** - Language model
- **UnleashX API** - Authentication service

---

## 🎨 AI Prompt Engineering

### System Prompt Strategy

The bot uses a carefully crafted system prompt that:

1. **Establishes Role**: Helpful search assistant with knowledge base access
2. **Provides Context**: Includes last 10 conversation messages
3. **Sets Constraints**: Answer only from knowledge base
4. **Enforces Attribution**: Mandatory `PAGES_USED:` footer
5. **Controls Tone**: Concise yet comprehensive responses

### Page Attribution Mechanism

The AI is instructed to end every response with:
```
PAGES_USED: Page Title 1, Page Title 2, Page Title 3
```

This enables:
- Accurate source tracking
- User transparency
- Database reference storage
- Follow-up question context

### Fallback Strategy

If AI doesn't provide `PAGES_USED:` section:
1. Parse response text for page title mentions
2. Case-insensitive matching
3. Deduplicate by page_id
4. Return best-effort page references

---

## 📊 Usage Tracking System

### Upsert Pattern

The system implements a smart upsert pattern for OpenAI usage:

- **First Request**: Creates new record with `REQUEST_COUNT=1`
- **Subsequent Requests**: Updates existing record, increments counter
- **One Row Per Workspace**: Consolidated usage per workspace

### Tracked Metrics

- `prompt_tokens` - Input tokens consumed
- `completion_tokens` - Output tokens generated
- `total_tokens` - Sum of prompt + completion
- `request_count` - Number of API calls
- `model` - OpenAI model used (gpt-4o-mini)

### Usage Retrieval

```python
from database import Database

db = Database()
stats = db.get_usage_stats(workspace_id=123)

for stat in stats:
    print(f"Model: {stat['MODEL']}")
    print(f"Total tokens: {stat['TOTAL_TOKENS_USED']}")
    print(f"Requests: {stat['REQUEST_COUNT']}")
```

---

## 🔄 Conversation Context

### Context Management

The bot maintains conversation continuity by:

1. **Storing all messages** in MongoDB with workspace isolation
2. **Retrieving last 10 messages** on each query
3. **Including in prompt** formatted as conversation history
4. **Enabling follow-up questions** like "tell me more about that"

### Example Flow

```
User: "What are the project deadlines?"
Bot: "The project has three deadlines: Alpha (Oct 15), Beta (Nov 1), Final (Dec 1)."

User: "Tell me more about the Beta deadline"
Bot: "The Beta deadline on November 1st includes feature freeze and testing phase..."
```

The second query understands "Beta deadline" from conversation context.

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `debug=False` in `app.py`
- [ ] Use production-grade WSGI server (Gunicorn, uWSGI)
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure MongoDB IP whitelisting
- [ ] Set up database connection pooling
- [ ] Implement rate limiting
- [ ] Configure logging to files
- [ ] Set up monitoring and alerts
- [ ] Backup strategy for MongoDB chat history

### Example Gunicorn Deployment

```bash
gunicorn -w 4 -b 0.0.0.0:5002 app:app
```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5002
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5002", "app:app"]
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. MySQL Connection Failed
```
Error: Error connecting to database: 2003 (HY000): Can't connect to MySQL server
```
**Solution**: Check `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD` in `.env`

#### 2. MongoDB Connection Failed
```
Error: Failed to connect to MongoDB: ServerSelectionTimeoutError
```
**Solution**: 
- Verify MongoDB is running
- Check IP whitelisting for deployed environments
- Validate `MONGODB_HOST` and credentials

#### 3. OpenAI API Error
```
Error: The api_key client option must be set
```
**Solution**: Set `OPENAI_API_KEY` in `.env`

#### 4. Token Verification Failed
```
Error: Invalid or expired user session token
```
**Solution**: 
- Obtain fresh token from UnleashX
- Check `UNLEASHX_URL` is correct
- Verify token hasn't expired

#### 5. No Pages Found
```
No pages found in workspace 123.
```
**Solution**: 
- Ensure pages exist with `STATUS=1` in `page_schema`
- Verify `WORKSPACE_ID` matches authenticated user
- Check pages have content in `element_schema`

---

## 🧪 Testing

### Manual Testing

1. **Test database connections**
   ```
   GET http://localhost:5002/chat/pages/test-database-connections
   ```

2. **Test authentication**
   ```bash
   curl -X POST http://localhost:5002/chat/pages/search \
     -H "Content-Type: application/json" \
     -H "token: your-token" \
     -d '{"query": "test"}'
   ```

3. **Test knowledge base summary**
   ```bash
   curl -X GET http://localhost:5002/chat/pages/summary \
     -H "token: your-token"
   ```

---

## 📈 Performance Considerations

### Optimization Tips

1. **Database Indexing**
   - Index on `WORKSPACE_ID` in `page_schema`
   - Index on `PAGE_ID` in `element_schema`
   - Composite index on `(WORKSPACE_ID, STATUS)`

2. **Connection Pooling**
   - Implement connection pool for MySQL
   - Reuse MongoDB client connection

3. **Caching**
   - Cache page content for workspace (TTL: 5 minutes)
   - Cache OpenAI responses for identical queries

4. **Token Optimization**
   - Limit conversation history to last 10 messages
   - Set `max_tokens=350` for concise responses
   - Use cheaper model (gpt-4o-mini vs gpt-4)

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Add docstrings for all functions
- Include security validation comments
- Maintain consistent error handling

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
- OpenAI for GPT-4o-mini API
- Flask and Python community

---

## 📞 Support

For issues, questions, or support:
- Create an issue in the repository
- Contact the development team
- Check the troubleshooting section above

---

**Built with ❤️ for UnleashX**
