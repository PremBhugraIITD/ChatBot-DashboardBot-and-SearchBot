import os
import sys
import json
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack

import openai
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent
from mcp.client.stdio import stdio_client

load_dotenv()  # loads OPENAI_API_KEY (and any other .env vars) into env
openai.api_key = os.getenv("OPENAI_API_KEY")


# ────────────────────────────────────────────────────────────────────────────────
# 1) Define MCP_SERVERS here.  Whenever you want to add a new server, just append
#    another dict (with "command", "args", and "env") to this list.
#
#  Each entry must match the signature for StdioServerParameters:
#     - "command":    e.g. "python" or "node"
#     - "args":       a list of strings, e.g. ["my_mcp_server.py"] or ["build/index.js"]
#     - "env":        a dict of environment vars to pass to the subprocess.
# ────────────────────────────────────────────────────────────────────────────────
MCP_SERVERS = [
    {
        "command": "node",
        "args": ["google-workspace-mcp-server/build/index.js"],
        "env": {
            "GOOGLE_CLIENT_ID":     os.getenv("GOOGLE_CLIENT_ID"),
            "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
            "GOOGLE_REFRESH_TOKEN": os.getenv("GOOGLE_REFRESH_TOKEN"),
        },
    },
    {
        "command": "python",
        "args": ["math_server.py"],
        "env": {},
    },
    {
        "command": "python",
        "args": ["whatsapp-mcp/whatsapp-mcp-server/main.py"],
        "env": {},
    },
    {
        "command": "python",
        "args": ["mcp-google-sheets/server.py"],
        "env": {
            "CREDENTIALS_PATH": os.getenv("CREDENTIALS_PATH"),
            "TOKEN_PATH":       os.getenv("TOKEN_PATH"),
        },
    },
    # ── Add more entries here as needed ──────────────────────────────────────
]


