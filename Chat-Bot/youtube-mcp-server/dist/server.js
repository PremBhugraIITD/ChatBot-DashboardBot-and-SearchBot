"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.startMcpServer = startMcpServer;
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const video_1 = require("./services/video");
const transcript_1 = require("./services/transcript");
const playlist_1 = require("./services/playlist");
const channel_1 = require("./services/channel");
async function startMcpServer() {
    const server = new index_js_1.Server({
        name: 'zubeid-youtube-mcp-server',
        version: '1.0.0',
    }, {
        capabilities: {
            tools: {},
        },
    });
    const videoService = new video_1.VideoService();
    const transcriptService = new transcript_1.TranscriptService();
    const playlistService = new playlist_1.PlaylistService();
    const channelService = new channel_1.ChannelService();
    server.setRequestHandler(types_js_1.ListToolsRequestSchema, async () => {
        return {
            tools: [
                {
                    name: 'videos_getVideo',
                    description: 'Get detailed information about a YouTube video',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            videoId: {
                                type: 'string',
                                description: 'The YouTube video ID',
                            },
                            parts: {
                                type: 'array',
                                description: 'Parts of the video to retrieve',
                                items: {
                                    type: 'string',
                                },
                            },
                        },
                        required: ['videoId'],
                    },
                },
                {
                    name: 'videos_searchVideos',
                    description: 'Search for videos on YouTube',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            query: {
                                type: 'string',
                                description: 'Search query',
                            },
                            maxResults: {
                                type: 'number',
                                description: 'Maximum number of results to return',
                            },
                        },
                        required: ['query'],
                    },
                },
                {
                    name: 'transcripts_getTranscript',
                    description: 'Get the transcript of a YouTube video',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            videoId: {
                                type: 'string',
                                description: 'The YouTube video ID',
                            },
                            language: {
                                type: 'string',
                                description: 'Language code for the transcript',
                            },
                        },
                        required: ['videoId'],
                    },
                },
                {
                    name: 'channels_getChannel',
                    description: 'Get information about a YouTube channel',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            channelId: {
                                type: 'string',
                                description: 'The YouTube channel ID',
                            },
                        },
                        required: ['channelId'],
                    },
                },
                {
                    name: 'channels_listVideos',
                    description: 'Get videos from a specific channel',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            channelId: {
                                type: 'string',
                                description: 'The YouTube channel ID',
                            },
                            maxResults: {
                                type: 'number',
                                description: 'Maximum number of results to return',
                            },
                        },
                        required: ['channelId'],
                    },
                },
                {
                    name: 'channels_getPlaylists',
                    description: 'Get playlists from a specific channel',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            channelId: {
                                type: 'string',
                                description: 'The YouTube channel ID',
                            },
                            maxResults: {
                                type: 'number',
                                description: 'Maximum number of results to return',
                            },
                        },
                        required: ['channelId'],
                    },
                },
                {
                    name: 'playlists_getPlaylist',
                    description: 'Get information about a YouTube playlist',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            playlistId: {
                                type: 'string',
                                description: 'The YouTube playlist ID',
                            },
                        },
                        required: ['playlistId'],
                    },
                },
                {
                    name: 'playlists_getPlaylistItems',
                    description: 'Get videos in a YouTube playlist',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            playlistId: {
                                type: 'string',
                                description: 'The YouTube playlist ID',
                            },
                            maxResults: {
                                type: 'number',
                                description: 'Maximum number of results to return',
                            },
                        },
                        required: ['playlistId'],
                    },
                },
            ],
        };
    });
    server.setRequestHandler(types_js_1.CallToolRequestSchema, async (request) => {
        const { name, arguments: args } = request.params;
        try {
            switch (name) {
                case 'videos_getVideo': {
                    const result = await videoService.getVideo(args);
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify(result, null, 2)
                            }]
                    };
                }
                case 'videos_searchVideos': {
                    const result = await videoService.searchVideos(args);
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify(result, null, 2)
                            }]
                    };
                }
                case 'transcripts_getTranscript': {
                    const result = await transcriptService.getTranscript(args);
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify(result, null, 2)
                            }]
                    };
                }
                case 'channels_getChannel': {
                    const result = await channelService.getChannel(args);
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify(result, null, 2)
                            }]
                    };
                }
                case 'channels_listVideos': {
                    const result = await channelService.listVideos(args);
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify(result, null, 2)
                            }]
                    };
                }
                case 'channels_getPlaylists': {
                    const result = await channelService.getPlaylists(args);
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify(result, null, 2)
                            }]
                    };
                }
                case 'playlists_getPlaylist': {
                    const result = await playlistService.getPlaylist(args);
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify(result, null, 2)
                            }]
                    };
                }
                case 'playlists_getPlaylistItems': {
                    const result = await playlistService.getPlaylistItems(args);
                    return {
                        content: [{
                                type: 'text',
                                text: JSON.stringify(result, null, 2)
                            }]
                    };
                }
                default:
                    throw new Error(`Unknown tool: ${name}`);
            }
        }
        catch (error) {
            return {
                content: [{
                        type: 'text',
                        text: `Error: ${error instanceof Error ? error.message : String(error)}`
                    }],
                isError: true
            };
        }
    });
    // Create transport and connect
    const transport = new stdio_js_1.StdioServerTransport();
    await server.connect(transport);
    // Log the server info
    console.log(`YouTube MCP Server v1.0.0 started successfully`);
    console.log(`Server will validate YouTube API key when tools are called`);
    return server;
}
