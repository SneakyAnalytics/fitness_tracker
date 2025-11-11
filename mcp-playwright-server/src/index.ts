#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { chromium, Browser, Page } from "playwright";

/**
 * MCP Server for Playwright Browser Automation
 *
 * Provides tools for automated web interactions, specifically designed
 * for TrainingPeaks data synchronization but usable for general automation.
 */

interface BrowserSession {
  browser: Browser;
  page: Page;
}

let browserSession: BrowserSession | null = null;

// Tool definitions
const TOOLS: Tool[] = [
  {
    name: "playwright_navigate",
    description:
      "Navigate to a URL in the browser. Opens a new browser if not already open.",
    inputSchema: {
      type: "object",
      properties: {
        url: {
          type: "string",
          description: "The URL to navigate to",
        },
        waitUntil: {
          type: "string",
          enum: ["load", "domcontentloaded", "networkidle"],
          description: "When to consider navigation successful (default: load)",
          default: "load",
        },
      },
      required: ["url"],
    },
  },
  {
    name: "playwright_click",
    description: "Click an element on the page using a CSS selector",
    inputSchema: {
      type: "object",
      properties: {
        selector: {
          type: "string",
          description: "CSS selector for the element to click",
        },
        timeout: {
          type: "number",
          description:
            "Maximum time to wait for element in milliseconds (default: 30000)",
          default: 30000,
        },
      },
      required: ["selector"],
    },
  },
  {
    name: "playwright_fill",
    description: "Fill a form field with text",
    inputSchema: {
      type: "object",
      properties: {
        selector: {
          type: "string",
          description: "CSS selector for the input field",
        },
        value: {
          type: "string",
          description: "Text to fill into the field",
        },
        timeout: {
          type: "number",
          description:
            "Maximum time to wait for element in milliseconds (default: 30000)",
          default: 30000,
        },
      },
      required: ["selector", "value"],
    },
  },
  {
    name: "playwright_get_text",
    description: "Extract text content from elements matching a selector",
    inputSchema: {
      type: "object",
      properties: {
        selector: {
          type: "string",
          description: "CSS selector for the element(s)",
        },
        all: {
          type: "boolean",
          description:
            "Get text from all matching elements (default: false, gets first match)",
          default: false,
        },
      },
      required: ["selector"],
    },
  },
  {
    name: "playwright_screenshot",
    description: "Take a screenshot of the current page",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description:
            "Path where to save the screenshot (optional, returns base64 if omitted)",
        },
        fullPage: {
          type: "boolean",
          description: "Capture the full scrollable page (default: false)",
          default: false,
        },
      },
      required: [],
    },
  },
  {
    name: "playwright_wait_for_selector",
    description: "Wait for an element to appear on the page",
    inputSchema: {
      type: "object",
      properties: {
        selector: {
          type: "string",
          description: "CSS selector to wait for",
        },
        timeout: {
          type: "number",
          description: "Maximum time to wait in milliseconds (default: 30000)",
          default: 30000,
        },
        state: {
          type: "string",
          enum: ["attached", "detached", "visible", "hidden"],
          description:
            "Wait for element to reach this state (default: visible)",
          default: "visible",
        },
      },
      required: ["selector"],
    },
  },
  {
    name: "playwright_download",
    description:
      "Download a file by clicking a download link and wait for download to complete",
    inputSchema: {
      type: "object",
      properties: {
        selector: {
          type: "string",
          description: "CSS selector for the download link/button",
        },
        downloadPath: {
          type: "string",
          description: "Directory path where the file should be saved",
        },
        timeout: {
          type: "number",
          description:
            "Maximum time to wait for download in milliseconds (default: 60000)",
          default: 60000,
        },
      },
      required: ["selector", "downloadPath"],
    },
  },
  {
    name: "playwright_close",
    description: "Close the browser session",
    inputSchema: {
      type: "object",
      properties: {},
      required: [],
    },
  },
  {
    name: "playwright_get_current_url",
    description: "Get the current page URL",
    inputSchema: {
      type: "object",
      properties: {},
      required: [],
    },
  },
  {
    name: "playwright_evaluate",
    description: "Execute JavaScript code in the browser context",
    inputSchema: {
      type: "object",
      properties: {
        script: {
          type: "string",
          description: "JavaScript code to execute",
        },
      },
      required: ["script"],
    },
  },
];

/**
 * Ensure browser is initialized
 */
