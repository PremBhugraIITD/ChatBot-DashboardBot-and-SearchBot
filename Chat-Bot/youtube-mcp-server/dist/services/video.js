"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.VideoService = void 0;
const googleapis_1 = require("googleapis");
/**
 * Service for interacting with YouTube videos
 */
class VideoService {
    constructor() {
        this.initialized = false;
        // Don't initialize in constructor
    }
    /**
     * Initialize the YouTube client only when needed
     */
    initialize() {
        if (this.initialized)
            return;
        const apiKey = process.env.YOUTUBE_API_KEY;
        if (!apiKey) {
            throw new Error('YOUTUBE_API_KEY environment variable is not set.');
        }
        this.youtube = googleapis_1.google.youtube({
            version: 'v3',
            auth: apiKey
        });
        this.initialized = true;
    }
    /**
     * Get detailed information about a YouTube video
     */
    async getVideo({ videoId, parts = ['snippet', 'contentDetails', 'statistics'] }) {
        try {
            this.initialize();
            const response = await this.youtube.videos.list({
                part: parts,
                id: [videoId]
            });
            return response.data.items?.[0] || null;
        }
        catch (error) {
            throw new Error(`Failed to get video: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Search for videos on YouTube
     */
    async searchVideos({ query, maxResults = 10 }) {
        try {
            this.initialize();
            const response = await this.youtube.search.list({
                part: ['snippet'],
                q: query,
                maxResults,
                type: ['video']
            });
            return response.data.items || [];
        }
        catch (error) {
            throw new Error(`Failed to search videos: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Get video statistics like views, likes, and comments
     */
    async getVideoStats({ videoId }) {
        try {
            this.initialize();
            const response = await this.youtube.videos.list({
                part: ['statistics'],
                id: [videoId]
            });
            return response.data.items?.[0]?.statistics || null;
        }
        catch (error) {
            throw new Error(`Failed to get video stats: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Get trending videos
     */
    async getTrendingVideos({ regionCode = 'US', maxResults = 10, videoCategoryId = '' }) {
        try {
            this.initialize();
            const params = {
                part: ['snippet', 'contentDetails', 'statistics'],
                chart: 'mostPopular',
                regionCode,
                maxResults
            };
            if (videoCategoryId) {
                params.videoCategoryId = videoCategoryId;
            }
            const response = await this.youtube.videos.list(params);
            return response.data.items || [];
        }
        catch (error) {
            throw new Error(`Failed to get trending videos: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Get related videos for a specific video
     */
    async getRelatedVideos({ videoId, maxResults = 10 }) {
        try {
            this.initialize();
            const response = await this.youtube.search.list({
                part: ['snippet'],
                relatedToVideoId: videoId,
                maxResults,
                type: ['video']
            });
            return response.data.items || [];
        }
        catch (error) {
            throw new Error(`Failed to get related videos: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
}
exports.VideoService = VideoService;
