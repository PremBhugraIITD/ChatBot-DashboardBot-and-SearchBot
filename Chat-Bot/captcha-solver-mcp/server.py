#!/usr/bin/env python3
"""
CAPTCHA Solver MCP Server

This MCP server provides tools for solving various types of CAPTCHAs using Google Gemini AI.
Extracted from automated booking system and converted to MCP format.
"""

import asyncio
import base64
import io
import json
import logging
import os
from typing import Any, Dict, Optional, Union

import google.generativeai as genai
import PIL.Image
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("captcha-solver-mcp")

# Initialize MCP server
server = Server("captcha-solver-mcp")

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCqdJIUwt_CuvYmW-qrJEjBOieQnouU3oQ")
genai.configure(api_key=GEMINI_API_KEY)

class CaptchaSolver:
    """Core CAPTCHA solving functionality using Gemini AI"""
    
    def __init__(self):
        self.math_model = genai.GenerativeModel('gemini-1.5-flash')
        self.text_model = genai.GenerativeModel('gemini-2.0-flash')
    
    def solve_math_captcha(self, image: PIL.Image.Image) -> Optional[str]:
        """
        Solve math-based CAPTCHA using Gemini 1.5 Flash
        Returns numeric result or None if failed
        """
        try:
            response = self.math_model.generate_content(
                [
                    "This is a math captcha. Calculate and return ONLY the numeric result.",
                    image
                ],
                generation_config={"temperature": 0}
            )
            captcha_text = response.text.strip()
            
            if captcha_text.isdigit():
                return captcha_text
            return None
                
        except Exception as e:
            logger.error(f"Error solving math captcha: {e}")
            return None
    
    def solve_text_captcha(self, image: PIL.Image.Image) -> Optional[str]:
        """
        Solve alphanumeric text CAPTCHA using Gemini 2.0 Flash
        Returns alphanumeric text or None if failed
        """
        try:
            response = self.text_model.generate_content(
                [
                    "OCR task: Return ONLY the alphanumeric captcha text. No explanation.",
                    image
                ],
                generation_config={
                    "temperature": 0,
                    "max_output_tokens": 10,
                }
            )
            
            captcha_text = response.text.strip()
            if captcha_text.isalnum():
                return captcha_text
                
            return None
                
        except Exception as e:
            logger.error(f"Error solving text captcha: {e}")
            return None
    
    def solve_auto_captcha(self, image: PIL.Image.Image, captcha_type: str = "auto") -> Optional[str]:
        """
        Auto-detect CAPTCHA type and solve accordingly
        """
        if captcha_type == "math":
            return self.solve_math_captcha(image)
        elif captcha_type == "text":
            return self.solve_text_captcha(image)
        else:
            # Try text first (more common), then math
            result = self.solve_text_captcha(image)
            if result is None:
                result = self.solve_math_captcha(image)
            return result

# Initialize CAPTCHA solver
captcha_solver = CaptchaSolver()

def base64_to_image(base64_data: str) -> PIL.Image.Image:
    """Convert base64 string to PIL Image"""
    try:
        # Handle Playwright screenshot response format
        if "Base64 data: " in base64_data:
            # Extract base64 data from Playwright response
            base64_data = base64_data.split("Base64 data: ")[-1].strip()
        
        # Remove data URL prefix if present
        if base64_data.startswith('data:image'):
            base64_data = base64_data.split(',')[1]
        
        image_data = base64.b64decode(base64_data)
        image = PIL.Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        logger.error(f"Error converting base64 to image: {e}")
        raise

def load_image_from_file() -> PIL.Image.Image:
    """Load image from base64 file written by screenshot tool"""
    try:
        # Look for image_base64.txt in Chat-Bot directory (two levels up from this file)
        base64_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'image_base64.txt')
        
        if not os.path.exists(base64_file_path):
            raise FileNotFoundError(f"Base64 file not found: {base64_file_path}")
        
        with open(base64_file_path, 'r') as f:
            base64_data = f.read().strip()
        
        if not base64_data:
            raise ValueError("Base64 file is empty")
        
        # Convert base64 to image
        image_data = base64.b64decode(base64_data)
        image = PIL.Image.open(io.BytesIO(image_data))
        logger.info(f"Successfully loaded image from {base64_file_path}: {image.size}")
        return image
        
    except Exception as e:
        logger.error(f"Error loading image from file: {e}")
        raise

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available CAPTCHA solving tools"""
    return [
        Tool(
            name="solve_math_captcha",
            description="Solve math-based CAPTCHA (e.g., '5 + 3 = ?'). Reads image from image_base64.txt file. Returns only the numeric result.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="solve_text_captcha",
            description="Solve alphanumeric text CAPTCHA using OCR. Reads image from image_base64.txt file. Returns only the text characters.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="solve_captcha_auto",
            description="Auto-detect CAPTCHA type and solve accordingly. Reads image from image_base64.txt file. Tries text recognition first, then math if needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "captcha_type": {
                        "type": "string",
                        "description": "Hint for CAPTCHA type: 'math', 'text', or 'auto' (default)",
                        "enum": ["math", "text", "auto"]
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for CAPTCHA solving"""
    
    try:
        if name == "solve_math_captcha":
            image = load_image_from_file()
            result = captcha_solver.solve_math_captcha(image)
            
            if result:
                return [TextContent(type="text", text=f"Math CAPTCHA solved: {result}")]
            else:
                return [TextContent(type="text", text="Failed to solve math CAPTCHA")]
        
        elif name == "solve_text_captcha":
            image = load_image_from_file()
            result = captcha_solver.solve_text_captcha(image)
            
            if result:
                return [TextContent(type="text", text=f"Text CAPTCHA solved: {result}")]
            else:
                return [TextContent(type="text", text="Failed to solve text CAPTCHA")]
        
        elif name == "solve_captcha_auto":
            captcha_type = arguments.get("captcha_type", "auto")
            image = load_image_from_file()
            result = captcha_solver.solve_auto_captcha(image, captcha_type)
            
            if result:
                return [TextContent(type="text", text=f"CAPTCHA solved: {result}")]
            else:
                return [TextContent(type="text", text="Failed to solve CAPTCHA")]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error in tool call {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Main server entry point"""
    logger.info("Starting CAPTCHA Solver MCP Server")
    
    # Verify Gemini API key
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
        logger.warning("GEMINI_API_KEY not set or using placeholder. Please set your actual API key.")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="captcha-solver-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main()) 