async function ensureBrowser(): Promise<BrowserSession> {
  if (!browserSession) {
    const browser = await chromium.launch({ headless: false }); // Use headless: true for production
    const page = await browser.newPage();
    browserSession = { browser, page };
  }
  return browserSession;
}

/**
 * Main server setup
 */
const server = new Server(
  {
    name: "mcp-playwright-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;

  try {
    switch (name) {
      case "playwright_navigate": {
        const { browser, page } = await ensureBrowser();
        const url = args.url as string;
        const waitUntil =
          (args.waitUntil as "load" | "domcontentloaded" | "networkidle") ||
          "load";

        await page.goto(url, { waitUntil });

        return {
          content: [
            {
              type: "text",
              text: `Successfully navigated to ${url}`,
            },
          ],
        };
      }

      case "playwright_click": {
        const { page } = await ensureBrowser();
        const selector = args.selector as string;
        const timeout = (args.timeout as number) || 30000;

        await page.click(selector, { timeout });

        return {
          content: [
            {
              type: "text",
              text: `Successfully clicked element: ${selector}`,
            },
          ],
        };
      }

      case "playwright_fill": {
        const { page } = await ensureBrowser();
        const selector = args.selector as string;
        const value = args.value as string;
        const timeout = (args.timeout as number) || 30000;

        await page.fill(selector, value, { timeout });

        return {
          content: [
            {
              type: "text",
              text: `Successfully filled ${selector} with value`,
            },
          ],
        };
      }

      case "playwright_get_text": {
        const { page } = await ensureBrowser();
        const selector = args.selector as string;
        const all = args.all as boolean;

        let text: string | string[];
        if (all) {
          text = await page.$$eval(selector, (elements) =>
            elements.map((el) => el.textContent?.trim() || "")
          );
        } else {
          text = (await page.textContent(selector))?.trim() || "";
        }

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ selector, text }, null, 2),
            },
          ],
        };
      }

      case "playwright_screenshot": {
        const { page } = await ensureBrowser();
        const path = args.path as string | undefined;
        const fullPage = args.fullPage as boolean;

        const screenshot = await page.screenshot({
          path,
          fullPage,
          type: path ? undefined : "png",
        });

        if (path) {
          return {
            content: [
              {
                type: "text",
                text: `Screenshot saved to ${path}`,
              },
            ],
          };
        } else {
          return {
            content: [
              {
                type: "text",
                text: `Screenshot captured (base64): ${screenshot
                  .toString("base64")
                  .substring(0, 100)}...`,
              },
            ],
          };
        }
      }

      case "playwright_wait_for_selector": {
        const { page } = await ensureBrowser();
        const selector = args.selector as string;
        const timeout = (args.timeout as number) || 30000;
        const state =
          (args.state as "attached" | "detached" | "visible" | "hidden") ||
          "visible";

        await page.waitForSelector(selector, { timeout, state });

        return {
          content: [
            {
              type: "text",
              text: `Element ${selector} reached state: ${state}`,
            },
          ],
        };
      }

      case "playwright_download": {
        const { page } = await ensureBrowser();
        const selector = args.selector as string;
        const downloadPath = args.downloadPath as string;
        const timeout = (args.timeout as number) || 60000;

        // Set download path
        const context = page.context();

        // Wait for download to start
        const [download] = await Promise.all([
          page.waitForEvent("download", { timeout }),
          page.click(selector),
        ]);

        // Save to specified path
        const suggestedFilename = download.suggestedFilename();
        const savePath = `${downloadPath}/${suggestedFilename}`;
        await download.saveAs(savePath);

        return {
          content: [
            {
              type: "text",
              text: `File downloaded successfully: ${savePath}`,
            },
          ],
        };
      }

      case "playwright_get_current_url": {
        const { page } = await ensureBrowser();
        const url = page.url();

        return {
          content: [
            {
              type: "text",
              text: url,
            },
          ],
        };
      }

      case "playwright_evaluate": {
        const { page } = await ensureBrowser();
        const script = args.script as string;

        const result = await page.evaluate(script);

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "playwright_close": {
        if (browserSession) {
          await browserSession.browser.close();
          browserSession = null;
        }

        return {
          content: [
            {
              type: "text",
              text: "Browser closed successfully",
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: "text",
              text: `Unknown tool: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error executing ${name}: ${
            error instanceof Error ? error.message : String(error)
          }`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Start the server
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Cleanup on exit
  process.on("SIGINT", async () => {
    if (browserSession) {
      await browserSession.browser.close();
    }
    process.exit(0);
  });
}

main();
