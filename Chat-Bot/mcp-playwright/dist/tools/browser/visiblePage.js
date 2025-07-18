import { resetBrowserState } from "../../toolHandler.js";
import { createErrorResponse, createSuccessResponse } from "../common/types.js";
import { BrowserToolBase } from "./base.js";
/**
 * Tool for getting the visible text content of the current page
 */
export class VisibleTextTool extends BrowserToolBase {
    /**
     * Execute the visible text page tool
     */
    async execute(args, context) {
        // Check if browser is available
        if (!context.browser || !context.browser.isConnected()) {
            // If browser is not connected, we need to reset the state to force recreation
            resetBrowserState();
            return createErrorResponse("Browser is not connected. The connection has been reset - please retry your navigation.");
        }
        // Check if page is available and not closed
        if (!context.page || context.page.isClosed()) {
            return createErrorResponse("Page is not available or has been closed. Please retry your navigation.");
        }
        return this.safeExecute(context, async (page) => {
            try {
                const visibleText = await page.evaluate(() => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
                        acceptNode: (node) => {
                            const style = window.getComputedStyle(node.parentElement);
                            return (style.display !== "none" && style.visibility !== "hidden")
                                ? NodeFilter.FILTER_ACCEPT
                                : NodeFilter.FILTER_REJECT;
                        },
                    });
                    let text = "";
                    let node;
                    while ((node = walker.nextNode())) {
                        const trimmedText = node.textContent?.trim();
                        if (trimmedText) {
                            text += trimmedText + "\n";
                        }
                    }
                    return text.trim();
                });
                // Truncate logic
                const maxLength = typeof args.maxLength === 'number' ? args.maxLength : 20000;
                let output = visibleText;
                let truncated = false;
                if (output.length > maxLength) {
                    output = output.slice(0, maxLength) + '\n[Output truncated due to size limits]';
                    truncated = true;
                }
                return createSuccessResponse(`Visible text content:\n${output}`);
            }
            catch (error) {
                return createErrorResponse(`Failed to get visible text content: ${error.message}`);
            }
        });
    }
}
/**
 * Tool for getting the visible HTML content of the current page
 */
