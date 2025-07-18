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
exports.ContentAnalysis = void 0;
const sdk_1 = require("@modelcontextprotocol/sdk");
const youtube_transcript_1 = require("youtube-transcript");
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
function safelyExecute(fn) {
    try {
        return fn();
    }
    catch (error) {
        console.error('Execution error:', error instanceof Error ? error.message : 'Unknown error');
        return null;
    }
}
class ContentAnalysis {
    constructor() {
        this.youtube = googleapis_1.google.youtube({
            version: 'v3',
            auth: process.env.YOUTUBE_API_KEY
        });
        this.languageClient = new googleapis_1.google.cloud.LanguageServiceClient();
    }
    async generateSummary({ videoId, maxLength = 250 }) {
        try {
            const transcript = await youtube_transcript_1.YoutubeTranscript.fetchTranscript(videoId);
            const text = transcript.map(t => t.text).join(' ');
            const [result] = await this.languageClient.summarize({
                document: {
                    content: text,
                    type: 'PLAIN_TEXT'
                },
                maxOutputTokens: maxLength
            });
            return result.summary || '';
        }
        catch (error) {
            throw new Error(`Failed to generate summary: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async analyzeSentiment({ videoId }) {
        try {
            const transcript = await youtube_transcript_1.YoutubeTranscript.fetchTranscript(videoId);
            const text = transcript.map(t => t.text).join(' ');
            const [result] = await this.languageClient.analyzeSentiment({
                document: {
                    content: text,
                    type: 'PLAIN_TEXT'
                }
            });
            return {
                sentiment: result.documentSentiment,
                segments: result.sentences.map(s => ({
                    text: s.text?.content,
                    sentiment: s.sentiment
                }))
            };
        }
        catch (error) {
            throw new Error(`Failed to analyze sentiment: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async extractTopics({ videoId }) {
        try {
            const transcript = await youtube_transcript_1.YoutubeTranscript.fetchTranscript(videoId);
            const text = transcript.map(t => t.text).join(' ');
            const [result] = await this.languageClient.analyzeEntities({
                document: {
                    content: text,
                    type: 'PLAIN_TEXT'
                }
            });
            return result.entities || [];
        }
        catch (error) {
            throw new Error(`Failed to extract topics: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async generateTimestamps({ videoId }) {
        try {
            const transcript = await youtube_transcript_1.YoutubeTranscript.fetchTranscript(videoId);
            const [result] = await this.languageClient.classifyText({
                document: {
                    content: transcript.map(t => t.text).join(' '),
                    type: 'PLAIN_TEXT'
                }
            });
            const keyMoments = [];
            let currentSegment = { text: [], timestamp: 0 };
            for (const item of transcript) {
                currentSegment.text.push(item.text);
                if (this.isSignificantChange(item.text) || item.offset >= currentSegment.timestamp + 30000) {
                    keyMoments.push({
                        timestamp: currentSegment.timestamp / 1000,
                        text: currentSegment.text.join(' '),
                        categories: result.categories
                    });
                    currentSegment = { text: [], timestamp: item.offset };
                }
            }
            return keyMoments;
        }
        catch (error) {
            throw new Error(`Failed to generate timestamps: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    isSignificantChange(text) {
        const indicators = [
            'next', 'now', 'let\'s', 'moving on',
            'first', 'second', 'finally',
            'but', 'however', 'although'
        ];
        return indicators.some(i => text.toLowerCase().includes(i));
    }
    async getRecommendations({ videoId, maxResults = 10 }) {
        try {
            const [videoDetails, topics] = await Promise.all([
                this.youtube.videos.list({
                    part: ['snippet', 'topicDetails'],
                    id: [videoId]
                }),
                this.extractTopics({ videoId })
            ]);
            const video = videoDetails.data.items?.[0];
            const topicIds = video.topicDetails?.topicIds || [];
            const categoryId = video.snippet?.categoryId;
            const response = await this.youtube.search.list({
                part: ['snippet'],
                relatedToVideoId: videoId,
                type: ['video'],
                videoCategoryId: categoryId,
                maxResults,
                topicId: topicIds[0] // Use primary topic
            });
            const recommendations = response.data.items?.map(item => {
                const relevanceScore = this.calculateRelevance(item.snippet?.title || '', item.snippet?.description || '', topics);
                return {
                    ...item,
                    relevanceScore
                };
            }) || [];
            return recommendations.sort((a, b) => b.relevanceScore - a.relevanceScore);
        }
        catch (error) {
            throw new Error(`Failed to get recommendations: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    calculateRelevance(title, description, topics) {
        let score = 0;
        const content = (title + ' ' + description).toLowerCase();
        topics.forEach(topic => {
            if (content.includes(topic.name.toLowerCase())) {
                score += topic.salience * 2;
            }
        });
        return score;
    }
}
exports.ContentAnalysis = ContentAnalysis;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Generate video summary from transcript',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                maxLength: { type: 'number' }
            },
            required: ['videoId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ContentAnalysis.prototype, "generateSummary", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Analyze video sentiment',
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
], ContentAnalysis.prototype, "analyzeSentiment", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Extract key topics from video',
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
], ContentAnalysis.prototype, "extractTopics", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Generate key moment timestamps',
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
], ContentAnalysis.prototype, "generateTimestamps", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get personalized video recommendations',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                maxResults: { type: 'number' }
            },
            required: ['videoId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ContentAnalysis.prototype, "getRecommendations", null);
