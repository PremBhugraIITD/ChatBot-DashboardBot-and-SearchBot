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
exports.VideoManagement = void 0;
const googleapis_1 = require("googleapis");
// @ts-ignore - We know the SDK exists
const sdk_1 = require("@modelcontextprotocol/sdk");
function safelyExecute(fn) {
    return fn().catch(error => {
        throw new Error(`Operation failed: ${error instanceof Error ? error.message : String(error)}`);
    });
}
class VideoManagement {
    constructor() {
        const apiKey = process.env.YOUTUBE_API_KEY;
        if (!apiKey) {
            throw new Error('YOUTUBE_API_KEY environment variable is not set. Please set it before running the application.');
        }
        // @ts-ignore - The Google API works this way
        this.youtube = googleapis_1.google.youtube({
            version: 'v3',
            auth: apiKey
        });
    }
    // @ts-ignore - We know the SDK exists
    async getVideo({ videoId, parts = ['snippet', 'contentDetails', 'statistics'] }) {
        return safelyExecute(async () => {
            const response = await this.youtube.videos.list({
                part: parts,
                id: [videoId]
            });
            return response.data.items?.[0] || null;
        });
    }
    // @ts-ignore - We know the SDK exists
    async searchVideos({ query, maxResults = 10 }) {
        return safelyExecute(async () => {
            const response = await this.youtube.search.list({
                part: ['snippet'],
                q: query,
                maxResults,
                type: ['video']
            });
            return response.data.items || [];
        });
    }
    // @ts-ignore - We know the SDK exists
    async getVideoStats({ videoId }) {
        return safelyExecute(async () => {
            const response = await this.youtube.videos.list({
                part: ['statistics'],
                id: [videoId]
            });
            return response.data.items?.[0]?.statistics || null;
        });
    }
}
exports.VideoManagement = VideoManagement;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get detailed information about a YouTube video',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                parts: {
                    type: 'array',
                    items: { type: 'string' }
                }
            },
            required: ['videoId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], VideoManagement.prototype, "getVideo", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Search for videos on YouTube',
        parameters: {
            type: 'object',
            properties: {
                query: { type: 'string' },
                maxResults: { type: 'number' }
            },
            required: ['query']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], VideoManagement.prototype, "searchVideos", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get video statistics like views, likes, and comments',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' }
            },
            required: ['videoId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], VideoManagement.prototype, "getVideoStats", null);
