#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ErrorCode, ListToolsRequestSchema, McpError, } from '@modelcontextprotocol/sdk/types.js';
import { google } from 'googleapis';
// Environment variables required for user tokens
const ACCESS_TOKEN = process.env.GMAIL_ACCESS_TOKEN;
const REFRESH_TOKEN = process.env.GMAIL_REFRESH_TOKEN;
if (!ACCESS_TOKEN || !REFRESH_TOKEN) {
    throw new Error('Required Google user tokens not found in environment variables. Please provide GMAIL_ACCESS_TOKEN and GMAIL_REFRESH_TOKEN.');
}
class GoogleWorkspaceServer {
    server;
    auth;
    gmail;
    constructor() {
        this.server = new Server({
            name: 'gmail-server',
            version: '0.1.0',
        }, {
            capabilities: {
                tools: {},
            },
        });
        // Set up OAuth2 client with user tokens only
        this.auth = new google.auth.OAuth2();
        this.auth.setCredentials({
            access_token: ACCESS_TOKEN,
            refresh_token: REFRESH_TOKEN
        });
        // Initialize API clients
        this.gmail = google.gmail({ version: 'v1', auth: this.auth });
        this.setupToolHandlers();
        // Error handling
        this.server.onerror = (error) => console.error('[MCP Error]', error);
        process.on('SIGINT', async () => {
            await this.server.close();
            process.exit(0);
        });
    }
    setupToolHandlers() {
        this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
            tools: [
                {
                    name: 'list_emails',
                    description: 'List recent emails from Gmail inbox',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            maxResults: {
                                type: 'number',
                                description: 'Maximum number of emails to return (default: 10)',
                            },
                            query: {
                                type: 'string',
                                description: 'Search query to filter emails',
                            },
                        },
                    },
                },
                {
                    name: 'search_emails',
                    description: 'Search emails with advanced query',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            query: {
                                type: 'string',
                                description: 'Gmail search query (e.g., "from:example@gmail.com has:attachment")',
                            },
                            maxResults: {
                                type: 'number',
                                description: 'Maximum number of emails to return (default: 10)',
                            },
                        },
                        required: ['query']
                    },
                },
                {
                    name: 'send_email',
                    description: 'Send a new email',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            to: {
                                type: 'string',
                                description: 'Recipient email address',
                            },
                            subject: {
                                type: 'string',
                                description: 'Email subject',
                            },
                            body: {
                                type: 'string',
                                description: 'Email body (can include HTML)',
                            },
                            cc: {
                                type: 'string',
                                description: 'CC recipients (comma-separated)',
                            },
                            bcc: {
                                type: 'string',
                                description: 'BCC recipients (comma-separated)',
                            },
                        },
                        required: ['to', 'subject', 'body']
                    },
                },
                {
                    name: 'modify_email',
                    description: 'Modify email labels (archive, trash, mark read/unread)',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            id: {
                                type: 'string',
                                description: 'Email ID',
                            },
                            addLabels: {
                                type: 'array',
                                items: { type: 'string' },
                                description: 'Labels to add',
                            },
                            removeLabels: {
                                type: 'array',
                                items: { type: 'string' },
                                description: 'Labels to remove',
                            },
                        },
                        required: ['id']
                    },
                },
            ],
        }));
        this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
            switch (request.params.name) {
                case 'list_emails':
                    return await this.handleListEmails(request.params.arguments);
                case 'search_emails':
                    return await this.handleSearchEmails(request.params.arguments);
                case 'send_email':
                    return await this.handleSendEmail(request.params.arguments);
                case 'modify_email':
                    return await this.handleModifyEmail(request.params.arguments);
                default:
                    throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${request.params.name}`);
            }
        });
    }
    async handleListEmails(args) {
        try {
            const maxResults = args?.maxResults || 10;
            const query = args?.query || '';
            const response = await this.gmail.users.messages.list({
                userId: 'me',
                maxResults,
                q: query,
            });
            const messages = response.data.messages || [];
            const emailDetails = await Promise.all(messages.map(async (msg) => {
                const detail = await this.gmail.users.messages.get({
                    userId: 'me',
                    id: msg.id,
                });
                const headers = detail.data.payload?.headers;
                const subject = headers?.find((h) => h.name === 'Subject')?.value || '';
                const from = headers?.find((h) => h.name === 'From')?.value || '';
                const date = headers?.find((h) => h.name === 'Date')?.value || '';
                return {
                    id: msg.id,
                    subject,
                    from,
                    date,
                };
            }));
            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify(emailDetails, null, 2),
                    },
                ],
            };
        }
        catch (error) {
            return {
                content: [
                    {
                        type: 'text',
                        text: `Error fetching emails: ${error.message}`,
                    },
                ],
                isError: true,
            };
        }
    }
    async handleSearchEmails(args) {
        try {
            const maxResults = args?.maxResults || 10;
            const query = args?.query || '';
            const response = await this.gmail.users.messages.list({
                userId: 'me',
                maxResults,
                q: query,
            });
            const messages = response.data.messages || [];
            const emailDetails = await Promise.all(messages.map(async (msg) => {
                const detail = await this.gmail.users.messages.get({
                    userId: 'me',
                    id: msg.id,
                });
                const headers = detail.data.payload?.headers;
                const subject = headers?.find((h) => h.name === 'Subject')?.value || '';
                const from = headers?.find((h) => h.name === 'From')?.value || '';
                const date = headers?.find((h) => h.name === 'Date')?.value || '';
                return {
                    id: msg.id,
                    subject,
                    from,
                    date,
                };
            }));
            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify(emailDetails, null, 2),
                    },
                ],
            };
        }
        catch (error) {
            return {
                content: [
                    {
                        type: 'text',
                        text: `Error fetching emails: ${error.message}`,
                    },
                ],
                isError: true,
            };
        }
    }
    async handleSendEmail(args) {
        try {
            const { to, subject, body, cc, bcc } = args;
            
            // Get the authenticated user's email address for the From header
            const profile = await this.gmail.users.getProfile({ userId: 'me' });
            const fromEmail = profile.data.emailAddress;
            
            // Create proper MIME email content with all required headers
            const headers = [
                'MIME-Version: 1.0',
                'Content-Type: text/html; charset=utf-8',
                'Content-Transfer-Encoding: 7bit',
                `From: ${fromEmail}`,
                `To: ${to}`,
                cc ? `Cc: ${cc}` : '',
                bcc ? `Bcc: ${bcc}` : '',
                `Subject: ${subject}`,
                `Date: ${new Date().toUTCString()}`,
            ].filter(Boolean);
            
            // Proper MIME message construction with double CRLF separation
            const message = headers.join('\r\n') + '\r\n\r\n' + body;
            
            // Encode the email properly for Gmail API
            const encodedMessage = Buffer.from(message, 'utf8')
                .toString('base64')
                .replace(/\+/g, '-')
                .replace(/\//g, '_')
                .replace(/=+$/, '');
            
            // Send the email
            const response = await this.gmail.users.messages.send({
                userId: 'me',
                requestBody: {
                    raw: encodedMessage,
                },
            });
            
            return {
                content: [
                    {
                        type: 'text',
                        text: `Email sent successfully. Message ID: ${response.data.id}`,
                    },
                ],
            };
        }
        catch (error) {
            return {
                content: [
                    {
                        type: 'text',
                        text: `Error sending email: ${error.message}`,
                    },
                ],
                isError: true,
            };
        }
    }
    async handleModifyEmail(args) {
        try {
            const { id, addLabels = [], removeLabels = [] } = args;
            const response = await this.gmail.users.messages.modify({
                userId: 'me',
                id,
                requestBody: {
                    addLabelIds: addLabels,
                    removeLabelIds: removeLabels,
                },
            });
            return {
                content: [
                    {
                        type: 'text',
                        text: `Email modified successfully. Updated labels for message ID: ${response.data.id}`,
                    },
                ],
            };
        }
        catch (error) {
            return {
                content: [
                    {
                        type: 'text',
                        text: `Error modifying email: ${error.message}`,
                    },
                ],
                isError: true,
            };
        }
    }
    async run() {
        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        console.error('Gmail MCP server running on stdio');
    }
}
const server = new GoogleWorkspaceServer();
server.run().catch(console.error);
