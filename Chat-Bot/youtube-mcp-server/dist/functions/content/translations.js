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
exports.TranslationManager = void 0;
const sdk_1 = require("@modelcontextprotocol/sdk");
const v2_1 = require("@google-cloud/translate/build/src/v2");
// Utility function for safe execution with error handling
function safelyExecute(fn) {
    return fn().catch(error => {
        throw new Error(`Operation failed: ${error instanceof Error ? error.message : String(error)}`);
    });
}
class TranslationManager {
    constructor() {
        this.youtube = google.youtube({
            version: "v3",
            auth: process.env.YOUTUBE_API_KEY
        });
        this.translate = new v2_1.Translate({
            projectId: process.env.GOOGLE_PROJECT_ID,
            key: process.env.GOOGLE_TRANSLATE_API_KEY
        });
    }
    async translateCaptions({ videoId, targetLanguages }) {
        return safelyExecute(async () => {
            const captions = await this.youtube.captions.list({
                part: ["snippet"],
                videoId
            });
            if (!captions.data.items?.length) {
                throw new Error(`No captions found for video: ${videoId}`);
            }
            const results = {};
            for (const caption of captions.data.items) {
                const track = await this.youtube.captions.download({
                    id: caption.id
                });
                for (const lang of targetLanguages) {
                    const [translation] = await this.translate.translate(track.data, lang);
                    if (!results[lang]) {
                        results[lang] = [];
                    }
                    results[lang].push(translation);
                }
            }
            return results;
        });
    }
    async translateMetadata({ videoId, targetLanguages, fields = ["title", "description", "tags"] }) {
        return safelyExecute(async () => {
            const video = await this.youtube.videos.list({
                part: ["snippet"],
                id: [videoId]
            });
            if (!video.data.items?.length) {
                throw new Error(`Video not found: ${videoId}`);
            }
            const translations = {};
            for (const lang of targetLanguages) {
                translations[lang] = {};
                const snippet = video.data.items[0].snippet;
                for (const field of fields) {
                    if (field === "tags" && snippet.tags) {
                        const [translatedTags] = await this.translate.translate(snippet.tags, lang);
                        translations[lang].tags = Array.isArray(translatedTags)
                            ? translatedTags
                            : [translatedTags];
                    }
                    else {
                        const content = snippet[field];
                        if (content) {
                            const [translation] = await this.translate.translate(content, lang);
                            translations[lang][field] = translation;
                        }
                    }
                }
            }
            return translations;
        });
    }
    async detectLanguages({ videoId, segments = false }) {
        return safelyExecute(async () => {
            const captions = await this.youtube.captions.list({
                part: ["snippet"],
                videoId
            });
            if (!captions.data.items?.length) {
                throw new Error(`No captions found for video: ${videoId}`);
            }
            if (segments) {
                return this.detectLanguageSegments(captions.data.items);
            }
            const allText = await this.getAllCaptionText(captions.data.items);
            const [detection] = await this.translate.detect(allText);
            return {
                language: detection.language,
                confidence: detection.confidence
            };
        });
    }
    async detectLanguageSegments(captions) {
        const segments = [];
        const segmentSize = 1000; // Characters per segment
        for (const caption of captions) {
            const track = await this.youtube.captions.download({
                id: caption.id
            });
            let currentSegment = "";
            const words = track.data.split(/\s+/);
            for (const word of words) {
                currentSegment += word + " ";
                if (currentSegment.length >= segmentSize) {
                    const [detection] = await this.translate.detect(currentSegment);
                    segments.push({
                        text: currentSegment.trim(),
                        language: detection.language,
                        confidence: detection.confidence
                    });
                    currentSegment = "";
                }
            }
            if (currentSegment) {
                const [detection] = await this.translate.detect(currentSegment);
                segments.push({
                    text: currentSegment.trim(),
                    language: detection.language,
                    confidence: detection.confidence
                });
            }
        }
        return this.mergeConsecutiveSegments(segments);
    }
    async getAllCaptionText(captions) {
        const texts = await Promise.all(captions.map(async (caption) => {
            const track = await this.youtube.captions.download({
                id: caption.id
            });
            return track.data;
        }));
        return texts.join(" ").trim();
    }
    mergeConsecutiveSegments(segments) {
        const merged = [];
        let current = null;
        for (const segment of segments) {
            if (!current || current.language !== segment.language) {
                if (current) {
                    merged.push({
                        ...current,
                        confidence: current.confidence.reduce((a, b) => a + b) / current.confidence.length
                    });
                }
                current = {
                    ...segment,
                    confidence: [segment.confidence]
                };
            }
            else {
                current.text += " " + segment.text;
                current.confidence.push(segment.confidence);
            }
        }
        if (current) {
            merged.push({
                ...current,
                confidence: current.confidence.reduce((a, b) => a + b) / current.confidence.length
            });
        }
        return merged;
    }
}
exports.TranslationManager = TranslationManager;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: "Translate video captions to multiple languages",
        parameters: {
            type: "object",
            properties: {
                videoId: { type: "string" },
                targetLanguages: {
                    type: "array",
                    items: { type: "string" }
                }
            },
            required: ["videoId", "targetLanguages"]
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], TranslationManager.prototype, "translateCaptions", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: "Translate video metadata to multiple languages",
        parameters: {
            type: "object",
            properties: {
                videoId: { type: "string" },
                targetLanguages: {
                    type: "array",
                    items: { type: "string" }
                },
                fields: {
                    type: "array",
                    items: {
                        type: "string",
                        enum: ["title", "description", "tags"]
                    }
                }
            },
            required: ["videoId", "targetLanguages"]
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], TranslationManager.prototype, "translateMetadata", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: "Detect spoken languages in video",
        parameters: {
            type: "object",
            properties: {
                videoId: { type: "string" },
                segments: {
                    type: "boolean",
                    description: "Whether to detect languages in segments"
                }
            },
            required: ["videoId"]
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], TranslationManager.prototype, "detectLanguages", null);
