"use strict";
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
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
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
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ShortsManager = void 0;
const sdk_1 = require("@modelcontextprotocol/sdk");
const ytdl = __importStar(require("ytdl-core"));
const fs = __importStar(require("fs/promises"));
const path = __importStar(require("path"));
const fluent_ffmpeg_1 = __importDefault(require("fluent-ffmpeg"));
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
class ShortsManager {
    constructor() {
        this.youtube = google.youtube({
            version: 'v3',
            auth: process.env.YOUTUBE_API_KEY
        });
    }
    async createShort({ videoId, startTime, duration = 60, title, effects = [] }) {
        try {
            const outputDir = path.join(process.cwd(), 'shorts');
            await fs.mkdir(outputDir, { recursive: true });
            const outputPath = path.join(outputDir, `${videoId}-short-${Date.now()}.mp4`);
            await this.extractAndProcessSegment(videoId, startTime, Math.min(duration, 60), outputPath, effects);
            const uploadedVideoId = await this.uploadShort(outputPath, title || `Short from ${videoId}`, effects);
            await fs.unlink(outputPath);
            return uploadedVideoId;
        }
        catch (error) {
            throw new Error(`Failed to create Short: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async findShortSegments({ videoId, maxSegments = 3 }) {
        try {
            const video = await this.youtube.videos.list({
                part: ['contentDetails', 'statistics'],
                id: [videoId]
            });
            const markers = await this.getEngagementMarkers(videoId);
            const segments = this.identifyInterestingSegments(markers, maxSegments);
            return segments.map(segment => ({
                startTime: segment.startTime,
                duration: segment.duration,
                confidence: segment.confidence,
                suggestedEffects: this.suggestEffects(segment.type)
            }));
        }
        catch (error) {
            throw new Error(`Failed to find segments: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    // Private helper methods
    async extractAndProcessSegment(videoId, startTime, duration, outputPath, effects) {
        return new Promise((resolve, reject) => {
            const video = ytdl(videoId, { quality: 'highest' });
            let command = (0, fluent_ffmpeg_1.default)(video)
                .seekInput(startTime)
                .duration(duration)
                .size('1080x1920')
                .videoFilter('scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:-1:-1');
            effects.forEach(effect => {
                switch (effect) {
                    case 'speedup':
                        command = command.videoFilters('setpts=0.5*PTS');
                        break;
                    case 'slowdown':
                        command = command.videoFilters('setpts=2*PTS');
                        break;
                    case 'fade':
                        command = command.videoFilters(`fade=in:0:30,fade=out:st=${duration - 1}:d=1`);
                        break;
                    case 'mirror':
                        command = command.videoFilters('hflip');
                        break;
                    case 'blur-background':
                        command = command.complexFilter([
                            '[0:v]split[original][blur]',
                            '[blur]scale=1080:1920,boxblur=20:20[blurred]',
                            '[original]scale=1080:1920:force_original_aspect_ratio=decrease[scaled]',
                            '[blurred][scaled]overlay=(W-w)/2:(H-h)/2'
                        ]);
                        break;
                }
            });
            command
                .outputOptions('-c:v', 'libx264')
                .outputOptions('-c:a', 'aac')
                .outputOptions('-movflags', '+faststart')
                .toFormat('mp4')
                .on('end', () => resolve())
                .on('error', (err) => reject(err))
                .save(outputPath);
        });
    }
    async uploadShort(filePath, title, effects) {
        const fileSize = (await fs.stat(filePath)).size;
        const res = await this.youtube.videos.insert({
            part: ['snippet', 'status'],
            requestBody: {
                snippet: {
                    title,
                    description: `Created with effects: ${effects.join(', ')}`,
                    tags: ['Short'],
                    categoryId: '22'
                },
                status: {
                    privacyStatus: 'public',
                    selfDeclaredMadeForKids: false
                }
            },
            media: {
                body: fs.createReadStream(filePath)
            }
        });
        return res.data.id;
    }
    async getEngagementMarkers(videoId) {
        const [analytics, comments] = await Promise.all([
            this.youtube.videos.list({
                part: ['statistics', 'topicDetails'],
                id: [videoId]
            }),
            this.youtube.commentThreads.list({
                part: ['snippet'],
                videoId,
                order: 'relevance',
                maxResults: 100
            })
        ]);
        const markers = [];
        comments.data.items.forEach(comment => {
            const text = comment.snippet.topLevelComment.snippet.textOriginal;
            const timestamp = this.extractTimestamp(text);
            if (timestamp) {
                markers.push({
                    time: timestamp,
                    type: 'comment',
                    engagement: parseInt(comment.snippet.topLevelComment.snippet.likeCount)
                });
            }
        });
        return markers;
    }
    extractTimestamp(text) {
        const timePattern = /(\d+:)?(\d+):(\d+)/;
        const match = text.match(timePattern);
        if (match) {
            const [hours, minutes, seconds] = match.slice(1).map(t => parseInt(t || '0'));
            return hours * 3600 + minutes * 60 + seconds;
        }
        return null;
    }
    identifyInterestingSegments(markers, maxSegments) {
        const segments = [];
        const windowSize = 60; // 60 seconds for Shorts
        for (let i = 0; i < markers.length; i++) {
            const segmentMarkers = markers.filter(m => m.time >= markers[i].time &&
                m.time < markers[i].time + windowSize);
            if (segmentMarkers.length > 0) {
                const engagement = segmentMarkers.reduce((sum, m) => sum + m.engagement, 0);
                segments.push({
                    startTime: markers[i].time,
                    duration: windowSize,
                    markers: segmentMarkers,
                    engagement,
                    type: this.determineSegmentType(segmentMarkers),
                    confidence: this.calculateConfidence(segmentMarkers)
                });
            }
        }
        return segments
            .sort((a, b) => b.engagement - a.engagement)
            .slice(0, maxSegments);
    }
    determineSegmentType(markers) {
        const types = markers.map(m => m.type);
        const typeCount = {};
        types.forEach(t => {
            typeCount[t] = (typeCount[t] || 0) + 1;
        });
        return Object.entries(typeCount)
            .sort(([, a], [, b]) => b - a)[0][0];
    }
    calculateConfidence(markers) {
        const factors = {
            markerCount: Math.min(markers.length / 5, 1),
            engagementSpread: this.calculateEngagementSpread(markers),
            markerTypes: new Set(markers.map(m => m.type)).size / 3
        };
        return Object.values(factors)
            .reduce((sum, val) => sum + val, 0) / Object.keys(factors).length;
    }
    calculateEngagementSpread(markers) {
        const engagements = markers.map(m => m.engagement);
        const max = Math.max(...engagements);
        const min = Math.min(...engagements);
        return 1 - ((max - min) / max);
    }
    suggestEffects(segmentType) {
        const effects = [];
        switch (segmentType) {
            case 'action':
                effects.push('speedup', 'fade');
                break;
            case 'highlight':
                effects.push('slowdown', 'blur-background');
                break;
            case 'transition':
                effects.push('fade');
                break;
            default:
                effects.push('blur-background');
        }
        return effects;
    }
}
exports.ShortsManager = ShortsManager;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Create Short from video segment',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                startTime: { type: 'number' },
                duration: { type: 'number' },
                title: { type: 'string' },
                effects: { type: 'array', items: { type: 'string' } }
            },
            required: ['videoId', 'startTime']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ShortsManager.prototype, "createShort", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Find optimal segments for Shorts',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                maxSegments: { type: 'number' }
            },
            required: ['videoId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ShortsManager.prototype, "findShortSegments", null);
