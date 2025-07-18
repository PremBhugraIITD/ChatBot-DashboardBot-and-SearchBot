#!/usr/bin/env node
"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const mcp_1 = require("@mondaydotcomorg/agent-toolkit/mcp");
const args_service_js_1 = require("./utils/args/args.service.js");
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
/**
 * Initializes and starts the MCP server with the Monday Agent Toolkit
 * Uses stdio for transport
 */
async function runServer() {
    const args = process.argv.slice(2);
    const parsedArgs = (0, args_service_js_1.parseArgs)(args);
    const validatedArgs = (0, args_service_js_1.validateArgs)(parsedArgs);
    const toolkit = new mcp_1.MondayAgentToolkit({
        mondayApiToken: validatedArgs.token,
        mondayApiVersion: validatedArgs.version,
        mondayApiRequestConfig: {},
        toolsConfiguration: {
            readOnlyMode: validatedArgs.readOnlyMode,
            enableDynamicApiTools: validatedArgs.enableDynamicApiTools,
            mode: validatedArgs.mode,
            enableToolManager: false,
        },
    });
    const transport = new stdio_js_1.StdioServerTransport();
    await toolkit.connect(transport);
}
runServer().catch((error) => {
    console.error('Fatal error in main():', error);
    process.exit(1);
});
