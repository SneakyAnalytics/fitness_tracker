# MCP Playwright Server Configuration

## Installation Complete! ✅

The Playwright MCP server has been built and is ready to use.

## Next Step: Configure VS Code

You need to add this server to your VS Code MCP configuration.

### Option 1: Manual Configuration (Recommended)

1. Open VS Code Settings (JSON): `Cmd+Shift+P` → "Preferences: Open User Settings (JSON)"

2. Add this configuration to your `settings.json`:

```json
{
  // ... your existing settings ...
  
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

3. Reload VS Code window: `Cmd+Shift+P` → "Developer: Reload Window"

### Option 2: Quick Test (Command Line)

Test the server directly:

```bash
cd /Users/jacobrobinson/fitness_tracker/mcp-playwright-server
node build/index.js
```

The server will start and wait for MCP protocol messages via stdio.

## Testing the Integration

Once configured in VS Code, I'll be able to use tools like:
- `playwright_navigate` - Navigate to websites
- `playwright_fill` - Fill form fields  
- `playwright_click` - Click buttons
- `playwright_download` - Download files
- And more...

## Next: TrainingPeaks Integration

After you configure the MCP server in VS Code and reload, we'll build:

1. **Login script** - Automated TrainingPeaks authentication
2. **Data sync tool** - Download workouts/metrics CSV files
3. **Streamlit integration** - One-click sync button in your app

Would you like me to prepare the TrainingPeaks integration code while you configure VS Code?
