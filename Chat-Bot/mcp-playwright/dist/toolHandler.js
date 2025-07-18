import { chromium, firefox, webkit, request } from 'playwright';
import { BROWSER_TOOLS, API_TOOLS } from './tools.js';
import { ScreenshotTool, NavigationTool, CloseBrowserTool, ConsoleLogsTool, ExpectResponseTool, AssertResponseTool, CustomUserAgentTool } from './tools/browser/index.js';
import { ClickTool, IframeClickTool, FillTool, SelectTool, HoverTool, EvaluateTool, IframeFillTool, UploadFileTool, PaymentIframeTool, SwitchToDefaultContentTool, SeleniumWaitTool } from './tools/browser/interaction.js';
import { VisibleTextTool, VisibleHtmlTool } from './tools/browser/visiblePage.js';
import { GetRequestTool, PostRequestTool, PutRequestTool, PatchRequestTool, DeleteRequestTool } from './tools/api/requests.js';
import { GoBackTool, GoForwardTool } from './tools/browser/navigation.js';
import { DragTool, PressKeyTool } from './tools/browser/interaction.js';
import { SaveAsPdfTool } from './tools/browser/output.js';
import { ClickAndSwitchTabTool } from './tools/browser/interaction.js';
// Global state
let browser;
let page;
let currentBrowserType = 'chrome'; // Changed default from 'chromium' to 'chrome'
/**
 * Resets browser and page variables
 * Used when browser is closed
 */
export function resetBrowserState() {
    browser = undefined;
    page = undefined;
    currentBrowserType = 'chromium';
}
/**
 * Sets the provided page to the global page variable
 * @param newPage The Page object to set as the global page
 */
export function setGlobalPage(newPage) {
    page = newPage;
    page.bringToFront(); // Bring the new tab to the front
    console.log("Global page has been updated.");
}
// Tool instances
let screenshotTool;
let navigationTool;
let closeBrowserTool;
let consoleLogsTool;
let clickTool;
let iframeClickTool;
let iframeFillTool;
let fillTool;
let selectTool;
let hoverTool;
let uploadFileTool;
let evaluateTool;
let expectResponseTool;
let assertResponseTool;
let customUserAgentTool;
let visibleTextTool;
let visibleHtmlTool;
let getRequestTool;
let postRequestTool;
let putRequestTool;
let patchRequestTool;
let deleteRequestTool;
// Add these variables at the top with other tool declarations
let goBackTool;
let goForwardTool;
let dragTool;
let pressKeyTool;
let saveAsPdfTool;
let clickAndSwitchTabTool;
// New Selenium-style payment tools
let paymentIframeTool;
let switchToDefaultContentTool;
let seleniumWaitTool;
async function registerConsoleMessage(page) {
    page.on("console", (msg) => {
        if (consoleLogsTool) {
            const type = msg.type();
            const text = msg.text();
            // "Unhandled Rejection In Promise" we injected
            if (text.startsWith("[Playwright]")) {
                const payload = text.replace("[Playwright]", "");
                consoleLogsTool.registerConsoleMessage("exception", payload);
            }
            else {
                consoleLogsTool.registerConsoleMessage(type, text);
            }
        }
    });
    // Uncaught exception
    page.on("pageerror", (error) => {
        if (consoleLogsTool) {
            const message = error.message;
            const stack = error.stack || "";
            consoleLogsTool.registerConsoleMessage("exception", `${message}\n${stack}`);
        }
    });
    // Unhandled rejection in promise
    await page.addInitScript(() => {
        window.addEventListener("unhandledrejection", (event) => {
            const reason = event.reason;
            const message = typeof reason === "object" && reason !== null
                ? reason.message || JSON.stringify(reason)
                : String(reason);
            const stack = reason?.stack || "";
            // Use console.error get "Unhandled Rejection In Promise"
            console.error(`[Playwright][Unhandled Rejection In Promise] ${message}\n${stack}`);
        });
    });
}
/**
 * Ensures a browser is launched and returns the page
 */