export class VisibleHtmlTool extends BrowserToolBase {
    /**
     * Execute the visible HTML page tool
     */
    async execute(args, context) {
        // Check if browser is available
        if (!context.browser || !context.browser.isConnected()) {
            // If browser is not connected, we need to reset the state to force recreation
            resetBrowserState();
            return createErrorResponse("Browser is not connected. The connection has been reset - please retry your navigation.");
        }
        // Check if page is available and not closed
        if (!context.page || context.page.isClosed()) {
            return createErrorResponse("Page is not available or has been closed. Please retry your navigation.");
        }
        return this.safeExecute(context, async (page) => {
            try {
                // Check if minimal mode is requested
                if (args.minimal === true) {
                    return await this.getMinimalHtml(page, args);
                }
                
                const { selector, removeComments, removeStyles, removeMeta, minify, cleanHtml } = args;
                // Default removeScripts to true unless explicitly set to false
                const removeScripts = args.removeScripts === false ? false : true;
                // Get the HTML content
                let htmlContent;
                if (selector) {
                    // If a selector is provided, get only the HTML for that element
                    const element = await page.$(selector);
                    if (!element) {
                        return createErrorResponse(`Element with selector "${selector}" not found`);
                    }
                    htmlContent = await page.evaluate((el) => el.outerHTML, element);
                }
                else {
                    // Otherwise get the full page HTML
                    htmlContent = await page.content();
                }
                // Determine if we need to apply filters
                const shouldRemoveScripts = removeScripts || cleanHtml;
                const shouldRemoveComments = removeComments || cleanHtml;
                const shouldRemoveStyles = removeStyles || cleanHtml;
                const shouldRemoveMeta = removeMeta || cleanHtml;
                // Apply filters in the browser context
                if (shouldRemoveScripts || shouldRemoveComments || shouldRemoveStyles || shouldRemoveMeta || minify) {
                    htmlContent = await page.evaluate(({ html, removeScripts, removeComments, removeStyles, removeMeta, minify }) => {
                        // Create a DOM parser to work with the HTML
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        // Remove script tags if requested
                        if (removeScripts) {
                            const scripts = doc.querySelectorAll('script');
                            scripts.forEach(script => script.remove());
                        }
                        // Remove style tags if requested
                        if (removeStyles) {
                            const styles = doc.querySelectorAll('style');
                            styles.forEach(style => style.remove());
                        }
                        // Remove meta tags if requested
                        if (removeMeta) {
                            const metaTags = doc.querySelectorAll('meta');
                            metaTags.forEach(meta => meta.remove());
                        }
                        // Remove HTML comments if requested
                        if (removeComments) {
                            const removeComments = (node) => {
                                const childNodes = node.childNodes;
                                for (let i = childNodes.length - 1; i >= 0; i--) {
                                    const child = childNodes[i];
                                    if (child.nodeType === 8) { // 8 is for comment nodes
                                        node.removeChild(child);
                                    }
                                    else if (child.nodeType === 1) { // 1 is for element nodes
                                        removeComments(child);
                                    }
                                }
                            };
                            removeComments(doc.documentElement);
                        }
                        // Get the processed HTML
                        let result = doc.documentElement.outerHTML;
                        // Minify if requested
                        if (minify) {
                            // Simple minification: remove extra whitespace
                            result = result.replace(/>\s+</g, '><').trim();
                        }
                        return result;
                    }, {
                        html: htmlContent,
                        removeScripts: shouldRemoveScripts,
                        removeComments: shouldRemoveComments,
                        removeStyles: shouldRemoveStyles,
                        removeMeta: shouldRemoveMeta,
                        minify
                    });
                }
                // Truncate logic
                const maxLength = typeof args.maxLength === 'number' ? args.maxLength : 20000;
                let output = htmlContent;
                if (output.length > maxLength) {
                    output = output.slice(0, maxLength) + '\n<!-- Output truncated due to size limits -->';
                }
                return createSuccessResponse(`HTML content:\n${output}`);
            }
            catch (error) {
                return createErrorResponse(`Failed to get visible HTML content: ${error.message}`);
            }
        });
    }

