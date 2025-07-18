"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PlaylistService = void 0;
const googleapis_1 = require("googleapis");
/**
 * Service for interacting with YouTube playlists
 */
class PlaylistService {
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
            version: "v3",
            auth: apiKey
        });
        this.initialized = true;
    }
    /**
     * Get information about a YouTube playlist
     */
    async getPlaylist({ playlistId }) {
        try {
            this.initialize();
            const response = await this.youtube.playlists.list({
                part: ['snippet', 'contentDetails'],
                id: [playlistId]
            });
            return response.data.items?.[0] || null;
        }
        catch (error) {
            throw new Error(`Failed to get playlist: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Get videos in a YouTube playlist
     */
    async getPlaylistItems({ playlistId, maxResults = 50 }) {
        try {
            this.initialize();
            const response = await this.youtube.playlistItems.list({
                part: ['snippet', 'contentDetails'],
                playlistId,
                maxResults
            });
            return response.data.items || [];
        }
        catch (error) {
            throw new Error(`Failed to get playlist items: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    /**
     * Search for playlists on YouTube
     */
    async searchPlaylists({ query, maxResults = 10 }) {
        try {
            this.initialize();
            const response = await this.youtube.search.list({
                part: ['snippet'],
                q: query,
                maxResults,
                type: ['playlist']
            });
            return response.data.items || [];
        }
        catch (error) {
            throw new Error(`Failed to search playlists: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
}
exports.PlaylistService = PlaylistService;