export async function ensureBrowser(browserSettings) {
    try {
        // Check if browser exists but is disconnected
        if (browser && !browser.isConnected()) {
            console.error("Browser exists but is disconnected. Cleaning up...");
            try {
                await browser.close().catch(err => console.error("Error closing disconnected browser:", err));
            }
            catch (e) {
                // Ignore errors when closing disconnected browser
            }
            // Reset browser and page references
            resetBrowserState();
        }
        // Launch new browser if needed
        if (!browser) {
            const { viewport, userAgent, browserType = 'chrome' } = browserSettings ?? {};
            // Use headless mode like the working Selenium script
            const headless = browserSettings?.headless ?? false;
            
            // If browser type is changing, force a new browser instance
            if (browser && currentBrowserType !== browserType) {
                try {
                    await browser.close().catch(err => console.error("Error closing browser on type change:", err));
                }
                catch (e) {
                    // Ignore errors
                }
                resetBrowserState();
            }
            console.log(`Launching new ${browserType} browser instance...`);
            
            // Always use chromium for maximum compatibility
            let browserInstance = chromium;
            
            browser = await browserInstance.launch({
                headless,
                channel: 'chrome', // Use real Chrome browser
                args: [
                    // EXACT Selenium args from working index.py - minimal and clean
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--window-size=1920,1080'
                ]
            });
            currentBrowserType = browserType;
            // Add cleanup logic when browser is disconnected
            browser.on('disconnected', () => {
                console.error("Browser disconnected event triggered");
                browser = undefined;
                page = undefined;
            });
            const context = await browser.newContext({
                viewport: {
                    width: viewport?.width ?? 1920,
                    height: viewport?.height ?? 1080,
                },
                // Simple, standard user agent like Selenium
                userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            });
            page = await context.newPage();
            
            // NO anti-detection scripts - Selenium approach is completely clean
            // The working index.py doesn't use any stealth scripts
            
            // Register console message handler
            await registerConsoleMessage(page);
        }
        // Verify page is still valid
        if (!page || page.isClosed()) {
            console.error("Page is closed or invalid. Creating new page...");
            // Create a new page if the current one is invalid
            const contexts = browser.contexts();
            let context;
            if (contexts.length > 0) {
                context = contexts[0];
            }
            else {
                context = await browser.newContext({
                    viewport: {
                        width: browserSettings?.viewport?.width ?? 1920,
                        height: browserSettings?.viewport?.height ?? 1080,
                    },
                    // Simple, standard user agent like Selenium
                    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                });
            }
            page = await context.newPage();
            
            // NO anti-detection scripts - Selenium approach is completely clean
            // The working index.py doesn't use any stealth scripts
            
            // Re-register console message handler
            await registerConsoleMessage(page);
        }
        return page;
    }
    catch (error) {
        console.error("Error ensuring browser:", error);
        // If something went wrong, clean up completely and retry once
        try {
            if (browser) {
                await browser.close().catch(() => { });
            }
        }
        catch (e) {
            // Ignore errors during cleanup
        }
        resetBrowserState();
        // Try one more time from scratch
        const { viewport, userAgent, browserType = 'chrome' } = browserSettings ?? {};
        // Use the appropriate browser engine
        let browserInstance;
        switch (browserType) {
            case 'firefox':
                browserInstance = firefox;
                break;
            case 'webkit':
                browserInstance = webkit;
                break;
            case 'chrome':
            default:
                browserInstance = chromium;
                break;
        }
        
        // Get Chrome channel instead of executable path
        const channel = 'chrome'; // Use installed Chrome
        
        browser = await browserInstance.launch({ 
            headless: browserSettings?.headless ?? true, // Default to headless like the working Selenium script
            channel: channel,
            args: [
                // EXACT Selenium args from working index.py - minimal and clean  
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--window-size=1920,1080'
            ]
        });
        currentBrowserType = browserType;
        browser.on('disconnected', () => {
            console.error("Browser disconnected event triggered (retry)");
            browser = undefined;
            page = undefined;
        });
        const context = await browser.newContext({
            viewport: {
                width: viewport?.width ?? 1920,
                height: viewport?.height ?? 1080,
            },
            // Simple, standard user agent like Selenium
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        });
        page = await context.newPage();
        
        // NO anti-detection scripts - Selenium approach is completely clean
        // The working index.py doesn't use any stealth scripts
        
        await registerConsoleMessage(page);
        return page;
    }
}
/**
 * Creates a new API request context
 */
