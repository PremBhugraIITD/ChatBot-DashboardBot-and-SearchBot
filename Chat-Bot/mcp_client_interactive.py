import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser

from contextlib import AsyncExitStack

# Import centralized MCP servers configuration
from mcp_servers_list import MCP_SERVERS

load_dotenv()

class AgentTypeParser(BaseOutputParser):
    """Custom parser to extract agent type from LLM response."""
    
    def parse(self, text: str) -> str:
        # Extract agent type from the response
        text = text.strip().lower()
        if "developer" in text:
            return "developer"
        elif "writer" in text:
            return "writer"
        elif "sales" in text:
            return "sales"
        else:
            return "general"

def create_routing_chain(llm):
    """Create a chain to route queries to appropriate sub-agents."""
    
    routing_template = """
    You are a smart routing system. Based on the user's query, determine which specialized agent should handle it.

    Available agents:
    - developer: For programming, coding, technical questions, software development, debugging, algorithms, data structures, knowledge base implementation
    - writer: For content creation, writing, editing, documentation, creative writing, copywriting, research-based writing
    - sales: For sales-related queries, customer outreach, lead generation, business development, marketing, product information lookup
    - general: For everything else including knowledge base queries, general information lookup, status checks, and uncategorized requests

    User Query: {query}

    Consider these patterns:
    - Knowledge base queries, information lookup, "what is", "how to", research questions → general
    - Programming, technical implementation, code-related questions → developer  
    - Content creation, writing tasks, documentation → writer
    - Sales, business, customer-related tasks → sales

    Based on the query above, which agent should handle this? Respond with just the agent name (developer/writer/sales/general).
    
    Agent:"""
    
    routing_prompt = PromptTemplate(
        template=routing_template,
        input_variables=["query"]
    )
    
    return routing_prompt | llm | AgentTypeParser()

def create_sub_agents(all_tools, llm):
    """Create specialized sub-agents with their own personalities and expertise."""
    
    # Developer Bot
    developer_agent = initialize_agent(
        tools=all_tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={
            "system_message": """You are a Developer Bot, an expert software engineer and programmer. 
            You specialize in:
            - Writing clean, efficient code in various programming languages
            - Debugging and troubleshooting technical issues
            - Explaining algorithms and data structures
            - Best practices in software development
            - Code reviews and optimization
            - Knowledge base integration and vector search implementations
            
            You have access to a knowledge base system that can help answer technical questions and provide documentation.
            When users ask technical questions, consider using the knowledge base tools to find relevant information.
            Always provide practical, working solutions with clear explanations. When asked to send code via WhatsApp or other platforms, use the available tools to do so."""
        }
    )
    
    # Writer Bot
    writer_agent = initialize_agent(
        tools=all_tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={
            "system_message": """You are a Writer Bot, a professional content creator and wordsmith. 
            You specialize in:
            - Creating engaging and compelling content
            - Writing clear, concise documentation
            - Crafting creative stories and articles
            - Editing and proofreading text
            - Adapting tone and style for different audiences
            - Research and fact-checking using knowledge bases
            
            You have access to a knowledge base system that can help you research topics and verify information.
            Use the knowledge base tools to gather accurate information for your writing projects.
            Always deliver well-structured, grammatically correct content that meets the user's specific needs. Use available tools to share or collaborate on documents when requested."""
        }
    )
    
    # Sales Bot
    sales_agent = initialize_agent(
        tools=all_tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={
            "system_message": """You are a Sales Bot, a professional sales and business development expert. 
            You specialize in:
            - Creating persuasive sales pitches and proposals
            - Lead generation and customer outreach
            - Market analysis and competitive research
            - Customer relationship management
            - Converting prospects into customers
            - Product knowledge and documentation research
            
            You have access to a knowledge base system that can help you find product information, pricing details, and company policies.
            Use the knowledge base tools to provide accurate and up-to-date information to prospects and customers.
            Always focus on understanding customer needs and providing value-driven solutions. Use available communication tools to reach out to prospects when requested."""
        }
    )
    
    # General Agent (fallback)
    general_agent = initialize_agent(
        tools=all_tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={
            "system_message": """You are a General Assistant Bot, a helpful and knowledgeable AI assistant. 
            You can help with a wide variety of tasks and questions. You have access to various tools and services 
            to assist users with their requests, including a comprehensive knowledge base system.
            
            When users ask questions, consider using the knowledge base tools to find relevant information and provide accurate answers.
            You can query the knowledge base, check its status, search for specific information, and help manage knowledge sources.
            Always be helpful, accurate, and use the appropriate tools when needed."""
        }
    )
    
    return {
        "developer": developer_agent,
        "writer": writer_agent,
        "sales": sales_agent,
        "general": general_agent
    }

