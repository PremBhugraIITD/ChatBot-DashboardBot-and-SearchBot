"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChannelService = void 0;
const googleapis_1 = require("googleapis");
/**
 * Service for interacting with YouTube channels
 */
class ChannelService {
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
     * Get channel details
     */
    async getChannel({ channelId }) {
        try {
            this.initialize();
            const response = await this.youtube.channels.list({
                part: ['snippet', 'statistics', 'contentDetails'],
                id: [channelId]
            });
            return response.data.items?.[0] || null;
        }
        catch (error) {
            throw new Error(`Failed to get channel: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Get channel playlists
     */
    async getPlaylists({ channelId, maxResults = 50 }) {
        try {
            this.initialize();
            const response = await this.youtube.playlists.list({
                part: ['snippet', 'contentDetails'],
                channelId,
                maxResults
            });
            return response.data.items || [];
        }
        catch (error) {
            throw new Error(`Failed to get channel playlists: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Get channel videos
     */
    async listVideos({ channelId, maxResults = 50 }) {
        try {
            this.initialize();
            const response = await this.youtube.search.list({
                part: ['snippet'],
                channelId,
                maxResults,
                order: 'date',
                type: 'video'
            });
            return response.data.items || [];
        }
        catch (error) {
            throw new Error(`Failed to list channel videos: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Get channel statistics
     */
    async getStatistics({ channelId }) {
        try {
            this.initialize();
            const response = await this.youtube.channels.list({
                part: ['statistics'],
                id: [channelId]
            });
            return response.data.items?.[0]?.statistics || null;
        }
        catch (error) {
            throw new Error(`Failed to get channel statistics: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
}
exports.ChannelService = ChannelService;
