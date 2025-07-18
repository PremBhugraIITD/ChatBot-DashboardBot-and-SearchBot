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
exports.PlaylistManagement = void 0;
// @ts-ignore - We know the SDK exists
const sdk_1 = require("@modelcontextprotocol/sdk");
const googleapis_1 = require("googleapis");
// Utility function for safe execution with error handling
function safelyExecute(fn) {
    return fn().catch(error => {
        throw new Error(`Operation failed: ${error instanceof Error ? error.message : String(error)}`);
    });
}
class PlaylistManagement {
    constructor() {
        const apiKey = process.env.YOUTUBE_API_KEY;
        if (!apiKey) {
            throw new Error('YOUTUBE_API_KEY environment variable is not set.');
        }
        // @ts-ignore - The Google API works this way
        this.youtube = googleapis_1.google.youtube({
            version: "v3",
            auth: apiKey
        });
    }
    // @ts-ignore - We know the SDK exists
    async getPlaylist({ playlistId }) {
        return safelyExecute(async () => {
            const response = await this.youtube.playlists.list({
                part: ['snippet', 'contentDetails'],
                id: [playlistId]
            });
            return response.data.items?.[0] || null;
        });
    }
    // @ts-ignore - We know the SDK exists
    async getPlaylistItems({ playlistId, maxResults = 50 }) {
        return safelyExecute(async () => {
            const response = await this.youtube.playlistItems.list({
                part: ['snippet', 'contentDetails'],
                playlistId,
                maxResults
            });
            return response.data.items || [];
        });
    }
}
exports.PlaylistManagement = PlaylistManagement;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get information about a YouTube playlist',
        parameters: {
            type: 'object',
            properties: {
                playlistId: { type: 'string' }
            },
            required: ['playlistId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], PlaylistManagement.prototype, "getPlaylist", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get videos in a YouTube playlist',
        parameters: {
            type: 'object',
            properties: {
                playlistId: { type: 'string' },
                maxResults: { type: 'number' }
            },
            required: ['playlistId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], PlaylistManagement.prototype, "getPlaylistItems", null);