async function ensureApiContext(url) {
    return await request.newContext({
        baseURL: url,
    });
}
/**
 * Initialize all tool instances
 */
function initializeTools(server) {
    // Browser tools
    if (!screenshotTool)
        screenshotTool = new ScreenshotTool(server);
    if (!navigationTool)
        navigationTool = new NavigationTool(server);
    if (!closeBrowserTool)
        closeBrowserTool = new CloseBrowserTool(server);
    if (!consoleLogsTool)
        consoleLogsTool = new ConsoleLogsTool(server);
    if (!clickTool)
        clickTool = new ClickTool(server);
    if (!iframeClickTool)
        iframeClickTool = new IframeClickTool(server);
    if (!iframeFillTool)
        iframeFillTool = new IframeFillTool(server);
    if (!fillTool)
        fillTool = new FillTool(server);
    if (!selectTool)
        selectTool = new SelectTool(server);
    if (!hoverTool)
        hoverTool = new HoverTool(server);
    if (!uploadFileTool)
        uploadFileTool = new UploadFileTool(server);
    if (!evaluateTool)
        evaluateTool = new EvaluateTool(server);
    if (!expectResponseTool)
        expectResponseTool = new ExpectResponseTool(server);
    if (!assertResponseTool)
        assertResponseTool = new AssertResponseTool(server);
    if (!customUserAgentTool)
        customUserAgentTool = new CustomUserAgentTool(server);
    if (!visibleTextTool)
        visibleTextTool = new VisibleTextTool(server);
    if (!visibleHtmlTool)
        visibleHtmlTool = new VisibleHtmlTool(server);
    // API tools
    if (!getRequestTool)
        getRequestTool = new GetRequestTool(server);
    if (!postRequestTool)
        postRequestTool = new PostRequestTool(server);
    if (!putRequestTool)
        putRequestTool = new PutRequestTool(server);
    if (!patchRequestTool)
        patchRequestTool = new PatchRequestTool(server);
    if (!deleteRequestTool)
        deleteRequestTool = new DeleteRequestTool(server);
    // Initialize new tools
    if (!goBackTool)
        goBackTool = new GoBackTool(server);
    if (!goForwardTool)
        goForwardTool = new GoForwardTool(server);
    if (!dragTool)
        dragTool = new DragTool(server);
    if (!pressKeyTool)
        pressKeyTool = new PressKeyTool(server);
    if (!saveAsPdfTool)
        saveAsPdfTool = new SaveAsPdfTool(server);
    if (!clickAndSwitchTabTool)
        clickAndSwitchTabTool = new ClickAndSwitchTabTool(server);
    // Initialize new Selenium-style payment tools
    if (!paymentIframeTool)
        paymentIframeTool = new PaymentIframeTool(server);
    if (!switchToDefaultContentTool)
        switchToDefaultContentTool = new SwitchToDefaultContentTool(server);
    if (!seleniumWaitTool)
        seleniumWaitTool = new SeleniumWaitTool(server);
}
/**
 * Main handler for tool calls
 */
