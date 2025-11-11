# Playwright MCP Server

Model Context Protocol server for Playwright browser automation. Designed specifically for automating TrainingPeaks data synchronization but usable for general web automation tasks.

## Features

- **Browser Navigation**: Navigate to URLs with configurable wait conditions
- **Form Interaction**: Click buttons, fill forms, extract text
- **Downloads**: Automate file downloads with path control
- **Screenshots**: Capture page screenshots for debugging
- **JavaScript Execution**: Run custom scripts in browser context
- **Session Management**: Persistent browser session across operations

## Installation

```bash
npm install
npm run build
```

## Configuration

Add this server to your MCP settings (e.g., VS Code settings.json):

```json
{
  "mcp": {
    "servers": {
      "playwright": {
        "command": "node",
        "args": [
          "/Users/jacobrobinson/fitness_tracker/mcp-playwright-server/build/index.js"
        ]
      }
    }
  }
}
```

## Available Tools

### playwright_navigate

Navigate to a URL

- `url` (required): URL to visit
- `waitUntil`: When to consider navigation complete (load/domcontentloaded/networkidle)

### playwright_click

Click an element

- `selector` (required): CSS selector
- `timeout`: Max wait time in ms

### playwright_fill

Fill a form field

- `selector` (required): CSS selector for input
- `value` (required): Text to enter
- `timeout`: Max wait time in ms

### playwright_get_text

Extract text content

- `selector` (required): CSS selector
- `all`: Get all matching elements (default: false)

### playwright_screenshot

Capture screenshot

- `path`: File path to save (optional)
- `fullPage`: Capture full scrollable page

### playwright_wait_for_selector

Wait for element to appear

- `selector` (required): CSS selector
- `timeout`: Max wait time
- `state`: Element state to wait for (visible/hidden/attached/detached)

### playwright_download

Download a file

- `selector` (required): CSS selector for download link
- `downloadPath` (required): Directory to save file
- `timeout`: Max wait time for download

### playwright_get_current_url

Get the current page URL

### playwright_evaluate

Execute JavaScript in browser

- `script` (required): JavaScript code to run

### playwright_close

Close the browser session

## Usage Example

Once configured, you can use these tools through your MCP client:

1. Navigate to TrainingPeaks login page
2. Fill username and password fields
3. Click login button
4. Wait for calendar page to load
5. Download workout data

## Development

- `npm run build`: Compile TypeScript
- `npm run watch`: Watch mode for development
- `npm start`: Run the server

## Notes

- Browser runs in non-headless mode by default for debugging
- Set `headless: true` in code for production use
- Browser session persists across tool calls until explicitly closed
