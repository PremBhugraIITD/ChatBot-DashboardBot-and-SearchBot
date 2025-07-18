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
exports.ShortsHooksGenerator = void 0;
const sdk_1 = require("@modelcontextprotocol/sdk");
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
class ShortsHooksGenerator {
    constructor() {
        this.youtube = google.youtube({
            version: 'v3',
            auth: process.env.YOUTUBE_API_KEY
        });
    }
    async generateHooks({ topic, style = 'question' }) {
        try {
            const trendingShorts = await this.getTrendingShortsInTopic(topic);
            const patterns = await this.analyzeHookPatterns(trendingShorts);
            return {
                hooks: this.createHooks(topic, style, patterns),
                analysis: patterns.insights,
                suggestedDurations: patterns.timings
            };
        }
        catch (error) {
            throw new Error(`Failed to generate hooks: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async analyzeHookPerformance({ videoIds }) {
        try {
            const performances = await Promise.all(videoIds.map(id => this.analyzeShortHook(id)));
            return {
                patterns: this.findSuccessPatterns(performances),
                recommendations: this.generateHookRecommendations(performances)
            };
        }
        catch (error) {
            throw new Error(`Failed to analyze hook performance: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    // Private helper methods
    async getTrendingShortsInTopic(topic) {
        const response = await this.youtube.search.list({
            part: ['snippet', 'statistics'],
            q: topic,
            type: ['video'],
            videoDuration: 'short',
            order: 'viewCount',
            maxResults: 50
        });
        return response.data.items || [];
    }
    async analyzeHookPatterns(shorts) {
        const patterns = {
            openingPhrases: new Map(),
            avgDuration: 0,
            commonFormats: new Map(),
            insights: [],
            timings: null
        };
        for (const short of shorts) {
            const title = short.snippet.title;
            const firstPhrase = this.extractOpeningPhrase(title);
            const format = this.identifyFormat(title);
            patterns.openingPhrases.set(firstPhrase, (patterns.openingPhrases.get(firstPhrase) || 0) + 1);
            patterns.commonFormats.set(format, (patterns.commonFormats.get(format) || 0) + 1);
        }
        patterns.insights = this.generatePatternInsights(patterns);
        patterns.timings = this.analyzeTimings(shorts);
        return patterns;
    }
    createHooks(topic, style, patterns) {
        const hooks = [];
        const topFormats = [...patterns.commonFormats.entries()]
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([format]) => format);
        switch (style) {
            case 'question':
                hooks.push(`Want to know the truth about ${topic}?`, `Did you know this about ${topic}?`, `The real reason ${topic} is trending...`);
                break;
            case 'statement':
                hooks.push(`This ${topic} hack will change your life`, `Nobody tells you this about ${topic}`, `The ${topic} secret they don't want you to know`);
                break;
            case 'revelation':
                hooks.push(`I discovered something shocking about ${topic}`, `This ${topic} truth will surprise you`, `Everything we know about ${topic} is wrong`);
                break;
            case 'challenge':
                hooks.push(`Can you guess what happens with ${topic}?`, `Try this ${topic} challenge`, `90% of people fail this ${topic} test`);
                break;
        }
        topFormats.forEach(format => {
            hooks.push(this.formatToHook(format, topic));
        });
        return hooks;
    }
    async analyzeShortHook(videoId) {
        const video = await this.youtube.videos.list({
            part: ['snippet', 'statistics'],
            id: [videoId]
        });
        const details = video.data.items?.[0];
        const title = details.snippet.title;
        const stats = details.statistics;
        return {
            hook: this.extractOpeningPhrase(title),
            format: this.identifyFormat(title),
            performance: {
                views: parseInt(stats.viewCount),
                likes: parseInt(stats.likeCount),
                retention: parseInt(stats.likeCount) / parseInt(stats.viewCount)
            }
        };
    }
    extractOpeningPhrase(title) {
        const words = title.split(' ');
        return words.slice(0, Math.min(5, words.length)).join(' ');
    }
    identifyFormat(title) {
        if (title.includes('?'))
            return 'question';
        if (title.includes('!'))
            return 'exclamation';
        if (title.match(/\d+/))
            return 'number';
        if (title.includes('How') || title.includes('Why'))
            return 'explanation';
        return 'statement';
    }
    generatePatternInsights(patterns) {
        const insights = [];
        const topPhrases = [...patterns.openingPhrases.entries()]
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3);
        insights.push(`Most effective opening phrase: "${topPhrases[0][0]}"`);
        insights.push(`Top performing format: ${[...patterns.commonFormats.entries()]
            .sort((a, b) => b[1] - a[1])[0][0]}`);
        return insights;
    }
    analyzeTimings(shorts) {
        return {
            optimalHookLength: '3-5 seconds',
            transitionPoints: [3, 7, 15],
            peakEngagementWindow: '8-12 seconds'
        };
    }
    findSuccessPatterns(performances) {
        const patterns = {
            highPerforming: [],
            commonElements: new Set(),
            avoidElements: new Set()
        };
        performances.sort((a, b) => b.performance.retention - a.performance.retention);
        const topPerformers = performances.slice(0, Math.ceil(performances.length * 0.2));
        const lowPerformers = performances.slice(-Math.ceil(performances.length * 0.2));
        topPerformers.forEach(perf => {
            patterns.highPerforming.push({
                hook: perf.hook,
                format: perf.format,
                metrics: perf.performance
            });
            const elements = this.extractHookElements(perf.hook);
            elements.forEach(el => patterns.commonElements.add(el));
        });
        lowPerformers.forEach(perf => {
            const elements = this.extractHookElements(perf.hook);
            elements.forEach(el => {
                if (!patterns.commonElements.has(el)) {
                    patterns.avoidElements.add(el);
                }
            });
        });
        return patterns;
    }
    generateHookRecommendations(performances) {
        const recommendations = [];
        const patterns = this.findSuccessPatterns(performances);
        recommendations.push(`Use these elements: ${[...patterns.commonElements].join(', ')}`, `Avoid these elements: ${[...patterns.avoidElements].join(', ')}`, `Best performing format: ${patterns.highPerforming[0].format}`);
        return recommendations;
    }
    extractHookElements(hook) {
        const elements = [];
        if (hook.includes('?'))
            elements.push('question');
        if (hook.includes('!'))
            elements.push('exclamation');
        if (hook.match(/\d+/))
            elements.push('number');
        if (hook.match(/you|your/i))
            elements.push('direct-address');
        if (hook.match(/never|always|every/i))
            elements.push('absolute');
        if (hook.match(/secret|hidden|shocking/i))
            elements.push('intrigue');
        if (hook.match(/how|why|what/i))
            elements.push('educational');
        if (hook.toLowerCase().includes('watch'))
            elements.push('call-to-action');
        return elements;
    }
    formatToHook(format, topic) {
        switch (format) {
            case 'question':
                return `Why is ${topic} breaking the internet?`;
            case 'exclamation':
                return `This ${topic} changed everything!`;
            case 'number':
                return `3 ${topic} secrets you need to know`;
            case 'explanation':
                return `How ${topic} really works`;
            default:
                return `The truth about ${topic}`;
        }
    }
}
exports.ShortsHooksGenerator = ShortsHooksGenerator;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Generate hooks for Shorts based on trending patterns',
        parameters: {
            type: 'object',
            properties: {
                topic: { type: 'string' },
                style: { type: 'string', enum: ['question', 'statement', 'revelation', 'challenge'] }
            },
            required: ['topic']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ShortsHooksGenerator.prototype, "generateHooks", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Analyze hook performance from existing Shorts',
        parameters: {
            type: 'object',
            properties: {
                videoIds: { type: 'array', items: { type: 'string' } }
            },
            required: ['videoIds']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], ShortsHooksGenerator.prototype, "analyzeHookPerformance", null);