    /**
     * Get minimal HTML containing only interactive elements and their selectors
     */
    async getMinimalHtml(page, args) {
        try {
            const minimalData = await page.evaluate(() => {
                // Get all interactive elements that the LLM might want to interact with
                const interactiveSelectors = [
                    'button', 'input', 'select', 'textarea', 'a[href]', 'img',
                    '[onclick]', '[role="button"]', '[role="link"]', '[role="tab"]',
                    '.btn', '.button', '.link', '.nav-item', '.menu-item',
                    'form', 'label', '[contenteditable]', '[tabindex]',
                    '[data-testid]', '[aria-label]'
                ];
                
                const elements = [];
                const seenElements = new Set(); // Avoid duplicates
                
                interactiveSelectors.forEach(selector => {
                    try {
                        const found = document.querySelectorAll(selector);
                        found.forEach((el) => {
                            // Skip if we've already processed this element
                            if (seenElements.has(el)) return;
                            seenElements.add(el);
                            
                            // Skip hidden elements
                            const style = window.getComputedStyle(el);
                            if (style.display === 'none' || style.visibility === 'hidden') return;
                            
                            // Generate multiple selector options for the element
                            const selectors = [];
                            
                            // ID selector (highest priority)
                            if (el.id) selectors.push(`#${el.id}`);
                            
                            // Data-testid selector (very reliable)
                            if (el.getAttribute('data-testid')) {
                                selectors.push(`[data-testid="${el.getAttribute('data-testid')}"]`);
                            }
                            
                            // Class selector
                            if (el.className && typeof el.className === 'string') {
                                const classes = el.className.trim().split(/\s+/).filter(c => c.length > 0 && !c.includes(' '));
                                if (classes.length > 0) {
                                    // Add individual classes and combined classes
                                    selectors.push(`.${classes[0]}`);
                                    if (classes.length <= 3) {
                                        selectors.push(`.${classes.join('.')}`);
                                    }
                                }
                            }
                            
                            // Attribute selectors
                            if (el.name) selectors.push(`[name="${el.name}"]`);
                            if (el.type) selectors.push(`[type="${el.type}"]`);
                            if (el.role) selectors.push(`[role="${el.role}"]`);
                            if (el.getAttribute('aria-label')) {
                                selectors.push(`[aria-label="${el.getAttribute('aria-label')}"]`);
                            }
                            
                            // Text-based selector for buttons/links
                            const text = el.textContent?.trim();
                            if (text && text.length > 0 && text.length < 50) {
                                // Use text selector for unique text
                                const textSelector = `text="${text}"`;
                                selectors.push(textSelector);
                            }
                            
                            // Fallback: tag with position
                            const tagName = el.tagName.toLowerCase();
                            selectors.push(`${tagName}`);
                            
                            elements.push({
                                tag: el.tagName.toLowerCase(),
                                type: el.type || null,
                                text: text?.substring(0, 100) || null,
                                selectors: selectors.slice(0, 5), // Limit to 5 best selectors
                                attributes: {
                                    id: el.id || null,
                                    class: el.className || null,
                                    name: el.name || null,
                                    placeholder: el.placeholder || null,
                                    value: el.type === 'password' ? '[hidden]' : (el.value || null),
                                    'aria-label': el.getAttribute('aria-label') || null,
                                    'data-testid': el.getAttribute('data-testid') || null,
                                    src: el.tagName.toLowerCase() === 'img' ? el.src : null,
                                    alt: el.tagName.toLowerCase() === 'img' ? el.alt : null
                                }
                            });
                        });
                    } catch (e) {
                        // Skip selectors that cause errors
                    }
                });
                
                return {
                    url: window.location.href,
                    title: document.title,
                    elements: elements.slice(0, 100) // Limit to 100 most relevant elements
                };
            });
            
            // Format the minimal HTML output
            let output = `🔍 MINIMAL PAGE ANALYSIS FOR ELEMENT SELECTION\n`;
            output += `📄 Page: ${minimalData.title}\n`;
            output += `🌐 URL: ${minimalData.url}\n`;
            output += `🎯 Interactive Elements Found: ${minimalData.elements.length}\n\n`;
            
            // Group elements by type for better organization
            const elementsByType = {};
            minimalData.elements.forEach(el => {
                const key = el.type ? `${el.tag}[${el.type}]` : el.tag;
                if (!elementsByType[key]) elementsByType[key] = [];
                elementsByType[key].push(el);
            });
            
            // Output organized by element type
            Object.entries(elementsByType).forEach(([type, elements]) => {
                output += `📋 ${type.toUpperCase()} (${elements.length}):\n`;
                elements.slice(0, 30).forEach((el, index) => {
                    const primarySelector = el.selectors[0];
                    const description = el.text ? `"${el.text.substring(0, 40)}..."` : 
                                      el.attributes.placeholder ? `placeholder: "${el.attributes.placeholder}"` :
                                      el.attributes['aria-label'] ? `aria-label: "${el.attributes['aria-label']}"` :
                                      el.attributes.alt ? `alt: "${el.attributes.alt}"` :
                                      el.attributes.src ? `src: "${el.attributes.src.substring(0, 50)}..."` :
                                      'no text';
                    
                    output += `  ${index + 1}. ${primarySelector}\n`;
                    output += `     Text: ${description}\n`;
                    if (el.selectors.length > 1) {
                        output += `     Alt selectors: ${el.selectors.slice(1, 3).join(', ')}\n`;
                    }
                    output += `\n`;
                });
                if (elements.length > 30) {
                    output += `     ... and ${elements.length - 30} more ${type} elements\n\n`;
                }
            });
            
            // Truncate if too long
            const maxLength = typeof args.maxLength === 'number' ? args.maxLength : 10000;
            if (output.length > maxLength) {
                output = output.slice(0, maxLength) + '\n<!-- Output truncated due to size limits -->';
            }
            
            return createSuccessResponse(output);
            
        } catch (error) {
            return createErrorResponse(`Failed to get minimal HTML: ${error.message}`);
        }
    }
}
