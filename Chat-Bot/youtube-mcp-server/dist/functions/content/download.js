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
exports.VideoDownloader = void 0;
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
class VideoDownloader {
    async downloadVideo({ videoId, format = 'mp4', quality = 'highest' }) {
        try {
            const info = await ytdl.getInfo(videoId);
            const outputDir = path.join(process.cwd(), 'downloads');
            await fs.mkdir(outputDir, { recursive: true });
            const outputPath = path.join(outputDir, `${videoId}-${Date.now()}.${format}`);
            if (format === 'mp4') {
                await this.downloadVideoFormat(info, outputPath, quality);
            }
            else {
                await this.downloadAudioFormat(info, outputPath, format);
            }
            return outputPath;
        }
        catch (error) {
            throw new Error(`Failed to download video: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async extractThumbnail({ videoId, timestamp = 0 }) {
        try {
            const outputDir = path.join(process.cwd(), 'thumbnails');
            await fs.mkdir(outputDir, { recursive: true });
            const outputPath = path.join(outputDir, `${videoId}-${timestamp}-${Date.now()}.jpg`);
            await this.extractFrameAtTimestamp(videoId, timestamp, outputPath);
            return outputPath;
        }
        catch (error) {
            throw new Error(`Failed to extract thumbnail: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async getDownloadOptions({ videoId }) {
        try {
            const info = await ytdl.getInfo(videoId);
            const videoFormats = info.formats
                .filter(f => f.container === 'mp4')
                .map(format => ({
                quality: `${format.height}p`,
                fps: format.fps,
                filesize: format.contentLength ? parseInt(format.contentLength) : null,
                mimeType: format.mimeType
            }))
                .sort((a, b) => (b.quality ? parseInt(b.quality) : 0) - (a.quality ? parseInt(a.quality) : 0));
            const audioFormats = info.formats
                .filter(f => f.mimeType.includes('audio'))
                .map(format => ({
                audioQuality: format.audioBitrate,
                mimeType: format.mimeType
            }));
            return {
                videoDetails: {
                    title: info.videoDetails.title,
                    lengthSeconds: parseInt(info.videoDetails.lengthSeconds),
                    thumbnails: info.videoDetails.thumbnails
                },
                videoFormats,
                audioFormats
            };
        }
        catch (error) {
            throw new Error(`Failed to get download options: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async downloadVideoFormat(info, outputPath, quality) {
        return new Promise((resolve, reject) => {
            const format = this.getBestFormat(info, quality);
            const video = ytdl(info.videoDetails.videoId, { format });
            (0, fluent_ffmpeg_1.default)(video)
                .toFormat('mp4')
                .on('end', () => resolve())
                .on('error', (err) => reject(err))
                .save(outputPath);
        });
    }
    async downloadAudioFormat(info, outputPath, format) {
        return new Promise((resolve, reject) => {
            const video = ytdl(info.videoDetails.videoId, {
                quality: 'highestaudio',
                filter: 'audioonly'
            });
            (0, fluent_ffmpeg_1.default)(video)
                .toFormat(format)
                .on('end', () => resolve())
                .on('error', (err) => reject(err))
                .save(outputPath);
        });
    }
    async extractFrameAtTimestamp(videoId, timestamp, outputPath) {
        return new Promise((resolve, reject) => {
            const video = ytdl(videoId);
            (0, fluent_ffmpeg_1.default)(video)
                .screenshots({
                timestamps: [timestamp],
                filename: path.basename(outputPath),
                folder: path.dirname(outputPath)
            })
                .on('end', () => resolve())
                .on('error', (err) => reject(err));
        });
    }
    getBestFormat(info, quality) {
        const formats = info.formats.filter(f => f.container === 'mp4');
        if (quality === 'highest') {
            return formats.sort((a, b) => (b.height || 0) - (a.height || 0))[0];
        }
        if (quality === 'lowest') {
            return formats.sort((a, b) => (a.height || 0) - (b.height || 0))[0];
        }
        const targetHeight = parseInt(quality);
        return formats
            .sort((a, b) => Math.abs((a.height || 0) - targetHeight) - Math.abs((b.height || 0) - targetHeight))[0];
    }
}
exports.VideoDownloader = VideoDownloader;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Download video in specified format',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                format: { type: 'string', enum: ['mp4', 'mp3', 'wav'] },
                quality: { type: 'string', enum: ['highest', 'lowest', '1080p', '720p', '480p', '360p'] }
            },
            required: ['videoId', 'format']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], VideoDownloader.prototype, "downloadVideo", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Extract video thumbnail',
        parameters: {
            type: 'object',
            properties: {
                videoId: { type: 'string' },
                timestamp: { type: 'number' }
            },
            required: ['videoId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], VideoDownloader.prototype, "extractThumbnail", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get video download options',
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
], VideoDownloader.prototype, "getDownloadOptions", null);
