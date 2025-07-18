import { BrowserToolBase } from './base.js';
import { createSuccessResponse, createErrorResponse } from '../common/types.js';
import { setGlobalPage } from '../../toolHandler.js';
/**
 * Get minimal HTML for element selection - only interactive elements and their selectors
 */
async function getMinimalHtmlForSelection(page) {
    try {
        const minimalHtml = await page.evaluate(() => {
            // Get all interactive elements that the LLM might want to click/fill
            const interactiveSelectors = [
                'button', 'input', 'select', 'textarea', 'a[href]', 
                '[onclick]', '[role="button"]', '[role="link"]', '[role="tab"]',
                '.btn', '.button', '.link', '.nav-item', '.menu-item',
                'form', 'label', '[contenteditable]', '[tabindex]'
            ];
            
            const elements = [];
            
            interactiveSelectors.forEach(selector => {
                try {
                    const found = document.querySelectorAll(selector);
                    found.forEach((el, index) => {
                        // Skip hidden elements
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden') return;
                        
                        // Generate multiple selector options for the element
                        const selectors = [];
                        
                        // ID selector (highest priority)
                        if (el.id) selectors.push(`#${el.id}`);
                        
                        // Class selector
                        if (el.className && typeof el.className === 'string') {
                            const classes = el.className.trim().split(/\s+/).filter(c => c.length > 0);
                            if (classes.length > 0) {
                                selectors.push(`.${classes.join('.')}`);
                            }
                        }
                        
                        // Attribute selectors
                        if (el.name) selectors.push(`[name="${el.name}"]`);
                        if (el.type) selectors.push(`[type="${el.type}"]`);
                        if (el.role) selectors.push(`[role="${el.role}"]`);
                        
                        // Text-based selector for buttons/links
                        const text = el.textContent?.trim();
                        if (text && text.length < 50) {
                            selectors.push(`text="${text}"`);
                        }
                        
                        // Fallback: tag with index
                        const tagName = el.tagName.toLowerCase();
                        const sameTagElements = document.querySelectorAll(tagName);
                        const elementIndex = Array.from(sameTagElements).indexOf(el);
                        selectors.push(`${tagName}:nth-of-type(${elementIndex + 1})`);
                        
                        elements.push({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || null,
                            text: text?.substring(0, 100) || null,
                            selectors: selectors,
                            attributes: {
                                id: el.id || null,
                                class: el.className || null,
                                name: el.name || null,
                                placeholder: el.placeholder || null,
                                value: el.value || null
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
                elements: elements.slice(0, 50) // Limit to 50 most relevant elements
            };
        });
        
        return minimalHtml;
    } catch (error) {
        console.error('Error getting minimal HTML:', error);
        return null;
    }
}
/**
 * Tool for clicking elements on the page - Enhanced with Selenium-style simplicity
 */
export class ClickTool extends BrowserToolBase {
    /**
     * Execute the click tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            // Store current URL to detect navigation
            const currentUrl = page.url();
            
            // Handle multiple elements by selecting the first one (previous behavior)
            let element;
            try {
                element = page.locator(args.selector);
                // Check if multiple elements exist
                const count = await element.count();
                if (count > 1) {
                    console.log(`⚠️ Selector '${args.selector}' matches ${count} elements, using first one`);
                    element = page.locator(args.selector).first();
                } else if (count === 0) {
                    throw new Error(`No elements found for selector: ${args.selector}`);
                }
            } catch (error) {
                throw new Error(`Failed to locate element with selector '${args.selector}': ${error.message}`);
            }
            
            // Selenium-style scroll into view and click approach
            await element.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500); // Simple 0.5 second delay like Selenium
            await element.click();
            
            // Wait a bit to see if navigation occurs - Selenium pattern
            await page.waitForTimeout(1000);
            
            // Check if navigation occurred
            const newUrl = page.url();
            const navigationOccurred = currentUrl !== newUrl;
            
            let response = {
                success: true,
                message: `Clicked element: ${args.selector}`,
                navigationDetected: navigationOccurred
            };
            
            // If navigation occurred, get minimal HTML for element selection
            if (navigationOccurred) {
                console.log(`🔄 Navigation detected: ${currentUrl} → ${newUrl}`);
                
                // Wait for page to stabilize after navigation
                try {
                    await page.waitForLoadState('domcontentloaded', { timeout: 5000 });
                } catch (e) {
                    // Continue even if timeout
                }
                
                // Get minimal HTML for element selection
                const minimalHtml = await getMinimalHtmlForSelection(page);
                
                if (minimalHtml) {
                    response.newPageContext = minimalHtml;
                    response.message += `\n\n🔄 Page navigation detected. New page loaded: ${newUrl}`;
                    response.message += `\n📄 Available interactive elements for selection:`;
                    
                    // Add summary of available elements
                    const elementSummary = minimalHtml.elements.slice(0, 30).map(el => {
                        const primarySelector = el.selectors[0];
                        const description = el.text ? `"${el.text.substring(0, 30)}..."` : `${el.tag}${el.type ? `[${el.type}]` : ''}`;
                        return `  • ${primarySelector} - ${description}`;
                    }).join('\n');
                    
                    response.message += `\n${elementSummary}`;
                    
                    if (minimalHtml.elements.length > 30) {
                        response.message += `\n  ... and ${minimalHtml.elements.length - 30} more elements`;
                    }
                } else {
                    response.message += `\n\n🔄 Page navigation detected but could not extract element information.`;
                }
            }
            if (navigationOccurred) {
                console.log(`🔄 Navigation detected: ${currentUrl} → ${newUrl}`);
                
                // Wait for page to stabilize after navigation
                try {
                    await page.waitForLoadState('domcontentloaded', { timeout: 5000 });
                } catch (e) {
                    // Continue even if timeout
                }
                
                response.message += `\n\n🔄 Page navigation detected. New page loaded: ${newUrl}`;
            }
            
            return createSuccessResponse(response.message);
        });
    }
}
/**
 * Tool for clicking a link and switching to the new tab
 */
export class ClickAndSwitchTabTool extends BrowserToolBase {
    /**
     * Execute the click and switch tab tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            // Listen for a new tab to open
            const [newPage] = await Promise.all([
                //context.browser.waitForEvent('page'), // Wait for a new page (tab) to open
                page.context().waitForEvent('page'), // Wait for a new page (tab) to open
                page.click(args.selector), // Click the link that opens the new tab
            ]);
            // Wait for the new page to load
            await newPage.waitForLoadState('domcontentloaded');
            // Switch control to the new tab
            setGlobalPage(newPage);
            //page= newPage; // Update the current page to the new tab
            //context.page = newPage;
            //context.page.bringToFront(); // Bring the new tab to the front
            return createSuccessResponse(`Clicked link and switched to new tab: ${newPage.url()}`);
            //return createSuccessResponse(`Clicked link and switched to new tab: ${context.page.url()}`);
        });
    }
}
/**
 * Tool for clicking elements inside iframes - Enhanced with Selenium-style natural timing
 */
export class IframeClickTool extends BrowserToolBase {
    /**
     * Execute the iframe click tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            // Add natural delay before iframe interaction (mimicking Selenium approach)
            await page.waitForTimeout(2000); // 2 second wait like Selenium
            
            const frame = page.frameLocator(args.iframeSelector);
            if (!frame) {
                return createErrorResponse(`Iframe not found: ${args.iframeSelector}`);
            }
            
            // Wait for iframe content to load - Selenium pattern
            await page.waitForTimeout(2000);
            
            // Scroll into view and click - mimicking Selenium's scrollIntoView pattern
            const element = frame.locator(args.selector);
            await element.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500); // Small delay after scroll
            await element.click();
            
            return createSuccessResponse(`Clicked element ${args.selector} inside iframe ${args.iframeSelector}`);
        });
    }
}
/**
 * Tool for filling elements inside iframes - Enhanced with Selenium-style natural timing
 */
export class IframeFillTool extends BrowserToolBase {
    /**
     * Execute the iframe fill tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            // Add natural delay before iframe interaction (mimicking Selenium approach)
            await page.waitForTimeout(2000); // 2 second wait like Selenium
            
            const frame = page.frameLocator(args.iframeSelector);
            if (!frame) {
                return createErrorResponse(`Iframe not found: ${args.iframeSelector}`);
            }
            
            // Wait for iframe content to load - Selenium pattern
            await page.waitForTimeout(2000);
            
            // Clear and fill with natural timing - mimicking Selenium's approach
            const element = frame.locator(args.selector);
            await element.scrollIntoViewIfNeeded();
            await page.waitForTimeout(500); // Small delay after scroll
            await element.clear();
            await page.waitForTimeout(500); // Delay between clear and fill
            await element.fill(args.value);
            
            return createSuccessResponse(`Filled element ${args.selector} inside iframe ${args.iframeSelector} with: ${args.value}`);
        });
    }
}
/**
 * Tool for filling form fields
 */
export class FillTool extends BrowserToolBase {
    /**
     * Execute the fill tool - Enhanced with Selenium-style simplicity
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            await page.waitForSelector(args.selector);
            
            // Handle multiple elements by selecting the first one (previous behavior)
            let element;
            try {
                element = page.locator(args.selector);
                // Check if multiple elements exist
                const count = await element.count();
                if (count > 1) {
                    console.log(`⚠️ Selector '${args.selector}' matches ${count} elements, using first one`);
                    element = page.locator(args.selector).first();
                } else if (count === 0) {
                    throw new Error(`No elements found for selector: ${args.selector}`);
                }
            } catch (error) {
                throw new Error(`Failed to locate element with selector '${args.selector}': ${error.message}`);
            }
            
            // Selenium-style simple approach - clear and send keys
            await element.clear();
            await page.waitForTimeout(500); // Simple delay like Selenium time.sleep(1)
            await element.fill(args.value);
            
            return createSuccessResponse(`Filled ${args.selector} with: ${args.value}`);
        });
    }
}
/**
 * Tool for selecting options from dropdown menus
 */
export class SelectTool extends BrowserToolBase {
    /**
     * Execute the select tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            await page.waitForSelector(args.selector);
            await page.selectOption(args.selector, args.value);
            return createSuccessResponse(`Selected ${args.selector} with: ${args.value}`);
        });
    }
}
/**
 * Tool for hovering over elements
 */
export class HoverTool extends BrowserToolBase {
    /**
     * Execute the hover tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            await page.waitForSelector(args.selector);
            await page.hover(args.selector);
            return createSuccessResponse(`Hovered ${args.selector}`);
        });
    }
}
/**
 * Tool for uploading files
 */
export class UploadFileTool extends BrowserToolBase {
    /**
     * Execute the upload file tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            await page.waitForSelector(args.selector);
            await page.setInputFiles(args.selector, args.filePath);
            return createSuccessResponse(`Uploaded file '${args.filePath}' to '${args.selector}'`);
        });
    }
}
/**
 * Tool for executing JavaScript in the browser
 */
export class EvaluateTool extends BrowserToolBase {
    /**
     * Execute the evaluate tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            const result = await page.evaluate(args.script);
            // Convert result to string for display
            let resultStr;
            try {
                resultStr = JSON.stringify(result, null, 2);
            }
            catch (error) {
                resultStr = String(result);
            }
            return createSuccessResponse([
                `Executed JavaScript:`,
                `${args.script}`,
                `Result:`,
                `${resultStr}`
            ]);
        });
    }
}
/**
 * Tool for dragging elements on the page
 */
export class DragTool extends BrowserToolBase {
    /**
     * Execute the drag tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            const sourceElement = await page.waitForSelector(args.sourceSelector);
            const targetElement = await page.waitForSelector(args.targetSelector);
            const sourceBound = await sourceElement.boundingBox();
            const targetBound = await targetElement.boundingBox();
            if (!sourceBound || !targetBound) {
                return createErrorResponse("Could not get element positions for drag operation");
            }
            await page.mouse.move(sourceBound.x + sourceBound.width / 2, sourceBound.y + sourceBound.height / 2);
            await page.mouse.down();
            await page.mouse.move(targetBound.x + targetBound.width / 2, targetBound.y + targetBound.height / 2);
            await page.mouse.up();
            return createSuccessResponse(`Dragged element from ${args.sourceSelector} to ${args.targetSelector}`);
        });
    }
}
/**
 * Tool for pressing keyboard keys
 */
export class PressKeyTool extends BrowserToolBase {
    /**
     * Execute the key press tool
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            if (args.selector) {
                await page.waitForSelector(args.selector);
                await page.focus(args.selector);
            }
            await page.keyboard.press(args.key);
            return createSuccessResponse(`Pressed key: ${args.key}`);
        });
    }
}
/**
 * Tool for switching browser tabs
 */
// export class SwitchTabTool extends BrowserToolBase {
//   /**
//    * Switch the tab to the specified index
//    */
//   async execute(args: any, context: ToolContext): Promise<ToolResponse> {
//     return this.safeExecute(context, async (page) => {
//       const tabs = await browser.page;      
//       // Validate the tab index
//       const tabIndex = Number(args.index);
//       if (isNaN(tabIndex)) {
//         return createErrorResponse(`Invalid tab index: ${args.index}. It must be a number.`);
//       }
//       if (tabIndex >= 0 && tabIndex < tabs.length) {
//         await tabs[tabIndex].bringToFront();
//         return createSuccessResponse(`Switched to tab with index ${tabIndex}`);
//       } else {
//         return createErrorResponse(
//           `Tab index out of range: ${tabIndex}. Available tabs: 0 to ${tabs.length - 1}.`
//         );
//       }
//     });
//   }
// }
/**
 * Tool for handling payment iframe interactions - Inspired by Selenium's payment portal success
 */
export class PaymentIframeTool extends BrowserToolBase {
    /**
     * Execute payment iframe interaction with Selenium-style approach
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            // Wait for payment page to load - like Selenium's time.sleep(3)
            await page.waitForTimeout(3000);
            
            // Switch to the payment iframe - Selenium pattern
            try {
                // Wait for iframe to be present (like Selenium's wait.until)
                await page.waitForSelector(args.iframeSelector, { timeout: 10000 });
                
                const iframe = page.frameLocator(args.iframeSelector);
                if (!iframe) {
                    return createErrorResponse(`Payment iframe not found: ${args.iframeSelector}`);
                }
                
                // Wait for iframe content to load - Selenium's time.sleep(2)
                await page.waitForTimeout(2000);
                
                // If action is provided, perform it
                if (args.action && args.selector) {
                    const element = iframe.locator(args.selector);
                    
                    switch (args.action) {
                        case 'click':
                            await element.scrollIntoViewIfNeeded();
                            await page.waitForTimeout(500); // Selenium-style delay
                            await element.click();
                            break;
                        case 'fill':
                            await element.clear();
                            await page.waitForTimeout(500);
                            await element.fill(args.value || '');
                            break;
                        case 'select':
                            await element.selectOption(args.value || '');
                            break;
                    }
                    
                    // Post-action delay like Selenium
                    await page.waitForTimeout(1000);
                }
                
                return createSuccessResponse(`Payment iframe interaction completed: ${args.action || 'iframe accessed'} on ${args.selector || 'N/A'}`);
                
            } catch (error) {
                return createErrorResponse(`Error in payment iframe interaction: ${error.message}`);
            }
        });
    }
}
/**
 * Tool for switching back to default content from iframe - Selenium pattern
 */
export class SwitchToDefaultContentTool extends BrowserToolBase {
    /**
     * Execute switch to default content (main page from iframe)
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            // The main page is always the default in Playwright
            // This tool exists for compatibility with Selenium-style workflows
            // where driver.switch_to.default_content() is used
            
            // Add natural delay like Selenium
            await page.waitForTimeout(2000);
            
            return createSuccessResponse("Switched to default content (main page)");
        });
    }
}
/**
 * Tool for adding Selenium-style explicit waits
 */
export class SeleniumWaitTool extends BrowserToolBase {
    /**
     * Execute Selenium-style wait operations
     */
    async execute(args, context) {
        return this.safeExecute(context, async (page) => {
            const { waitType, selector, timeout = 10000, text } = args;
            
            switch (waitType) {
                case 'element_to_be_clickable':
                    // Selenium's WebDriverWait(driver, 10).until(EC.element_to_be_clickable)
                    await page.waitForSelector(selector, { 
                        state: 'visible', 
                        timeout 
                    });
                    await page.waitForTimeout(500); // Extra stability delay
                    break;
                    
                case 'presence_of_element_located':
                    // Selenium's WebDriverWait(driver, 10).until(EC.presence_of_element_located)
                    await page.waitForSelector(selector, { timeout });
                    break;
                    
                case 'visibility_of_element_located':
                    // Selenium's WebDriverWait(driver, 10).until(EC.visibility_of_element_located)
                    await page.waitForSelector(selector, { 
                        state: 'visible', 
                        timeout 
                    });
                    break;
                    
                case 'text_to_be_present':
                    // Wait for specific text to appear
                    if (text) {
                        await page.waitForFunction(
                            (sel, txt) => {
                                const element = document.querySelector(sel);
                                return element && element.textContent.includes(txt);
                            },
                            [selector, text],
                            { timeout }
                        );
                    }
                    break;
                    
                default:
                    return createErrorResponse(`Unknown wait type: ${waitType}`);
            }
            
            return createSuccessResponse(`Selenium-style wait completed: ${waitType} for ${selector}`);
        });
    }
}
