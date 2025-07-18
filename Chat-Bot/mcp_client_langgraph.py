import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
load_dotenv()

async def main():
    client = MultiServerMCPClient({
        "math": {
            "command": "python",
            "args": ["math_server.py"],
            "transport": "stdio",
        },
        "Google Spreadsheet":{
            "command": "python",
            "args": ["mcp-google-sheets/server.py"],
            "transport": "stdio",
            "env": {
                "CREDENTIALS_PATH": os.getenv("CREDENTIALS_PATH"),
                "TOKEN_PATH":       os.getenv("TOKEN_PATH"),
            }
        },
        "whatsapp": {
            "command": "python",
            "args": ["whatsapp-mcp/whatsapp-mcp-server/main.py"],
            "transport": "stdio",
        },
        "google_workspace": {
            "command": "node",
            "args": ["google-workspace-mcp-server/build/index.js"],
            "transport": "stdio",
            "env": {
                "GOOGLE_CLIENT_ID":     os.getenv("GOOGLE_CLIENT_ID"),
                "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
                "GOOGLE_REFRESH_TOKEN": os.getenv("GOOGLE_REFRESH_TOKEN"),
            }
        }
    })

    print("Loading MCP tools...")
    tools = await client.get_tools()

    print("\n" + "="*60)
    print("MCP TOOLS LOADED")
    print("="*60)
    print(f"Total tools available: {len(tools)}")
    print()
    
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}")
    
    print("="*60)
    print()

    llm = ChatOpenAI(
        model="gpt-4",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        temperature=0.0,
    )

    agent = create_react_agent(llm, tools)
    
    print("MCP Agent ready! Type 'quit' to exit.")
    
    while True:
        try:
            user_query = input("\nEnter your query: ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_query:
                print("Please enter a valid query.")
                continue
            
            print("Processing...")
            
            response = await agent.ainvoke({"messages": user_query})
            
            result = extract_ai_message_and_tools(response)
            
            print("\n" + "="*50)
            print("AI Response:", result['ai_message_content'])
            print("Tools Used:", result['tools_called'])
            print("="*50)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

def extract_ai_message_and_tools(response):
    messages = response['messages']
    
    ai_message_content = None
    tools_called = []
    
    for message in messages:
        if hasattr(message, '__class__') and message.__class__.__name__ == 'AIMessage':
            if hasattr(message, 'content') and message.content:
                ai_message_content = message.content
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tools_called.append({
                        'name': tool_call['name'],
                        'args': tool_call['args']
                    })
    
    return {
        'ai_message_content': ai_message_content,
        'tools_called': tools_called
    }

if __name__ == "__main__":
    asyncio.run(main())