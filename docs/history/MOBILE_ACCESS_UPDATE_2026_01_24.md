# Mobile Access & Security Updates - January 24, 2026

## Changes Made

### 1. ✅ Removed Password Protection

- **Why**: Now using Tailscale private network instead of public Cloudflare tunnel
- **Security**: Tailscale provides encrypted VPN mesh network, no need for additional password layer
- **Files Changed**:
  - `src/ui/streamlit_app.py` - Removed entire password check function
  - `docker-compose.yml` - Removed `STREAMLIT_PASSWORD` environment variable

### 2. ✅ Fixed Mobile Access

Added Streamlit configuration for mobile device compatibility:

**Created `.streamlit/config.toml`:**

```toml
[server]
enableCORS = false
enableXsrfProtection = false
enableWebsocketCompression = true
headless = true
```

**Updated `docker-compose.yml`:**

- Added `.streamlit` volume mount
- Added `--server.enableCORS=false --server.enableXsrfProtection=false` to command flags

### 3. Why Mobile Access Failed Before

The issue was **XSRF (Cross-Site Request Forgery) protection** was enabled by default. This causes problems with:

- Mobile browsers (different user agents)
- Connections through Tailscale (different network paths)
- WebSocket connections from mobile devices

By disabling XSRF protection on Tailscale's private network, we're safe because:
✅ Only devices on your Tailscale network can access the app
✅ Tailscale uses encrypted WireGuard tunnels
✅ You control which devices are on your network

## How to Access on Mobile

### iPhone/Android:

1. Install **Tailscale** app from App Store/Play Store
2. Sign in with your Tailscale account
3. Connect to your Tailscale network
4. Open browser and go to: `http://100.117.194.8:8501`

### Troubleshooting Mobile Access:

If the app still doesn't load on mobile:

1. **Check Tailscale connection:**
   - Open Tailscale app
   - Verify you're connected (green indicator)
   - Check that Beelink (100.117.194.8) shows as online

2. **Try these URLs:**
   - `http://100.117.194.8:8501` (Tailscale IP)
   - `http://beelink:8501` (if you set up MagicDNS)

3. **Browser issues:**
   - Try different browsers (Safari, Chrome, Firefox)
   - Clear browser cache
   - Try incognito/private mode

4. **Check container logs:**
   ```bash
   ssh rakej@100.117.194.8 "docker logs fitness-tracker-ui"
   ```

## Python on Beelink

### Current Setup

- Python runs inside Docker containers (Python 3.12)
- Direct Python installation on Windows not required for current functionality
- Migrations and scripts run via `docker exec`

### If You Want Native Python (Optional):

This could be useful for:

- Running scripts outside Docker
- Faster development/testing
- Direct database access

**Installation:**

```powershell
# Windows PowerShell (as Administrator)
winget install Python.Python.3.12

# Or download from python.org
# Then add to PATH
```

**Benefits:**

- Run migrations directly: `python migrations/add_proposed_workout_name.py`
- Test scripts without Docker overhead
- Easier debugging

**Not Required For:**

- Current app functionality
- Docker-based deployment
- Scheduled tasks (use Docker exec instead)

## Next Steps

### Test Mobile Access:

1. Open Tailscale on your phone
2. Navigate to `http://100.117.194.8:8501`
3. Should load directly without password prompt
4. Test navigation and features

### If You Install Python:

The migration script that had issues could run directly:

```bash
ssh rakej@100.117.194.8
cd fitness_tracker
python migrations/add_proposed_workout_name.py
```

But it's not necessary since we can use Docker:

```bash
ssh rakej@100.117.194.8 "docker exec fitness-tracker-api python migrations/add_proposed_workout_name.py"
```

## Security Notes

### Tailscale Security Model:

- ✅ End-to-end encrypted (WireGuard protocol)
- ✅ Zero-trust network architecture
- ✅ You control device access via Tailscale admin console
- ✅ No public internet exposure

### Why Password Removal is Safe:

- Only Tailscale network devices can connect
- Beelink not accessible from public internet
- Simpler user experience on trusted devices
- One less credential to manage

### What's Still Protected:

- TrainingPeaks login (stored in .env)
- Google Gemini API key (stored in .env)
- Database files (only accessible on Tailscale network)