async def initialize_mcp_client():
    """Initialize all MCP servers and create agents."""
    stack = AsyncExitStack()
    await stack.__aenter__()
    
    try:
        # Initialize storage for per-server tools
        server_tools = {}
        all_tools = []

        # Spin up each MCP server and load its tools
        for cfg in MCP_SERVERS:
            server_id = cfg["id"]
            params = StdioServerParameters(
                command=cfg["command"],
                args=cfg["args"],
                env=cfg.get("env", {}),
            )
            try:
                read, write = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
            except Exception as e:
                print(f"⚠️  Failed to connect/init {cfg['args'][0]}: {e}")
                continue

            try:
                tools = await load_mcp_tools(session)
                print(f"📦 Loaded tools from {cfg['args'][0]}:")
                for t in tools:
                    print(f"  • {t.name}")
                # Store per-server tool list
                server_tools[server_id] = tools
                all_tools.extend(tools)
            except Exception as e:
                print(f"⚠️  Failed to load tools from {cfg['args'][0]}: {e}")

        if not all_tools:
            raise RuntimeError("❌ No tools loaded from any MCP server.")

        # Initialize LLM
        llm = ChatOpenAI(model="gpt-4")
        
        # Create routing chain
        routing_chain = create_routing_chain(llm)
        
        # Create sub-agents
        sub_agents = create_sub_agents(all_tools, llm)
        
        # Keep the original agent for backward compatibility
        direct_agent = initialize_agent(
            tools=all_tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
            handle_parsing_errors=True,
        )

        print("🤖 Initialized sub-agents: Developer, Writer, Sales, General")
        
        return {
            "routing_chain": routing_chain,
            "sub_agents": sub_agents,
            "direct_agent": direct_agent,
            "server_tools": server_tools,
            "stack": stack
        }
        
    except Exception as e:
        await stack.__aexit__(None, None, None)
        raise e

async def query_with_routing(prompt, routing_chain, sub_agents):
    """Process query with automatic routing to appropriate sub-agent."""
    try:
        # Route the query to appropriate sub-agent
        agent_type = await routing_chain.ainvoke({"query": prompt})
        print(f"🎯 Routing query to: {agent_type} agent")
        
        # Get the appropriate agent
        selected_agent = sub_agents.get(agent_type, sub_agents["general"])
        
        # Process the query with the selected agent
        result = await selected_agent.ainvoke(prompt)
        
        return {
            "response": result,
            "agent_used": agent_type,
            "message": f"Response generated by {agent_type} agent"
        }
    except Exception as e:
        return {"error": str(e)}

async def query_specific_agent(prompt, agent_type, sub_agents):
    """Query a specific sub-agent directly."""
    if agent_type not in sub_agents:
        return {"error": f"Agent '{agent_type}' not found. Available agents: {list(sub_agents.keys())}"}
    
    try:
        selected_agent = sub_agents[agent_type]
        result = await selected_agent.ainvoke(prompt)
        
        return {
            "response": result,
            "agent_used": agent_type,
            "message": f"Response generated by {agent_type} agent"
        }
    except Exception as e:
        return {"error": str(e)}

async def query_direct_agent(prompt, direct_agent):
    """Query the direct agent without routing."""
    try:
        result = await direct_agent.ainvoke(prompt)
        return {"response": result}
    except Exception as e:
        return {"error": str(e)}

def get_available_agents():
    """Returns list of available sub-agents."""
    return {
        "agents": [
            {
                "name": "developer",
                "description": "Expert in programming, coding, and technical solutions"
            },
            {
                "name": "writer", 
                "description": "Specialist in content creation, writing, and documentation"
            },
            {
                "name": "sales",
                "description": "Expert in sales, business development, and customer outreach"
            },
            {
                "name": "general",
                "description": "General-purpose assistant for various tasks"
            }
        ]
    }

def get_tools_info(server_id, server_tools):
    """Returns the list of tools for the specified MCP server ID."""
    tools = server_tools.get(server_id)
    if not tools:
        return {"error": f"No tools found for server '{server_id}'"}

    tool_data = []
    for tool in tools:
        # Normalize args_schema:
        raw_schema = getattr(tool, "args_schema", None)
        if isinstance(raw_schema, dict):
            args_schema = raw_schema
        elif raw_schema and hasattr(raw_schema, "schema"):
            args_schema = raw_schema.schema()
        else:
            args_schema = {}

        tool_data.append({
            "name": tool.name,
            "description": getattr(tool, "description", ""),
            "args_schema": args_schema,
        })

    return {"tools": tool_data}

