#!/usr/bin/env node
"use strict";
/**
 * OpenAI OCR MCP Server
 * 
 * This server provides OCR (Optical Character Recognition) capabilities through OpenAI's GPT-4o-mini vision model.
 * It extracts text from images provided via URLs and returns only the text content without analysis.
 * Optimized for cost-effective processing with reduced token usage.
 * 
 * The server uses OpenAI's most affordable vision API to process images and extract text content efficiently.
 * 
 * Available Tools:
 * - extract_text_from_image: Extract text from images via URL (text-only, no analysis)
 *
 * Model Information:
 * - Uses OpenAI's GPT-4o-mini model for vision processing (cost-optimized)
 * - Optimized for fast, cost-effective text extraction without analysis
 * - Limited to 1000 tokens for efficient processing
 * - Supports images via HTTP/HTTPS URLs or data URLs
 *
 * Features:
 * - URL validation (format, protocol, security)
 * - Robust error handling and logging
 * - Direct text extraction and return (no analysis)
 * - Fast, cost-effective text-only extraction
 * - Support for both standard and project-specific OpenAI API keys
 * - Supports HTTP/HTTPS URLs and data URLs
 *
 * Usage Examples:
 * - extract_text_from_image with image_url: "https://example.com/document.jpg"
 * - extract_text_from_image with image_url: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
 * - Returns only extracted text content (no analysis or commentary)
 * - Supports JPG, PNG, GIF, and WebP image formats
 *
 * Environment Setup:
 * - Requires OpenAI API key in environment variables
 * - Supports multiple API key formats (OPENAI_API_KEY, openai_api_key)
 * - Optional .env file support for API key configuration
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
// Core imports
const readline_1 = require("readline");
const child_process_1 = require("child_process");
const dotenv = __importStar(require("dotenv"));
// ============================================================================
// Configuration
// ============================================================================
// Global API key variable
let OPENAI_API_KEY;
// Initialize conversation state
const conversationState = {
    llmResponses: [],
    lastOcrResult: '',
    lastImageUrl: ''
};
/**
 * Validate the API key format and check for common issues
 */
function validateApiKey(key) {
    if (!key) {
        return { isValid: false, issue: 'API key is empty' };
    }
    // Remove any whitespace or newlines that might have been added
    const cleanKey = key.trim();
    // Check for truncation issues
    if (cleanKey === 'sk-proj-' || cleanKey.startsWith('sk-proj-*')) {
        return { isValid: false, issue: 'API key appears to be truncated' };
    }
    // Check for proper format and length
    const isStandardKey = cleanKey.startsWith('sk-') && cleanKey.length > 20;
    const isProjectKey = cleanKey.startsWith('sk-proj-') && cleanKey.length > 30;
    if (!isStandardKey && !isProjectKey) {
        return {
            isValid: false,
            issue: `Invalid key format. Key must start with "sk-" or "sk-proj-" and be of sufficient length. Got: ${cleanKey.substring(0, 8)}...`
        };
    }
    return { isValid: true };
}
/**
 * Get OpenAI API key from environment variables, checking multiple formats
 */
function getOpenAIApiKey() {
    // Check for various possible environment variable names and formats
    const possibleEnvVars = [
        'OPENAI_API_KEY',
        'openai_api_key',
        'OpenAI_API_Key'
    ];
    for (const envVar of possibleEnvVars) {
        const key = process.env[envVar];
        if (key && key !== 'your-api-key-here') {
            // Clean the key and validate it
            const cleanKey = key.trim();
            const validation = validateApiKey(cleanKey);
            if (validation.isValid) {
                return cleanKey;
            }
        }
    }
    return undefined;
}
/**
 * Debug function to check environment variables
 */
