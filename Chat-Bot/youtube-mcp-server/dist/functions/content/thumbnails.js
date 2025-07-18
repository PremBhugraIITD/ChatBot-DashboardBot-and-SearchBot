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
exports.ThumbnailManager = void 0;
const sdk_1 = require("@modelcontextprotocol/sdk");
const canvas_1 = require("canvas");
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
class ThumbnailManager {
    constructor() {
        this.youtube = google.youtube({
            version: 'v3',
            auth: process.env.YOUTUBE_API_KEY
        });
    }
    async generateThumbnail({ title, imageUrl, style = 'vlog' }) {
        try {
            const canvas = (0, canvas_1.createCanvas)(1280, 720);
            const ctx = canvas.getContext('2d');
            if (imageUrl) {
                const image = await (0, canvas_1.loadImage)(imageUrl);
                ctx.drawImage(image, 0, 0, 1280, 720);
            }
            else {
                ctx.fillStyle = this.getStyleBackground(style);
                ctx.fillRect(0, 0, 1280, 720);
            }
            await this.applyStyleEffects(ctx, style);
            this.addStyledText(ctx, title, style);
            const outputDir = path.join(process.cwd(), 'thumbnails');
            await fs.mkdir(outputDir, { recursive: true });
            const outputPath = path.join(outputDir, `thumbnail-${Date.now()}.png`);
            const buffer = canvas.toBuffer('image/png');
            await fs.writeFile(outputPath, buffer);
            return outputPath;
        }
        catch (error) {
            throw new Error(`Failed to generate thumbnail: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async abTestThumbnails({ thumbnailPaths, duration = 48 }) {
        try {
            const results = [];
            const hours = duration || 48;
            const interval = hours / thumbnailPaths.length;
            for (let i = 0; i < thumbnailPaths.length; i++) {
                const startTime = new Date();
                startTime.setHours(startTime.getHours() + (i * interval));
                const endTime = new Date(startTime);
                endTime.setHours(endTime.getHours() + interval);
                results.push({
                    thumbnail: thumbnailPaths[i],
                    schedule: {
                        start: startTime.toISOString(),
                        end: endTime.toISOString()
                    }
                });
            }
            return results;
        }
        catch (error) {
            throw new Error(`Failed to setup A/B test: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    // Private style-specific methods
    getStyleBackground(style) {
        switch (style) {
            case 'gaming':
                return '#1a1a1a';
            case 'vlog':
                return '#f5f5f5';
            case 'tutorial':
                return '#ffffff';
            case 'news':
                return '#cc0000';
            default:
                return '#ffffff';
        }
    }
    async applyStyleEffects(ctx, style) {
        switch (style) {
            case 'gaming':
                this.addGamingEffects(ctx);
                break;
            case 'vlog':
                this.addVlogEffects(ctx);
                break;
            case 'tutorial':
                this.addTutorialEffects(ctx);
                break;
            case 'news':
                this.addNewsEffects(ctx);
                break;
        }
    }
    addGamingEffects(ctx) {
        ctx.shadowColor = '#00ff00';
        ctx.shadowBlur = 20;
        ctx.fillStyle = '#00ff00';
        ctx.fillRect(0, 680, 1280, 40);
    }
    addVlogEffects(ctx) {
        const gradient = ctx.createLinearGradient(0, 0, 1280, 720);
        gradient.addColorStop(0, 'rgba(255,255,255,0.1)');
        gradient.addColorStop(1, 'rgba(255,255,255,0.3)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 1280, 720);
    }
    addTutorialEffects(ctx) {
        ctx.fillStyle = '#e0e0e0';
        ctx.fillRect(50, 50, 100, 100);
        ctx.fillRect(1130, 50, 100, 100);
    }
    addNewsEffects(ctx) {
        ctx.fillStyle = '#cc0000';
        ctx.fillRect(0, 0, 1280, 80);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 40px Arial';
        ctx.fillText('BREAKING', 20, 55);
    }
    addStyledText(ctx, text, style) {
        ctx.shadowBlur = 0;
        switch (style) {
            case 'gaming':
                this.addGamingText(ctx, text);
                break;
            case 'vlog':
                this.addVlogText(ctx, text);
                break;
            case 'tutorial':
                this.addTutorialText(ctx, text);
                break;
            case 'news':
                this.addNewsText(ctx, text);
                break;
        }
    }
    addGamingText(ctx, text) {
        ctx.font = 'bold 80px Arial';
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 4;
        ctx.strokeText(text, 50, 650);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(text, 50, 650);
    }
    addVlogText(ctx, text) {
        ctx.font = '70px Arial';
        ctx.fillStyle = '#000000';
        ctx.fillText(text, 50, 650);
    }
    addTutorialText(ctx, text) {
        ctx.font = 'bold 60px Arial';
        ctx.fillStyle = '#333333';
        ctx.fillText(text, 50, 650);
    }
    addNewsText(ctx, text) {
        ctx.font = 'bold 65px Arial';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(text, 50, 150);
    }
}
exports.ThumbnailManager = ThumbnailManager;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Generate custom thumbnail',
        parameters: {
            type: 'object',
            properties: {
                title: { type: 'string' },
                imageUrl: { type: 'string' },
                style: { type: 'string', enum: ['gaming', 'vlog', 'tutorial', 'news'] }
            },
            required: ['title']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ThumbnailManager.prototype, "generateThumbnail", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'A/B test thumbnails',
        parameters: {
            type: 'object',
            properties: {
                thumbnailPaths: { type: 'array', items: { type: 'string' } },
                duration: { type: 'number' }
            },
            required: ['thumbnailPaths']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ThumbnailManager.prototype, "abTestThumbnails", null);
