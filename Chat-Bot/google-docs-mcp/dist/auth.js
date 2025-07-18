// src/auth.ts
import { google } from 'googleapis';
const SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive' // Full Drive access for listing, searching, and document discovery
];
/**
 * Create OAuth2 client using environment variables for access and refresh tokens
 * This replaces the file-based authentication system
 */
export async function authorize() {
    try {
        // Get tokens from environment variables
        const accessToken = process.env.GDOCS_ACCESS_TOKEN;
        const refreshToken = process.env.GDOCS_REFRESH_TOKEN;
        // Validate required environment variables
        if (!accessToken) {
            throw new Error('GDOCS_ACCESS_TOKEN environment variable is required');
        }
        if (!refreshToken) {
            throw new Error('GDOCS_REFRESH_TOKEN environment variable is required');
        }
        console.error('Creating OAuth2 client with environment tokens...');
        // Create OAuth2 client - we don't need client_id/client_secret for token-only auth
        // The Google API library will handle token refresh automatically
        const oAuth2Client = new google.auth.OAuth2();
        // Set the credentials directly
        oAuth2Client.setCredentials({
            access_token: accessToken,
            refresh_token: refreshToken,
            token_type: 'Bearer',
            scope: SCOPES.join(' ')
        });
        console.error('OAuth2 client configured successfully with environment tokens.');
        return oAuth2Client;
    }
    catch (error) {
        console.error('Failed to authorize with environment tokens:', error);
        throw new Error(`Google Docs authentication failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
}