function debugEnvironment() {
    return __awaiter(this, void 0, void 0, function* () {
        // Check all possible environment variable names
        const possibleEnvVars = [
            'OPENAI_API_KEY',
            'openai_api_key',
            'OpenAI_API_Key'
        ];
        
        // Check environment using the env command
        const envProcess = (0, child_process_1.spawn)('env');
        let envOutput = '';
        envProcess.stdout.on('data', (data) => {
            envOutput += data.toString();
        });
        yield new Promise((resolve) => {
            envProcess.on('close', () => {
                resolve(undefined);
            });
        });
    });
}
// Constants
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
const SERVER_NAME = "openai-ocr-service";
const SERVER_VERSION = "1.0.0";
const PROTOCOL_VERSION = "2024-11-05"; // Updated to match MCP Inspector expectation
// Store client info for future use
let clientInfo = null;
// ============================================================================
// Tool Definition
// ============================================================================
/**
 * The OCR tool specification
 */
const OCR_TOOL = {
    name: "extract_text_from_image",
    description: "Extract text from images using OpenAI's vision capabilities. Returns only the text content without analysis. Simply provide the URL to an image.",
    parameters: {
        type: "object",
        properties: {
            image_url: {
                type: "string",
                description: "URL to an image file (e.g., https://example.com/image.jpg or data:image/jpeg;base64,...)"
            }
        },
        required: ["image_url"]
    }
};
// ============================================================================
// Utility Functions
// ============================================================================
/**
 * Set up logging to stderr
 */
function log(message) {
    console.error(`[${new Date().toISOString()}] ${message}`);
}
// Load environment variables
let envResult;
try {
    envResult = dotenv.config();
    if (envResult.error) {
        // Will attempt to use environment variables from system
    }
} catch (error) {
    // Will attempt to use environment variables from system
}
// Get the API key from environment variables
OPENAI_API_KEY = getOpenAIApiKey();

// Only log if there's a critical error
if (!OPENAI_API_KEY) {
    log('ERROR: Valid OpenAI API key not found in environment variables or .env file');
    log('Please set the API key in your .env file:');
    log('OPENAI_API_KEY=your_api_key_here');
    log('or');
    log('openai_api_key=your_api_key_here');
    log('');
    log('Make sure:');
    log('1. The .env file exists in the project root directory');
    log('2. There are no spaces around the equals sign');
    log('3. The API key is not wrapped in quotes');
    log('4. The API key starts with either "sk-" or "sk-proj-"');
}

// Debug environment configuration
debugEnvironment().then(() => {
    // Silent initialization
});
/**
 * Send a JSON-RPC response to stdout
 */
function sendResponse(id, result) {
    const response = {
        jsonrpc: '2.0',
        id,
        result
    };
    process.stdout.write(JSON.stringify(response) + '\n');
}
/**
 * Send a JSON-RPC error to stdout
 */
function sendError(id, code, message) {
    const response = {
        jsonrpc: '2.0',
        id: id || 'error',
        error: {
            code,
            message
        }
    };
    process.stdout.write(JSON.stringify(response) + '\n');
}
/**
 * Validate image URL format and type
 */
function validateImageUrl(imageUrl) {
    // Check if it's a data URL (base64 encoded image)
    if (imageUrl.startsWith('data:image/')) {
        const validDataUrlPattern = /^data:image\/(jpeg|jpg|png|gif|webp);base64,/i;
        if (!validDataUrlPattern.test(imageUrl)) {
            throw new Error('Invalid data URL format. Must be data:image/[jpeg|jpg|png|gif|webp];base64,');
        }
        return true;
    }
    
    // Validate HTTP/HTTPS URL
    try {
        const url = new URL(imageUrl);
        
        // Only allow HTTP and HTTPS protocols
        if (!['http:', 'https:'].includes(url.protocol)) {
            throw new Error('Invalid URL protocol. Only HTTP and HTTPS are supported.');
        }
        
        // Basic security: avoid localhost and internal IPs
        if (url.hostname === 'localhost' || 
            url.hostname === '127.0.0.1' || 
            url.hostname.startsWith('192.168.') ||
            url.hostname.startsWith('10.') ||
            url.hostname.startsWith('172.16.') ||
            url.hostname.startsWith('172.31.')) {
            throw new Error('Internal/localhost URLs are not allowed for security reasons.');
        }
        
        // Check for common image file extensions
        const pathname = url.pathname.toLowerCase();
        const hasImageExtension = ALLOWED_EXTENSIONS.some(ext => pathname.endsWith(ext));
        
        if (!hasImageExtension) {
            // Don't throw error for missing extension, as some URLs might not have extensions
            // OpenAI will handle content validation
        }
        
        return true;
    } catch (error) {
        if (error.message.includes('Internal/localhost')) {
            throw error;
        }
        throw new Error(`Invalid URL format: ${error.message}`);
    }
}
/**
 * Log LLM response to the OCR result
 */
