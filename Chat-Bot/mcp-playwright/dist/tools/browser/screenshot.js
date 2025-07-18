import fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { BrowserToolBase } from './base.js';
import { createSuccessResponse } from '../common/types.js';
const defaultDownloadsPath = path.join(os.homedir(), 'Downloads');
// Use MCP server directory for temporary screenshot storage
const mcpServerTempPath = path.join(process.cwd(), 'temp_screenshots');
/**
 * Tool for taking screenshots of pages or elements
 */
export class ScreenshotTool extends BrowserToolBase {
    constructor() {
        super(...arguments);
        this.screenshots = new Map();
    }
    /**
     * Execute the screenshot tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            const screenshotOptions = {
                type: args.type || "png",
                fullPage: !!args.fullPage
            };
            
            let screenshot;
            
            if (args.selector) {
                // Screenshot specific element
                const element = await page.$(args.selector);
                if (!element) {
                    return {
                        content: [{
                                type: "text",
                                text: `Element not found: ${args.selector}`,
                            }],
                        isError: true
                    };
                }
                // Use element.screenshot() for element-specific screenshots
                screenshot = await element.screenshot({
                    type: screenshotOptions.type
                });
            } else {
                // Screenshot entire page or viewport
                screenshot = await page.screenshot(screenshotOptions);
            }
            
            // Generate output path - use temp directory in MCP server folder
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `${args.name || 'screenshot'}-${timestamp}.png`;
            
            // Create temp directory if it doesn't exist
            if (!fs.existsSync(mcpServerTempPath)) {
                fs.mkdirSync(mcpServerTempPath, { recursive: true });
            }
            
            // Use temp directory for temporary storage
            const tempOutputPath = path.join(mcpServerTempPath, filename);
            
            // Save screenshot to temp file first
            fs.writeFileSync(tempOutputPath, screenshot);
            
            const base64Screenshot = screenshot.toString('base64');
            const messages = [`Screenshot temporarily saved to: ${path.relative(process.cwd(), tempOutputPath)}`];
            
            // Write base64 data to file for CAPTCHA tools (avoid large data transfers)
            const chatBotDir = path.join(process.cwd(), 'Chat-Bot');
            const base64FilePath = path.join(chatBotDir, 'image_base64.txt');
            fs.writeFileSync(base64FilePath, base64Screenshot);
            messages.push(`Base64 data written to: Chat-Bot/image_base64.txt`);
            
            // Delete the temporary image file immediately after base64 is written
            try {
                fs.unlinkSync(tempOutputPath);
                messages.push(`Temporary image file deleted: ${filename}`);
            } catch (deleteError) {
                messages.push(`Warning: Could not delete temporary file: ${deleteError.message}`);
            }
            
            // Also save to user's Downloads folder if downloadsDir is specified
            if (args.downloadsDir) {
                const downloadsDir = args.downloadsDir;
                if (!fs.existsSync(downloadsDir)) {
                    fs.mkdirSync(downloadsDir, { recursive: true });
                }
                const userOutputPath = path.join(downloadsDir, filename);
                fs.writeFileSync(userOutputPath, screenshot);
                messages.push(`Screenshot also saved to: ${path.relative(process.cwd(), userOutputPath)}`);
            }
            
            // Handle base64 storage
            if (args.storeBase64 !== false) {
                this.screenshots.set(args.name || 'screenshot', base64Screenshot);
                this.server.notification({
                    method: "notifications/resources/list_changed",
                });
                messages.push(`Screenshot also stored in memory with name: '${args.name || 'screenshot'}'`);
            }
            return createSuccessResponse(messages);
        });
    }
    /**
     * Get all stored screenshots
     */
    getScreenshots() {
        return this.screenshots;
    }
}