export async function handleToolCall(name, args, server) {
    // Initialize tools
    initializeTools(server);
    try {
        // Special case for browser close to ensure it always works
        if (name === "playwright_close") {
            if (browser) {
                try {
                    if (browser.isConnected()) {
                        await browser.close().catch(e => console.error("Error closing browser:", e));
                    }
                }
                catch (error) {
                    console.error("Error during browser close in handler:", error);
                }
                finally {
                    resetBrowserState();
                }
                return {
                    content: [{
                            type: "text",
                            text: "Browser closed successfully",
                        }],
                    isError: false,
                };
            }
            return {
                content: [{
                        type: "text",
                        text: "No browser instance to close",
                    }],
                isError: false,
            };
        }
        // Check if we have a disconnected browser that needs cleanup
        if (browser && !browser.isConnected() && BROWSER_TOOLS.includes(name)) {
            console.error("Detected disconnected browser before tool execution, cleaning up...");
            try {
                await browser.close().catch(() => { }); // Ignore errors
            }
            catch (e) {
                // Ignore any errors during cleanup
            }
            resetBrowserState();
        }
        // Prepare context based on tool requirements
        const context = {
            server
        };
        // Set up browser if needed
        if (BROWSER_TOOLS.includes(name)) {
            const browserSettings = {
                viewport: {
                    width: args.width,
                    height: args.height
                },
                userAgent: name === "playwright_custom_user_agent" ? args.userAgent : undefined,
                browserType: args.browserType || 'chromium'
            };
            try {
                context.page = await ensureBrowser(browserSettings);
                context.browser = browser;
                // Additional validation to ensure page is properly set
                if (!context.page) {
                    throw new Error("Failed to create or retrieve browser page");
                }
                console.log(`🌐 Browser context set for ${name}: page=${!!context.page}, browser=${!!context.browser}`);
            }
            catch (error) {
                console.error("Failed to ensure browser:", error);
                return {
                    content: [{
                            type: "text",
                            text: `Failed to initialize browser: ${error.message}. Please try again.`,
                        }],
                    isError: true,
                };
            }
        }
        // Set up API context if needed
        if (API_TOOLS.includes(name)) {
            try {
                context.apiContext = await ensureApiContext(args.url);
            }
            catch (error) {
                return {
                    content: [{
                            type: "text",
                            text: `Failed to initialize API context: ${error.message}`,
                        }],
                    isError: true,
                };
            }
        }
        // Route to appropriate tool
        switch (name) {
            // Browser tools
            case "playwright_navigate": {
                // Run navigation
                const navResult = await navigationTool.execute(args, context);
                // If navigation failed, return immediately
                if (navResult.isError) return navResult;
                // After navigation, fetch interactive elements analysis for agent context
                const htmlArgs = {
                    minimal: true,
                    maxLength: 15000
                };
                const htmlResult = await visibleHtmlTool.execute(htmlArgs, context);
                // Return both navigation and HTML results
                return {
                    content: [
                        ...(Array.isArray(navResult.content) ? navResult.content : [navResult.content]),
                        { type: "text", text: "--- Interactive Elements Analysis ---" },
                        ...(Array.isArray(htmlResult.content) ? htmlResult.content : [htmlResult.content])
                    ],
                    isError: !!(navResult.isError || htmlResult.isError)
                };
            }
            case "playwright_screenshot":
                return await screenshotTool.execute(args, context);
            case "playwright_close":
                return await closeBrowserTool.execute(args, context);
            case "playwright_console_logs":
                return await consoleLogsTool.execute(args, context);
            case "playwright_click": {
                // Capture pre-click interactive elements state for comparison
                const preClickArgs = {
                    minimal: true,
                    maxLength: 15000
                };
                let preClickElements = null;
                try {
                    const preClickResult = await visibleHtmlTool.execute(preClickArgs, context);
                    if (!preClickResult.isError) {
                        preClickElements = preClickResult;
                    }
                } catch (error) {
                    // Continue without pre-click state if capture fails
                    console.log("⚠️ Failed to capture pre-click state:", error.message);
                }
                
                // Run click
                const clickResult = await clickTool.execute(args, context);
                // If click failed, return immediately
                if (clickResult.isError) return clickResult;
                
                // ALWAYS show interactive elements to LLM after every click
                const postClickArgs = {
                    minimal: true,
                    maxLength: 15000
                };
                
                try {
                    const postClickResult = await visibleHtmlTool.execute(postClickArgs, context);
                    
                    if (!postClickResult.isError) {
                        // Check if navigation was detected by looking for the navigation flag in the response
                        const navigationDetected = clickResult.content?.[0]?.text?.includes('🔄 Page navigation detected');
                        
                        if (navigationDetected) {
                            // Navigation detected - show full interactive elements analysis
                            return {
                                content: [
                                    { type: "text", text: "Element clicked successfully and page navigation detected." },
                                    { type: "text", text: "--- Interactive Elements Analysis ---" },
                                    ...(Array.isArray(postClickResult.content) ? postClickResult.content : [postClickResult.content])
                                ],
                                isError: false
                            };
                        } else {
                            // No navigation - check for changes and show either changes or full state
                            let changedElements = null;
                            if (preClickElements) {
                                try {
                                    changedElements = compareInteractiveElements(preClickElements, postClickResult);
                                } catch (error) {
                                    console.log("⚠️ Failed to analyze page changes:", error.message);
                                }
                            }
                            
                            if (changedElements && changedElements.length > 0) {
                                // Changes detected - show both the changes and current state
                                return {
                                    content: [
                                        { type: "text", text: "Element clicked successfully. Page changes detected:" },
                                        { type: "text", text: "--- Page Changes Analysis ---" },
                                        { type: "text", text: changedElements },
                                        { type: "text", text: "--- Current Interactive Elements ---" },
                                        ...(Array.isArray(postClickResult.content) ? postClickResult.content : [postClickResult.content])
                                    ],
                                    isError: false
                                };
                            } else {
                                // No changes detected - show current interactive elements state
                                return {
                                    content: [
                                        { type: "text", text: "Element clicked successfully." },
                                        { type: "text", text: "--- Current Interactive Elements ---" },
                                        ...(Array.isArray(postClickResult.content) ? postClickResult.content : [postClickResult.content])
                                    ],
                                    isError: false
                                };
                            }
                        }
                    } else {
                        // Failed to get interactive elements - return original click result
                        console.log("⚠️ Failed to get post-click interactive elements, returning original click result");
                        return clickResult;
                    }
                } catch (error) {
                    console.log("⚠️ Failed to analyze post-click state:", error.message);
                    // Return original click result if analysis fails
                    return clickResult;
                }
            }
            case "playwright_iframe_click":
                return await iframeClickTool.execute(args, context);
            case "playwright_iframe_fill":
                return await iframeFillTool.execute(args, context);
            case "playwright_fill":
                return await fillTool.execute(args, context);
            case "playwright_select":
                return await selectTool.execute(args, context);
            case "playwright_hover":
                return await hoverTool.execute(args, context);
            case "playwright_upload_file":
                return await uploadFileTool.execute(args, context);
            case "playwright_evaluate":
                return await evaluateTool.execute(args, context);
            case "playwright_expect_response":
                return await expectResponseTool.execute(args, context);
            case "playwright_assert_response":
                return await assertResponseTool.execute(args, context);
            case "playwright_custom_user_agent":
                return await customUserAgentTool.execute(args, context);
            case "playwright_get_visible_text":
                return await visibleTextTool.execute(args, context);
            case "playwright_get_visible_html":
                return await visibleHtmlTool.execute(args, context);
            // API tools
            case "playwright_get":
                return await getRequestTool.execute(args, context);
            case "playwright_post":
                return await postRequestTool.execute(args, context);
            case "playwright_put":
                return await putRequestTool.execute(args, context);
            case "playwright_patch":
                return await patchRequestTool.execute(args, context);
            case "playwright_delete":
                return await deleteRequestTool.execute(args, context);
            // New tools
            case "playwright_go_back":
                return await goBackTool.execute(args, context);
            case "playwright_go_forward":
                return await goForwardTool.execute(args, context);
            case "playwright_drag":
                return await dragTool.execute(args, context);
            case "playwright_press_key":
                return await pressKeyTool.execute(args, context);
            case "playwright_save_as_pdf":
                return await saveAsPdfTool.execute(args, context);
            case "playwright_click_and_switch_tab":
                return await clickAndSwitchTabTool.execute(args, context);
            // Selenium-style payment tools
            case "playwright_payment_iframe":
                return await paymentIframeTool.execute(args, context);
            case "playwright_switch_to_default_content":
                return await switchToDefaultContentTool.execute(args, context);
            case "playwright_selenium_wait":
                return await seleniumWaitTool.execute(args, context);
            default:
                return {
                    content: [{
                            type: "text",
                            text: `Unknown tool: ${name}`,
                        }],
                    isError: true,
                };
        }
    }
    catch (error) {
        console.error(`Error handling tool ${name}:`, error);
        // Handle browser-specific errors at the top level
        if (BROWSER_TOOLS.includes(name)) {
            const errorMessage = error.message;
            if (errorMessage.includes("Target page, context or browser has been closed") ||
                errorMessage.includes("Browser has been disconnected") ||
                errorMessage.includes("Target closed") ||
                errorMessage.includes("Protocol error") ||
                errorMessage.includes("Connection closed")) {
                // Reset browser state if it's a connection issue
                resetBrowserState();
                return {
                    content: [{
                            type: "text",
                            text: `Browser connection error: ${errorMessage}. Browser state has been reset, please try again.`,
                        }],
                    isError: true,
                };
            }
        }
        return {
            content: [{
                    type: "text",
                    text: error instanceof Error ? error.message : String(error),
                }],
            isError: true,
        };
    }
}
/**
 * Get console logs
 */
