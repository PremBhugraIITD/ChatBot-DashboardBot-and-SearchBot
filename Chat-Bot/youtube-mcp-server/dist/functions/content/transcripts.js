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
exports.TranscriptManagement = void 0;
// @ts-ignore - We know the SDK exists
const sdk_1 = require("@modelcontextprotocol/sdk");
const youtube_transcript_1 = require("youtube-transcript");
class TranscriptManagement {
    constructor() {
        // No constructor arguments needed for YouTube transcript
    }
    // @ts-ignore - We know the SDK exists
    async getTranscript({ videoId, language = process.env.YOUTUBE_TRANSCRIPT_LANG || 'en' }) {
        try {
            // @ts-ignore - Library may not match types exactly
            const transcript = await youtube_transcript_1.YoutubeTranscript.fetchTranscript(videoId);
            return {
                videoId,
                language,
                transcript
            };
        }
        catch (error) {
            throw new Error(`Failed to get transcript: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    // @ts-ignore - We know the SDK exists
    async searchTranscript({ videoId, query, language = process.env.YOUTUBE_TRANSCRIPT_LANG || 'en' }) {
        try {
            // @ts-ignore - Library may not match types exactly
            const transcript = await youtube_transcript_1.YoutubeTranscript.fetchTranscript(videoId);
            // Search through transcript for the query
            const matches = transcript.filter(item => item.text.toLowerCase().includes(query.toLowerCase()));
            return {
                videoId,
                query,
                matches,
                totalMatches: matches.length
            };
        }
        catch (error) {
            throw new Error(`Failed to search transcript: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
}
exports.TranscriptManagement = TranscriptManagement;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get the transcript of a YouTube video',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                language: { type: 'string' }
            },
            required: ['videoId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], TranscriptManagement.prototype, "getTranscript", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Search within a transcript',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                query: { type: 'string' },
                language: { type: 'string' }
            },
            required: ['videoId', 'query']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], TranscriptManagement.prototype, "searchTranscript", null);