function logLlmResponse(response) {
    const timestamp = new Date().toISOString();
    
    // Store in conversation state
    conversationState.llmResponses.push({
        timestamp,
        response: JSON.stringify(response)
    });
}
// ============================================================================
// Core Tool Implementation
// ============================================================================
/**
 * Implementation of the extract_text_from_image tool
 */
function extractTextFromImage(args) {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            // First verify we have an API key
            if (!OPENAI_API_KEY) {
                OPENAI_API_KEY = getOpenAIApiKey();
                if (!OPENAI_API_KEY) {
                    throw new Error('OpenAI API key is not available. Please set the environment variable.');
                }
            }
            
            // Validate API key format
            const validation = validateApiKey(OPENAI_API_KEY);
            if (!validation.isValid) {
                throw new Error(`Invalid API key: ${validation.issue}`);
            }
            
            // Validate args
            if (!args) {
                throw new Error("Arguments are required but were undefined");
            }
            const { image_url } = args;
            
            // Validate image_url
            if (!image_url) {
                throw new Error("image_url is required but was missing");
            }
            
            // Validate image URL format and type
            validateImageUrl(image_url);
            
            // Call OpenAI API using curl
            return new Promise((resolve, reject) => {
                const requestBody = {
                    model: "gpt-4o-mini",
                    messages: [
                        {
                            role: 'user',
                            content: [
                                {
                                    type: 'text',
                                    text: 'Extract all text from this image. Only return the text content, do not provide any analysis or commentary.'
                                },
                                {
                                    type: 'image_url',
                                    image_url: {
                                        url: image_url,
                                        detail: 'high'
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens: 1000
                };
                
                const curl = (0, child_process_1.spawn)('curl', [
                    '-s',
                    '-X', 'POST',
                    'https://api.openai.com/v1/chat/completions',
                    '-H', `Authorization: Bearer ${OPENAI_API_KEY}`,
                    '-H', 'Content-Type: application/json',
                    '-v', // Add verbose output
                    '-d', JSON.stringify(requestBody)
                ]);
                let output = '';
                let errorOutput = '';
                curl.stdout.on('data', (data) => {
                    output += data.toString();
                });
                curl.stderr.on('data', (data) => {
                    errorOutput += data.toString();
                });
                curl.on('close', (code) => {
                    if (code !== 0) {
                        reject(new Error(`OpenAI API call failed with code ${code}: ${errorOutput}`));
                        return;
                    }
                    try {
                        const jsonResponse = JSON.parse(output);
                        if (jsonResponse.error) {
                            reject(new Error(`OpenAI API error: ${jsonResponse.error.message}`));
                            return;
                        }
                        
                        const content = jsonResponse.choices[0].message.content;
                        
                        // Extract the actual text content from OpenAI's response
                        // With text-only prompt, OpenAI should return cleaner responses
                        let extractedText = content;
                        
                        // Remove common OpenAI introductory phrases (even with text-only prompt)
                        const introPatterns = [
                            /^Here is the extracted text from the image:\s*/i,
                            /^The text in the image says:\s*/i,
                            /^The image contains the following text:\s*/i,
                            /^I can see the following text in the image:\s*/i,
                            /^The extracted text from the image is:\s*/i,
                            /^Text extracted from the image:\s*/i,
                            /^The text from the image:\s*/i,
                            /^Text content:\s*/i,
                            /^Here's the text:\s*/i,
                            /^The text reads:\s*/i
                        ];
                        
                        for (const pattern of introPatterns) {
                            extractedText = extractedText.replace(pattern, '');
                        }
                        
                        // Remove any trailing analysis sections if they accidentally appear
                        // Split on common analysis markers and take only the first part
                        const analysisSeparators = [
                            /\n\n(?:Analysis|Detailed Analysis|Commentary|Notes?):/i,
                            /\n\n(?:This|The image|The text)/i
                        ];
                        
                        for (const separator of analysisSeparators) {
                            const parts = extractedText.split(separator);
                            if (parts.length > 1) {
                                extractedText = parts[0];
                                break;
                            }
                        }
                        
                        // Clean up any leading/trailing whitespace
                        extractedText = extractedText.trim();
                        
                        // Store the OCR result in conversation state
                        conversationState.lastOcrResult = extractedText;
                        conversationState.lastImageUrl = image_url;
                        
                        // Return just the extracted text
                        resolve({
                            content: [
                                { type: "text", text: extractedText }
                            ]
                        });
                    }
                    catch (error) {
                        reject(new Error(`Failed to parse OpenAI response: ${error instanceof Error ? error.message : String(error)}`));
                    }
                });
            });
        }
        catch (error) {
            return {
                content: [
                    { type: "text", text: `Error: ${error instanceof Error ? error.message : String(error)}` }
                ],
                isError: true
            };
        }
    });
}
// ============================================================================
// MCP Method Handlers
// ============================================================================
/**
 * Handle the initialize method
 */
function handleInitialize(id, params) {
    // Store client info for future use
    if (params && params.clientInfo) {
        clientInfo = params.clientInfo;
    }
    
    // Create the response
    const response = {
        protocolVersion: PROTOCOL_VERSION,
        serverInfo: {
            name: SERVER_NAME,
            version: SERVER_VERSION
        },
        capabilities: {
            tools: {
                [OCR_TOOL.name]: {
                    description: OCR_TOOL.description,
                    parameters: OCR_TOOL.parameters
                }
            }
        }
    };
    
    // Include client info in response if provided
    if (clientInfo) {
        response.clientInfo = clientInfo;
    }
    
    sendResponse(id, response);
}
/**
 * Handle the ListOfferings method
 */
function handleListOfferings(id) {
    // Create the response
    const response = {
        protocolVersion: PROTOCOL_VERSION,
        serverInfo: {
            name: SERVER_NAME,
            version: SERVER_VERSION
        },
        offerings: {
            tools: [OCR_TOOL]
        }
    };
    
    // Include client info in response if available
    if (clientInfo) {
        response.clientInfo = clientInfo;
    }
    
    sendResponse(id, response);
}
/**
 * Handle the callTool method
 */
function handleCallTool(id, params) {
    return __awaiter(this, void 0, void 0, function* () {
        if (!params) {
            sendError(id, -32602, "Invalid params");
            return;
        }
        const { name, arguments: args } = params;
        if (name === OCR_TOOL.name) {
            try {
                const result = yield extractTextFromImage(args);
                sendResponse(id, result);
            }
            catch (error) {
                sendError(id, -32000, `Error executing tool: ${error instanceof Error ? error.message : String(error)}`);
            }
        }
        else {
            sendError(id, -32601, `Tool not found: ${name}`);
        }
    });
}
/**
 * Handle notification methods (methods that start with 'notifications/')
 * These don't require a response
 */
function handleNotification(method, params) {
    switch (method) {
        case 'notifications/llm_response':
            // Log the response
            logLlmResponse(params);
            break;
        case 'notifications/initialized':
            break;
        case 'notifications/exit':
            break;
        default:
            break;
    }
}
/**
 * Handle the tools/list method which is used by the MCP Inspector
 */
function handleToolsList(id) {
    // Create the response with the required schemas
    const response = {
        tools: [
            {
                name: OCR_TOOL.name,
                description: OCR_TOOL.description,
                inputSchema: {
                    type: "object",
                    properties: {
                        image_url: {
                            type: "string",
                            description: "URL to an image file (e.g., https://example.com/image.jpg or data:image/jpeg;base64,...)"
                        }
                    },
                    required: ["image_url"]
                }
            }
        ]
    };
    sendResponse(id, response);
}
/**
 * Handle the tools/call method which is used by the MCP Inspector to call tools
 */
function handleToolsCall(id, params) {
    return __awaiter(this, void 0, void 0, function* () {
        if (!params) {
            sendError(id, -32602, "Invalid params");
            return;
        }
        const { name, arguments: args } = params;
        if (name === OCR_TOOL.name) {
            try {
                const result = yield extractTextFromImage(args);
                sendResponse(id, result);
            }
            catch (error) {
                sendError(id, -32000, `Error executing tool: ${error instanceof Error ? error.message : String(error)}`);
            }
        }
        else {
            sendError(id, -32601, `Tool not found: ${name}`);
        }
    });
}
// ============================================================================
// Server Management
// ============================================================================
/**
 * Keep-alive mechanism to prevent the process from exiting
 */
function keepAlive() {
    const keepAliveInterval = setInterval(() => {
        // Silent heartbeat
    }, 30000); // Every 30 seconds
    
    // Clean up interval when process exits
    process.on('exit', () => {
        clearInterval(keepAliveInterval);
    });
}
/**
 * Set up process error handlers
 */
function setupErrorHandlers() {
    process.on('uncaughtException', (error) => {
        log(`UNCAUGHT EXCEPTION: ${error.message}`);
        log(error.stack || '');
    });
    process.on('unhandledRejection', (reason) => {
        log(`UNHANDLED PROMISE REJECTION: ${reason instanceof Error ? reason.message : String(reason)}`);
    });
}
// ============================================================================
// Main Function
// ============================================================================
/**
 * Main function to run the server
 */
function main() {
    // Set up error handlers
    setupErrorHandlers();
    // Start the keep-alive mechanism
    keepAlive();
    // Set up readline interface
    const rl = (0, readline_1.createInterface)({
        input: process.stdin,
        terminal: false
    });
    // Process each line from stdin
    rl.on('line', (line) => __awaiter(this, void 0, void 0, function* () {
        try {
            const truncatedLine = line.length > 500 ? `${line.substring(0, 500)}...` : line;
            log(`Received message: ${truncatedLine}`);
            const message = JSON.parse(line);
            const { method, id, params } = message;
            
            // Handle different MCP methods
            switch (method) {
                case 'initialize':
                    handleInitialize(id, params);
                    break;
                case 'initialized':
                    // No response needed for initialized notification
                    break;
                case 'ping':
                    sendResponse(id, null);
                    break;
                case 'tools/list':
                    handleToolsList(id);
                    break;
                case 'tools/call':
                    handleToolsCall(id, params);
                    break;
                case 'callTool':
                    handleCallTool(id, params);
                    break;
                case 'listOfferings':
                    handleListOfferings(id);
                    break;
                default:
                    if (method && method.startsWith('notifications/')) {
                        handleNotification(method, params);
                    }
                    else {
                        sendError(id, -32601, `Method not supported: ${method}`);
                    }
            }
        }
        catch (error) {
            sendError(null, -32700, `Error processing message: ${error instanceof Error ? error.message : String(error)}`);
        }
    }));
    
    // Keep the process alive by not closing on stdin end
    rl.on('close', () => {
        // Don't exit, just continue running
    });
}

// Start the server
main();