class MCPClient:
    def __init__(self):
        # We will spin up one ClientSession per server in MCP_SERVERS
        self.sessions: List[ClientSession] = []
        # This maps each tool_name -> the ClientSession that implements it
        self.tool_to_session: Dict[str, ClientSession] = {}
        # AsyncExitStack to manage all subprocesses & sessions
        self.exit_stack = AsyncExitStack()

    async def connect_to_servers(self):
        """
        Launches one stdio-based MCP subprocess per entry in MCP_SERVERS,
        initializes each ClientSession, and builds a tool→session mapping.
        """
        for idx, server_cfg in enumerate(MCP_SERVERS):
            command = server_cfg["command"]
            args = server_cfg["args"]
            env_vars = server_cfg.get("env", {}) or {}

            # Build the parameter object for this particular server
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env_vars
            )

            # 1) Start the subprocess via stdio_client(...) and enter it into exit_stack
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio_reader_writer, write_coroutine = stdio_transport

            # 2) Create a ClientSession on top of that stdio stream
            session = await self.exit_stack.enter_async_context(
                ClientSession(stdio_reader_writer, write_coroutine)
            )
            await session.initialize()

            # 3) Query this session for its tools, so we can print/log them
            list_resp = await session.list_tools()
            tool_names = [tool.name for tool in list_resp.tools]
            print(f"\n[Connected to server #{idx + 1} → '{' '.join([command] + args)}' with tools: {tool_names} ]")

            # 4) Remember this session in our list
            self.sessions.append(session)

            # 5) For each tool, record which session “owns” it
            for tool in list_resp.tools:
                if tool.name in self.tool_to_session:
                    # If two servers implement the same tool name, this is ambiguous.
                    raise RuntimeError(f"Duplicate tool name '{tool.name}' detected! "
                                       "Each tool name must be unique across all servers.")
                self.tool_to_session[tool.name] = session

        # At this point, all subprocesses are running, all sessions are initialized,
        # and self.tool_to_session knows exactly which session to call for each tool.

    async def process_query(self, query: str) -> str:
        """
        1) Ask ALL MCP sessions what tools they expose (we already have that cached, but re-fetching is also fine).
        2) Build one combined list of OpenAI “functions” from _all_ tools across all servers.
        3) Send the user’s query + combined “functions” to GPT-4.
        4) If GPT-4 does NOT call a function, just return its plain-text response.
        5) If GPT-4 DOES call a function, figure out which session to invoke, run it,
           then feed that result back to GPT-4 for a second pass.
        """
        # -----------------------------------------------------------------------
        # STEP A: Build a combined “functions” schema from every session’s tools
        # -----------------------------------------------------------------------
        combined_functions = []
        for session in self.sessions:
            list_resp = await session.list_tools()
            for tool in list_resp.tools:
                combined_functions.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {}
                })

        # Prepare the initial chat history with only the user’s query
        messages = [ { "role": "user", "content": query } ]

        # -----------------------------------------------------------------------
        # STEP B: Send to GPT-4 with functions=combined_functions
        # -----------------------------------------------------------------------
        first_resp = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=messages,
            functions=combined_functions,
            temperature=0.0,
            max_tokens=1000
        )
        choice = first_resp.choices[0].message

        # If GPT-4 did NOT pick a function, just return its text reply
        if choice.get("role") == "assistant" and "function_call" not in choice:
            return choice["content"]

        # -----------------------------------------------------------------------
        # STEP C: GPT-4 DID pick a function. Parse out name + arguments
        # -----------------------------------------------------------------------
        if choice.get("role") == "assistant" and choice.get("function_call"):
            func_call = choice["function_call"]
            tool_name = func_call["name"]
            # ───────────────────────────────────────────────────────────────────
            # Print (or log) the name of the tool that’s about to be invoked:
            print(f"Tools used for this query: {tool_name}")
            # ───────────────────────────────────────────────────────────────────
            try:
                tool_args: Dict[str, Any] = json.loads(func_call["arguments"])
            except json.JSONDecodeError:
                return f"Error parsing arguments for tool {tool_name}: {func_call['arguments']}"

            # -------------------------------------------------------------------
            # STEP D: Find out WHICH session implements this tool_name
            # -------------------------------------------------------------------
            if tool_name not in self.tool_to_session:
                return f"Error: no MCP session found for tool '{tool_name}'"
            target_session = self.tool_to_session[tool_name]

            # -------------------------------------------------------------------
            # STEP E: Invoke that MCP tool on its session
            # -------------------------------------------------------------------
            tool_result = await target_session.call_tool(tool_name, tool_args)
            # tool_result.content is typically a TextContent (or similar),
            # so we must convert it to a plain str before handing it back to GPT-4:

            if isinstance(tool_result.content, TextContent):
                plain_text_output = str(tool_result.content)  # calls TextContent.__str__()
            else:
                # If it’s already a string, just use it directly.
                plain_text_output = tool_result.content

            # -------------------------------------------------------------------
            # STEP F: Insert the function_call + its output into the chat history
            # -------------------------------------------------------------------
            messages.append({
                "role": "assistant",
                "name": tool_name,
                "content": None,
                "function_call": {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args)
                }
            })
            messages.append({
                "role": "function",
                "name": tool_name,
                "content": str(plain_text_output)
            })

            # -------------------------------------------------------------------
            # STEP G: Ask GPT-4 to finish its reply (no more functions needed)
            # -------------------------------------------------------------------
            second_resp = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=messages,
                temperature=0.0,
                max_tokens=1000
            )
            return second_resp.choices[0].message["content"]

        # Fallback if something unexpected happened
        return "No valid response from GPT-4."

    async def chat_loop(self):
        """Read from stdin, call process_query, print to stdout (REPL)."""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.\n")

        while True:
            try:
                query = input("Query: ").strip()
                if query.lower() == "q":
                    break

                response_text = await self.process_query(query)
                print("\n" + response_text + "\n")

            except Exception as e:
                # If any error bubbles up, show it and keep the loop alive
                print(f"\nError during chat_loop: {str(e)}\n")

    async def cleanup(self):
        """Shut down all MCP sessions and kill subprocesses."""
        await self.exit_stack.aclose()



# ────────────────────────────────────────────────────────────────────────────────
# Entrypoint: no CLI args needed.  It will just read MCP_SERVERS from above.
# ────────────────────────────────────────────────────────────────────────────────
async def main():
    client = MCPClient()
    try:
        await client.connect_to_servers()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
