import axios from 'axios';
import { createTrelloRateLimiters } from './rate-limiter.js';
import * as fs from 'fs/promises';
import * as path from 'path';
// Path for storing active board/workspace configuration
const CONFIG_DIR = path.join(process.env.HOME || process.env.USERPROFILE || '.', '.trello-mcp');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
export class TrelloClient {
    constructor(config) {
        this.config = config;
        this.activeConfig = { ...config };
        this.axiosInstance = axios.create({
            baseURL: 'https://api.trello.com/1',
            params: {
                key: config.apiKey,
                token: config.token,
            },
        });
        this.rateLimiter = createTrelloRateLimiters();
        // Add rate limiting interceptor
        this.axiosInstance.interceptors.request.use(async (config) => {
            await this.rateLimiter.waitForAvailableToken();
            return config;
        });
    }
    /**
     * Load saved configuration from disk
     */
    async loadConfig() {
        try {
            await fs.mkdir(CONFIG_DIR, { recursive: true });
            const data = await fs.readFile(CONFIG_FILE, 'utf8');
            const savedConfig = JSON.parse(data);
            // Only update boardId and workspaceId, keep credentials from env
            if (savedConfig.boardId) {
                this.activeConfig.boardId = savedConfig.boardId;
            }
            if (savedConfig.workspaceId) {
                this.activeConfig.workspaceId = savedConfig.workspaceId;
            }
            console.log(`Loaded configuration: Board ID ${this.activeConfig.boardId}, Workspace ID ${this.activeConfig.workspaceId || 'not set'}`);
        }
        catch (error) {
            // File might not exist yet, that's okay
            if (error instanceof Error && 'code' in error && error.code !== 'ENOENT') {
                throw error;
            }
        }
    }
    /**
     * Save current configuration to disk
     */
    async saveConfig() {
        try {
            await fs.mkdir(CONFIG_DIR, { recursive: true });
            const configToSave = {
                boardId: this.activeConfig.boardId,
                workspaceId: this.activeConfig.workspaceId,
            };
            await fs.writeFile(CONFIG_FILE, JSON.stringify(configToSave, null, 2));
        }
        catch (error) {
            console.error('Failed to save configuration:', error);
            throw new Error('Failed to save configuration');
        }
    }
    /**
     * Get the current active board ID
     */
    get activeBoardId() {
        return this.activeConfig.boardId;
    }
    /**
     * Get the current active workspace ID
     */
    get activeWorkspaceId() {
        return this.activeConfig.workspaceId;
    }
    /**
     * Set the active board
     */
    async setActiveBoard(boardId) {
        // Verify the board exists
        const board = await this.getBoardById(boardId);
        this.activeConfig.boardId = boardId;
        await this.saveConfig();
        return board;
    }
    /**
     * Set the active workspace
     */
    async setActiveWorkspace(workspaceId) {
        // Verify the workspace exists
        const workspace = await this.getWorkspaceById(workspaceId);
        this.activeConfig.workspaceId = workspaceId;
        await this.saveConfig();
        return workspace;
    }
    async handleRequest(request) {
        try {
            return await request();
        }
        catch (error) {
            if (axios.isAxiosError(error)) {
                if (error.response?.status === 429) {
                    // Rate limit exceeded, wait and retry
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    return this.handleRequest(request);
                }
                throw new Error(`Trello API error: ${error.response?.data?.message ?? error.message}`);
            }
            throw error;
        }
    }
    /**
     * List all boards the user has access to
     */
    async listBoards() {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get('/members/me/boards');
            return response.data;
        });
    }
    /**
     * Get a specific board by ID
     */
    async getBoardById(boardId) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get(`/boards/${boardId}`);
            return response.data;
        });
    }
    /**
     * List all workspaces the user has access to
     */
    async listWorkspaces() {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get('/members/me/organizations');
            return response.data;
        });
    }
    /**
     * Get a specific workspace by ID
     */
    async getWorkspaceById(workspaceId) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get(`/organizations/${workspaceId}`);
            return response.data;
        });
    }
    /**
     * List boards in a specific workspace
     */
    async listBoardsInWorkspace(workspaceId) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get(`/organizations/${workspaceId}/boards`);
            return response.data;
        });
    }
    async getCardsByList(listId) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get(`/lists/${listId}/cards`);
            return response.data;
        });
    }
    async getLists() {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get(`/boards/${this.activeConfig.boardId}/lists`);
            return response.data;
        });
    }
    async getRecentActivity(limit = 10) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get(`/boards/${this.activeConfig.boardId}/actions`, {
                params: { limit },
            });
            return response.data;
        });
    }
    async addCard(params) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.post('/cards', {
                idList: params.listId,
                name: params.name,
                desc: params.description,
                due: params.dueDate,
                idLabels: params.labels,
            });
            return response.data;
        });
    }
    async updateCard(params) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.put(`/cards/${params.cardId}`, {
                name: params.name,
                desc: params.description,
                due: params.dueDate,
                idLabels: params.labels,
            });
            return response.data;
        });
    }
    async archiveCard(cardId) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.put(`/cards/${cardId}`, {
                closed: true,
            });
            return response.data;
        });
    }
    async moveCard(cardId, listId) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.put(`/cards/${cardId}`, {
                idList: listId,
            });
            return response.data;
        });
    }
    async addList(name) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.post('/lists', {
                name,
                idBoard: this.activeConfig.boardId,
            });
            return response.data;
        });
    }
    async archiveList(listId) {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.put(`/lists/${listId}/closed`, {
                value: true,
            });
            return response.data;
        });
    }
    async getMyCards() {
        return this.handleRequest(async () => {
            const response = await this.axiosInstance.get('/members/me/cards');
            return response.data;
        });
    }
    async attachImageToCard(cardId, imageUrl, name) {
        return this.handleRequest(async () => {
            // Attaching an image directly from URL without downloading it
            const response = await this.axiosInstance.post(`/cards/${cardId}/attachments`, {
                url: imageUrl,
                name: name || 'Image Attachment',
            });
            return response.data;
        });
    }
}
//# sourceMappingURL=trello-client.js.map