export function getConsoleLogs() {
    return consoleLogsTool?.getConsoleLogs() ?? [];
}
/**
 * Get screenshots
 */
export function getScreenshots() {
    return screenshotTool?.getScreenshots() ?? new Map();
}
/**
 * Compare two interactive elements results to find new or changed elements
 * @param {Object} preClickResult - Result from visibleHtmlTool before click
 * @param {Object} postClickResult - Result from visibleHtmlTool after click
 * @returns {string|null} - Formatted string of new/changed elements or null if no changes
 */
function compareInteractiveElements(preClickResult, postClickResult) {
    try {
        // Extract content text from both results
        const preContent = Array.isArray(preClickResult.content) 
            ? preClickResult.content.map(c => c.text || c).join('\n')
            : (preClickResult.content?.text || preClickResult.content || '');
            
        const postContent = Array.isArray(postClickResult.content)
            ? postClickResult.content.map(c => c.text || c).join('\n') 
            : (postClickResult.content?.text || postClickResult.content || '');

        // Quick check if content is identical
        if (preContent === postContent) {
            return null; // No changes detected
        }

        // Parse element counts and structure for more detailed comparison
        const preLines = preContent.split('\n').filter(line => line.trim());
        const postLines = postContent.split('\n').filter(line => line.trim());
        
        // Look for new interactive elements sections
        const newElements = [];
        let inNewSection = false;
        
        for (let i = 0; i < postLines.length; i++) {
            const line = postLines[i];
            
            // Check if this line exists in pre-click content
            if (!preLines.includes(line)) {
                // This is a new line - check if it's an element or section header
                if (line.includes('📋') || line.includes('🎯') || 
                    line.includes('📄') || line.includes('🌐')) {
                    // Section header - track it
                    newElements.push(line);
                    inNewSection = true;
                } else if (line.trim().match(/^\d+\./)) {
                    // Numbered element - this is likely a new interactive element
                    newElements.push(line);
                    // Also include the next few lines that describe this element
                    let j = i + 1;
                    while (j < postLines.length && j < i + 3) {
                        const nextLine = postLines[j];
                        if (nextLine.includes('Text:') || nextLine.includes('Alt selectors:') || 
                            nextLine.includes('placeholder:') || nextLine.includes('aria-label:')) {
                            newElements.push(nextLine);
                        } else if (nextLine.trim() === '') {
                            newElements.push(nextLine);
                            break;
                        }
                        j++;
                    }
                } else if (inNewSection && (line.includes('Text:') || line.includes('Alt selectors:'))) {
                    // Element description line
                    newElements.push(line);
                }
            }
        }

        // Filter out purely structural changes and focus on meaningful new elements
        const meaningfulChanges = newElements.filter(line => {
            return line.includes('📋') || line.trim().match(/^\d+\./) || 
                   line.includes('Text:') || line.includes('Alt selectors:');
        });

        if (meaningfulChanges.length === 0) {
            return null; // No meaningful changes
        }

        // Format the output to show only new/changed elements
        let output = '🆕 NEW INTERACTIVE ELEMENTS DETECTED:\n\n';
        
        // Group and format the changes
        let currentSection = '';
        for (const line of meaningfulChanges) {
            if (line.includes('📋')) {
                currentSection = line;
                output += `${line}\n`;
            } else if (line.trim().match(/^\d+\./)) {
                output += `${line}\n`;
            } else if (line.includes('Text:') || line.includes('Alt selectors:')) {
                output += `     ${line}\n`;
            }
        }

        output += '\n✨ These elements appeared after your click action and are now available for interaction.';

        return output.length > 100 ? output : null; // Only return if we have substantial changes
        
    } catch (error) {
        console.log("⚠️ Error comparing interactive elements:", error.message);
        return null;
    }
}

export { registerConsoleMessage };
