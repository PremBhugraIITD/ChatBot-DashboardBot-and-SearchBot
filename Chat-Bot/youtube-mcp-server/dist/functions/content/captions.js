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
Object.defineProperty(exports, "__esModule", { value: true });
exports.CaptionManager = void 0;
const sdk_1 = require("@modelcontextprotocol/sdk");
const fs = __importStar(require("fs/promises"));
const path = __importStar(require("path"));
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
class CaptionManager {
    // [Previous methods remain the same]
    async uploadCaptions(videoId, captions, language) {
        const name = `${language}_${Date.now()}.srt`;
        const tmpPath = path.join(process.cwd(), 'temp', name);
        await fs.mkdir(path.dirname(tmpPath), { recursive: true });
        await fs.writeFile(tmpPath, captions);
        await this.youtube.captions.insert({
            part: ['snippet'],
            requestBody: {
                snippet: {
                    videoId,
                    language,
                    name,
                    isDraft: false
                }
            },
            media: {
                body: fs.createReadStream(tmpPath)
            }
        });
        await fs.unlink(tmpPath);
    }
    async getCaptionTracks(videoId) {
        const response = await this.youtube.captions.list({
            part: ['snippet'],
            videoId
        });
        return response.data.items || [];
    }
    async generateTranslations(videoId, languages, sourceCaptions) {
        for (const language of languages) {
            const translated = await this.translateCaptions(sourceCaptions, language);
            await this.uploadCaptions(videoId, translated, language);
        }
    }
    async translateCaptions(captions, targetLanguage) {
        const lines = captions.split('\n');
        let output = '';
        let isText = false;
        for (const line of lines) {
            if (line.trim() === '') {
                output += '\n';
                isText = false;
                continue;
            }
            if (/^\d+$/.test(line.trim()) || /^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$/.test(line.trim())) {
                output += line + '\n';
                isText = false;
            }
            else if (isText || !line.includes('-->')) {
                const [translation] = await this.translateClient.translate(line, targetLanguage);
                output += translation + '\n';
                isText = true;
            }
            else {
                output += line + '\n';
            }
        }
        return output;
    }
    formatTime(seconds) {
        const pad = (n) => n.toString().padStart(2, '0');
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);
        return `${pad(h)}:${pad(m)}:${pad(s)},${ms.toString().padStart(3, '0')}`;
    }
    calculateSimilarity(str1, str2) {
        const len1 = str1.length;
        const len2 = str2.length;
        const matrix = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(0));
        for (let i = 0; i <= len1; i++)
            matrix[i][0] = i;
        for (let j = 0; j <= len2; j++)
            matrix[0][j] = j;
        for (let i = 1; i <= len1; i++) {
            for (let j = 1; j <= len2; j++) {
                const cost = str1[i - 1] === str2[j - 1] ? 0 : 1;
                matrix[i][j] = Math.min(matrix[i - 1][j] + 1, // deletion
                matrix[i][j - 1] + 1, // insertion
                matrix[i - 1][j - 1] + cost // substitution
                );
            }
        }
        const maxLen = Math.max(len1, len2);
        return 1 - matrix[len1][len2] / maxLen;
    }
    // Optional additional methods for advanced caption management
    async analyzeCaptionQuality({ videoId }) {
        try {
            const captionTracks = await this.getCaptionTracks(videoId);
            const qualityAnalysis = await Promise.all(captionTracks.map(async (track) => {
                const captionContent = await this.downloadCaptionTrack(track);
                return {
                    language: track.snippet.language,
                    complexity: this.calculateCaptionComplexity(captionContent),
                    readingSpeed: this.calculateReadingSpeed(captionContent),
                    wordCount: this.countWords(captionContent)
                };
            }));
            return {
                videoId,
                captionQuality: qualityAnalysis
            };
        }
        catch (error) {
            throw new Error(`Failed to analyze caption quality: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async downloadCaptionTrack(track) {
        const response = await this.youtube.captions.download({
            id: track.id,
            tfmt: 'srt'
        });
        return response.data;
    }
    calculateCaptionComplexity(captions) {
        const lines = captions.split('\n').filter(line => !line.trim().match(/^\d+$/) &&
            !line.trim().match(/^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$/));
        const totalChars = lines.join(' ').length;
        const uniqueWords = new Set(lines.join(' ').toLowerCase().split(/\s+/));
        return (uniqueWords.size / totalChars) * 1000; // Lexical density metric
    }
    calculateReadingSpeed(captions) {
        const lines = captions.split('\n').filter(line => !line.trim().match(/^\d+$/) &&
            !line.trim().match(/^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$/));
        const wordCount = lines.join(' ').split(/\s+/).length;
        const estimatedReadTime = lines.length * 2; // Assume 2 seconds per caption line
        return wordCount / estimatedReadTime; // Words per second
    }
    countWords(captions) {
        const lines = captions.split('\n').filter(line => !line.trim().match(/^\d+$/) &&
            !line.trim().match(/^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$/));
        return lines.join(' ').split(/\s+/).length;
    }
}
exports.CaptionManager = CaptionManager;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Analyze caption quality and complexity',
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
], CaptionManager.prototype, "analyzeCaptionQuality", null);
