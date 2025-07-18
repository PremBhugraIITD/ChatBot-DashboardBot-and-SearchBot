#!/usr/bin/env python3
"""
Zoho Books MCP Server Wrapper for STDIO mode.

This wrapper script runs the Zoho Books MCP server in STDIO mode
for integration with the Chat-Bot system.
"""

import sys
import os

# Add the zoho-books-mcp directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Override sys.argv to force STDIO mode
if len(sys.argv) == 1:
    sys.argv.append('--stdio')

# Import and run the main server
from server import main

if __name__ == "__main__":
    main()
