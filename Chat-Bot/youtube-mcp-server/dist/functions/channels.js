"use strict";
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChannelManagement = void 0;
// @ts-ignore - We know the SDK exists
const sdk_1 = require("@modelcontextprotocol/sdk");
const googleapis_1 = require("googleapis");
// Utility functions
function safeGet(obj, path, defaultValue) {
    return path.split('.').reduce((acc, part) => acc && acc[part] !== undefined ? acc[part] : defaultValue, obj);
}
function safeParse(value, defaultValue = 0) {
    if (value === null || value === undefined)
        return defaultValue;
    const parsed = Number(value);
    return isNaN(parsed) ? defaultValue : parsed;
}
class ChannelManagement {
    constructor() {
        const apiKey = process.env.YOUTUBE_API_KEY;
        if (!apiKey) {
            throw new Error('YOUTUBE_API_KEY environment variable is not set.');
        }
        // @ts-ignore - The Google API works this way
        this.youtube = googleapis_1.google.youtube({
            version: 'v3',
            auth: apiKey
        });
    }
    // @ts-ignore - We know the SDK exists
    async getChannel({ channelId }) {
        try {
            const response = await this.youtube.channels.list({
                part: ['snippet', 'statistics', 'contentDetails'],
                id: [channelId]
            });
            return response.data.items?.[0] || null;
        }
        catch (error) {
            throw new Error(`Failed to get channel: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    // @ts-ignore - We know the SDK exists
    async getChannelVideos({ channelId, maxResults = 50 }) {
        try {
            const response = await this.youtube.search.list({
                part: ['snippet'],
                channelId,
                maxResults,
                order: 'date',
                type: ['video']
            });
            return response.data.items || [];
        }
        catch (error) {
            throw new Error(`Failed to get channel videos: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
}
exports.ChannelManagement = ChannelManagement;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get channel details',
        parameters: {
            type: 'object',
            properties: {
                channelId: { type: 'string' }
            },
            required: ['channelId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ChannelManagement.prototype, "getChannel", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get channel videos',
        parameters: {
            type: 'object',
            properties: {
                channelId: { type: 'string' },
                maxResults: { type: 'number' }
            },
            required: ['channelId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ChannelManagement.prototype, "getChannelVideos", null);