def print_menu():
    """Display the main menu options."""
    print("\n" + "="*60)
    print("🤖 MCP CLIENT - MULTI-AGENT SYSTEM")
    print("="*60)
    print("Choose an option:")
    print("1. 🎯 Smart Query (Auto-route to appropriate agent)")
    print("2. 👨‍💻 Developer Agent (Direct)")
    print("3. ✍️  Writer Agent (Direct)")
    print("4. 💼 Sales Agent (Direct)")
    print("5. 🔧 General Agent (Direct)")
    print("6. 🚀 Direct Agent (No routing)")
    print("7. 📋 List Available Agents")
    print("8. 🛠️  List Tools by Server")
    print("9. ❌ Exit")
    print("="*60)

def print_response(result):
    """Pretty print the response."""
    print("\n" + "="*60)
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        if "agent_used" in result:
            print(f"🤖 Agent Used: {result['agent_used'].upper()}")
            print(f"📝 Message: {result['message']}")
        print("\n📤 Response:")
        print("-" * 40)
        if isinstance(result["response"], dict) and "output" in result["response"]:
            print(result["response"]["output"])
        else:
            print(result["response"])
    print("="*60)

async def main():
    """Main interactive loop."""
    print("🚀 Initializing MCP Client...")
    
    try:
        # Initialize the MCP client
        client_data = await initialize_mcp_client()
        routing_chain = client_data["routing_chain"]
        sub_agents = client_data["sub_agents"]
        direct_agent = client_data["direct_agent"]
        server_tools = client_data["server_tools"]
        stack = client_data["stack"]
        
        print("✅ Initialization complete!")
        
        while True:
            try:
                print_menu()
                choice = input("Enter your choice (1-9): ").strip()
                
                if choice == "1":
                    prompt = input("\n💬 Enter your query: ").strip()
                    if prompt:
                        print("🔄 Processing with smart routing...")
                        result = await query_with_routing(prompt, routing_chain, sub_agents)
                        print_response(result)
                
                elif choice == "2":
                    prompt = input("\n💬 Enter your developer query: ").strip()
                    if prompt:
                        print("🔄 Processing with Developer Agent...")
                        result = await query_specific_agent(prompt, "developer", sub_agents)
                        print_response(result)
                
                elif choice == "3":
                    prompt = input("\n💬 Enter your writing query: ").strip()
                    if prompt:
                        print("🔄 Processing with Writer Agent...")
                        result = await query_specific_agent(prompt, "writer", sub_agents)
                        print_response(result)
                
                elif choice == "4":
                    prompt = input("\n💬 Enter your sales query: ").strip()
                    if prompt:
                        print("🔄 Processing with Sales Agent...")
                        result = await query_specific_agent(prompt, "sales", sub_agents)
                        print_response(result)
                
                elif choice == "5":
                    prompt = input("\n💬 Enter your general query: ").strip()
                    if prompt:
                        print("🔄 Processing with General Agent...")
                        result = await query_specific_agent(prompt, "general", sub_agents)
                        print_response(result)
                
                elif choice == "6":
                    prompt = input("\n💬 Enter your direct query: ").strip()
                    if prompt:
                        print("🔄 Processing with Direct Agent...")
                        result = await query_direct_agent(prompt, direct_agent)
                        print_response(result)
                
                elif choice == "7":
                    agents = get_available_agents()
                    print("\n📋 Available Agents:")
                    print("-" * 40)
                    for agent in agents["agents"]:
                        print(f"• {agent['name'].upper()}: {agent['description']}")
                
                elif choice == "8":
                    print("\n🛠️  Available MCP Servers:")
                    print("-" * 40)
                    for server_id in server_tools.keys():
                        print(f"• {server_id}")
                    
                    server_choice = input("\nEnter server ID to see tools: ").strip()
                    if server_choice in server_tools:
                        tools_info = get_tools_info(server_choice, server_tools)
                        if "error" in tools_info:
                            print(f"❌ {tools_info['error']}")
                        else:
                            print(f"\n🔧 Tools for '{server_choice}' server:")
                            print("-" * 40)
                            for tool in tools_info["tools"]:
                                print(f"• {tool['name']}: {tool['description']}")
                    else:
                        print("❌ Invalid server ID")
                
                elif choice == "9":
                    print("\n👋 Goodbye!")
                    break
                
                else:
                    print("❌ Invalid choice. Please select 1-9.")
                
                # Wait for user to continue
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ An error occurred: {e}")
                input("Press Enter to continue...")
    
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
    
    finally:
        # Cleanup
        if 'stack' in locals():
            await stack.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(main())
