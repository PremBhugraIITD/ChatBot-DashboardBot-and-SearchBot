import { z } from 'zod';
import { createClickUpClient } from '../clickup-client/index.js';
import { createDocsClient } from '../clickup-client/docs.js';
import { createAuthClient } from '../clickup-client/auth.js';
// Create clients
const clickUpClient = createClickUpClient();
const docsClient = createDocsClient(clickUpClient);
const authClient = createAuthClient(clickUpClient);
export function setupDocTools(server) {
    // Register get_doc_content tool
    server.tool('get_doc_content', 'Get the content of a specific ClickUp doc. Returns combined content from all pages in the doc.', {
        doc_id: z.string().describe('The ID of the doc to get'),
        workspace_id: z.string().describe('The ID of the workspace containing the doc')
    }, async ({ doc_id, workspace_id }) => {
        try {
            // Get the pages of the doc
            const pages = await docsClient.getDocPages(workspace_id, doc_id);
            // Combine the content of all pages
            let combinedContent = '';
            if (Array.isArray(pages)) {
                for (const page of pages) {
                    if (page.content) {
                        combinedContent += page.content + '\n\n';
                    }
                }
            }
            return {
                content: [{ type: 'text', text: combinedContent || 'No content found in this doc.' }]
            };
        }
        catch (error) {
            console.error('Error getting doc content:', error);
            return {
                content: [{ type: 'text', text: `Error getting doc content: ${error.message}` }],
                isError: true
            };
        }
    });
    // Register search_docs tool
    server.tool('search_docs', 'Search for docs in a ClickUp workspace using a query string. Returns matching docs with their metadata.', {
        workspace_id: z.string().describe('The ID of the workspace to search in'),
        query: z.string().describe('The search query'),
        cursor: z.string().optional().describe('Cursor for pagination')
    }, async ({ workspace_id, query, cursor }) => {
        try {
            // Search for docs in the workspace
            const result = await docsClient.searchDocs(workspace_id, { query, cursor });
            return {
                content: [{ type: 'text', text: JSON.stringify(result.docs, null, 2) }]
            };
        }
        catch (error) {
            console.error('Error searching docs:', error);
            return {
                content: [{ type: 'text', text: `Error searching docs: ${error.message}` }],
                isError: true
            };
        }
    });
    // Register get_docs_from_workspace tool
    server.tool('get_docs_from_workspace', 'Get all docs from a ClickUp workspace. Supports pagination and filtering for deleted/archived docs.', {
        workspace_id: z.string().describe('The ID of the workspace to get docs from'),
        cursor: z.string().optional().describe('Cursor for pagination'),
        deleted: z.boolean().optional().describe('Whether to include deleted docs'),
        archived: z.boolean().optional().describe('Whether to include archived docs'),
        limit: z.number().optional().describe('The maximum number of docs to return')
    }, async ({ workspace_id, cursor, deleted, archived, limit }) => {
        try {
            // Get docs from the workspace
            const result = await docsClient.getDocsFromWorkspace(workspace_id, {
                cursor,
                deleted: deleted !== undefined ? deleted : false,
                archived: archived !== undefined ? archived : false,
                limit: limit || 50
            });
            return {
                content: [{ type: 'text', text: JSON.stringify(result.docs, null, 2) }]
            };
        }
        catch (error) {
            console.error('Error getting docs from workspace:', error);
            return {
                content: [{ type: 'text', text: `Error getting docs from workspace: ${error.message}` }],
                isError: true
            };
        }
    });
    // Register get_doc_pages tool
    server.tool('get_doc_pages', 'Get the pages of a specific ClickUp doc. Returns page content in the requested format (markdown or plain text).', {
        doc_id: z.string().describe('The ID of the doc to get pages from'),
        workspace_id: z.string().describe('The ID of the workspace containing the doc'),
        content_format: z.enum(['text/md', 'text/plain']).optional().describe('The format to return the content in')
    }, async ({ doc_id, workspace_id, content_format }) => {
        try {
            // Get the pages of the doc
            const pages = await docsClient.getDocPages(workspace_id, doc_id, content_format);
            return {
                content: [{ type: 'text', text: JSON.stringify(pages, null, 2) }]
            };
        }
        catch (error) {
            console.error('Error getting doc pages:', error);
            return {
                content: [{ type: 'text', text: `Error getting doc pages: ${error.message}` }],
                isError: true
            };
        }
    });
}
//# sourceMappingURL=doc-tools.js.map