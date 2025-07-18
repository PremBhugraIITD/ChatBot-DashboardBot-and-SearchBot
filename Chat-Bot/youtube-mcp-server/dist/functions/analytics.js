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
exports.AnalyticsManagement = void 0;
const sdk_1 = require("@modelcontextprotocol/sdk");
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
class AnalyticsManagement {
    constructor() {
        this.youtube = googleapis_1.google.youtube({
            version: 'v3',
            auth: process.env.YOUTUBE_API_KEY
        });
    }
    async analyzeChannelGrowth({ channelId, period = '30days' }) {
        try {
            const analytics = await this.youtube.channelAnalytics.query({
                ids: 'channel==' + channelId,
                metrics: [
                    'views',
                    'estimatedMinutesWatched',
                    'averageViewDuration',
                    'subscribersGained',
                    'subscribersLost',
                    'likes',
                    'comments'
                ].join(','),
                dimensions: 'day',
                startDate: this.getStartDate(period),
                endDate: 'today'
            });
            return this.processGrowthMetrics(analytics.data.rows || []);
        }
        catch (error) {
            throw new Error(`Failed to analyze channel growth: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async getVideoMetrics({ videoId }) {
        try {
            const [videoStats, analytics] = await Promise.all([
                this.youtube.videos.list({
                    part: ['statistics'],
                    id: [videoId]
                }),
                this.youtube.videoAnalytics.query({
                    ids: 'video==' + videoId,
                    metrics: [
                        'views',
                        'estimatedMinutesWatched',
                        'averageViewDuration',
                        'averageViewPercentage',
                        'annotationClickThroughRate',
                        'annotationCloseRate',
                        'subscribersGained',
                        'shares'
                    ].join(','),
                    dimensions: 'day'
                })
            ]);
            return {
                overall: videoStats.data.items?.[0].statistics,
                detailed: this.processVideoMetrics(analytics.data.rows || [])
            };
        }
        catch (error) {
            throw new Error(`Failed to get video metrics: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async predictPerformance({ videoId }) {
        try {
            const [video, analytics] = await Promise.all([
                this.youtube.videos.list({
                    part: ['snippet', 'statistics'],
                    id: [videoId]
                }),
                this.getVideoMetrics({ videoId })
            ]);
            const predictions = this.generatePredictions(video.data.items?.[0], analytics);
            return {
                predictions,
                confidence: this.calculateConfidence(video.data.items?.[0]),
                factors: this.getInfluencingFactors(video.data.items?.[0])
            };
        }
        catch (error) {
            throw new Error(`Failed to predict performance: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    getStartDate(period) {
        const date = new Date();
        switch (period) {
            case '7days':
                date.setDate(date.getDate() - 7);
                break;
            case '30days':
                date.setDate(date.getDate() - 30);
                break;
            case '90days':
                date.setDate(date.getDate() - 90);
                break;
            case '365days':
                date.setDate(date.getDate() - 365);
                break;
        }
        return date.toISOString().split('T')[0];
    }
    processGrowthMetrics(data) {
        const metrics = {
            viewsGrowth: 0,
            subscriberGrowth: 0,
            engagementTrends: {
                likes: [],
                comments: [],
                shares: []
            },
            watchTimeAnalysis: {
                total: 0,
                average: 0,
                trend: 'stable'
            }
        };
        if (data.length > 1) {
            const firstDay = data[0];
            const lastDay = data[data.length - 1];
            metrics.viewsGrowth = ((lastDay.views - firstDay.views) / firstDay.views) * 100;
            metrics.subscriberGrowth = lastDay.subscribersGained - lastDay.subscribersLost;
            data.forEach(day => {
                metrics.engagementTrends.likes.push(day.likes);
                metrics.engagementTrends.comments.push(day.comments);
                metrics.watchTimeAnalysis.total += day.estimatedMinutesWatched;
            });
            metrics.watchTimeAnalysis.average = metrics.watchTimeAnalysis.total / data.length;
            metrics.watchTimeAnalysis.trend = this.analyzeTrend(data.map(d => d.estimatedMinutesWatched));
        }
        return metrics;
    }
    processVideoMetrics(data) {
        return {
            viewsOverTime: data.map(d => ({
                date: d[0],
                views: d[1],
                watchTime: d[2]
            })),
            retentionRate: this.calculateRetention(data),
            peakEngagementPoints: this.findPeaks(data),
            audienceRetention: this.analyzeAudienceRetention(data)
        };
    }
    analyzeTrend(values) {
        if (values.length < 2)
            return 'insufficient_data';
        const gradient = values[values.length - 1] - values[0];
        const percentage = (gradient / values[0]) * 100;
        if (percentage > 10)
            return 'growing';
        if (percentage < -10)
            return 'declining';
        return 'stable';
    }
    calculateRetention(data) {
        if (!data.length)
            return 0;
        const totalViews = data.reduce((sum, day) => sum + day[1], 0);
        const completedViews = data.reduce((sum, day) => sum + (day[2] >= 0.9 ? day[1] : 0), 0);
        return (completedViews / totalViews) * 100;
    }
    findPeaks(data) {
        const peaks = [];
        const viewThreshold = Math.max(...data.map(d => d[1])) * 0.8;
        data.forEach((day, index) => {
            if (day[1] >= viewThreshold) {
                peaks.push({
                    date: day[0],
                    views: day[1],
                    percentile: (day[1] / viewThreshold) * 100
                });
            }
        });
        return peaks;
    }
    analyzeAudienceRetention(data) {
        const segments = {
            start: 0,
            middle: 0,
            end: 0
        };
        data.forEach((day, index) => {
            const position = index / data.length;
            const retention = day[2] / day[1]; // watchTime / views
            if (position < 0.33)
                segments.start += retention;
            else if (position < 0.66)
                segments.middle += retention;
            else
                segments.end += retention;
        });
        const normalize = (val, count) => (val / count) * 100;
        const segmentSize = Math.floor(data.length / 3);
        return {
            startRetention: normalize(segments.start, segmentSize),
            middleRetention: normalize(segments.middle, segmentSize),
            endRetention: normalize(segments.end, segmentSize)
        };
    }
    generatePredictions(video, analytics) {
        const baseMetrics = video.statistics;
        const projectedViews = this.projectMetric(baseMetrics.viewCount, analytics.detailed.viewsOverTime);
        const projectedEngagement = this.projectEngagement(baseMetrics, analytics);
        return {
            views: {
                next7Days: projectedViews.week,
                next30Days: projectedViews.month,
                next90Days: projectedViews.quarter
            },
            engagement: {
                likes: projectedEngagement.likes,
                comments: projectedEngagement.comments,
                shares: projectedEngagement.shares
            },
            milestones: this.predictMilestones(baseMetrics, projectedViews)
        };
    }
    projectMetric(current, history) {
        const growth = history.reduce((acc, day, i) => {
            if (i === 0)
                return acc;
            return acc + ((day.views - history[i - 1].views) / history[i - 1].views);
        }, 0) / (history.length - 1);
        return {
            week: current * Math.pow(1 + growth, 7),
            month: current * Math.pow(1 + growth, 30),
            quarter: current * Math.pow(1 + growth, 90)
        };
    }
    projectEngagement(current, analytics) {
        const engagementRates = {
            likes: current.likeCount / current.viewCount,
            comments: current.commentCount / current.viewCount,
            shares: analytics.detailed.peakEngagementPoints.length / current.viewCount
        };
        const projected = this.projectMetric(current.viewCount, analytics.detailed.viewsOverTime);
        return {
            likes: projected.month * engagementRates.likes,
            comments: projected.month * engagementRates.comments,
            shares: projected.month * engagementRates.shares
        };
    }
    predictMilestones(current, projected) {
        const milestones = [];
        const metrics = ['viewCount', 'likeCount', 'commentCount'];
        metrics.forEach(metric => {
            const value = parseInt(current[metric]);
            const nextMilestone = Math.pow(10, Math.floor(Math.log10(value)) + 1);
            if (nextMilestone > value) {
                const daysToMilestone = this.calculateDaysToMilestone(value, nextMilestone, projected);
                milestones.push({
                    metric,
                    current: value,
                    next: nextMilestone,
                    estimatedDays: daysToMilestone
                });
            }
        });
        return milestones;
    }
    calculateDaysToMilestone(current, target, projected) {
        const dailyGrowth = (projected.month - current) / 30;
        return Math.ceil((target - current) / dailyGrowth);
    }
    calculateConfidence(video) {
        const factors = {
            age: this.getAgeFactor(video.snippet.publishedAt),
            consistency: this.getConsistencyFactor(video.statistics),
            dataPoints: this.getDataPointsFactor(video.statistics),
            category: this.getCategoryFactor(video.snippet.categoryId)
        };
        return Object.values(factors).reduce((sum, val) => sum + val, 0) / Object.keys(factors).length;
    }
    getInfluencingFactors(video) {
        const factors = [];
        const stats = video.statistics;
        const snippet = video.snippet;
        if (parseInt(stats.viewCount) > 10000) {
            factors.push('High view count indicates strong initial performance');
        }
        if (parseInt(stats.likeCount) / parseInt(stats.viewCount) > 0.1) {
            factors.push('Above average engagement rate');
        }
        if (snippet.tags && snippet.tags.length > 10) {
            factors.push('Well-optimized tags');
        }
        return factors;
    }
    getAgeFactor(publishedAt) {
        const age = Date.now() - new Date(publishedAt).getTime();
        const days = age / (1000 * 60 * 60 * 24);
        return Math.min(1, days / 30); // Higher confidence with more historical data
    }
    getConsistencyFactor(stats) {
        const engagementRate = parseInt(stats.likeCount) / parseInt(stats.viewCount);
        return engagementRate > 0.05 ? 1 : engagementRate * 20;
    }
    getDataPointsFactor(stats) {
        const points = Object.values(stats).filter(val => parseInt(val) > 0).length;
        return points / Object.keys(stats).length;
    }
    getCategoryFactor(categoryId) {
        const predictableCategories = ['10', '20', '27', '28']; // Music, Gaming, Education, Science
        return predictableCategories.includes(categoryId) ? 1 : 0.8;
    }
}
exports.AnalyticsManagement = AnalyticsManagement;
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Analyze channel growth trends',
        parameters: {
            type: 'object',
            properties: {
                channelId: { type: 'string' },
                period: { type: 'string', enum: ['7days', '30days', '90days', '365days'] }
            },
            required: ['channelId']
        }
    }),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], AnalyticsManagement.prototype, "analyzeChannelGrowth", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Get video performance metrics',
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
], AnalyticsManagement.prototype, "getVideoMetrics", null);
__decorate([
    (0, sdk_1.MCPFunction)({
        description: 'Predict future video performance',
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
], AnalyticsManagement.prototype, "predictPerformance", null);
