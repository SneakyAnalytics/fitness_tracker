# Beelink Access Guide - Tailscale Configuration

## Overview

The Beelink is a Windows mini-PC running development services accessible via Tailscale VPN mesh network. This provides secure, encrypted remote access without exposing services to the public internet.

## Network Configuration

**Tailscale Network:**

- **Beelink IP:** `100.117.194.8`
- **Mac Development Machine:** `100.111.4.32`
- **Network:** Private mesh VPN (no port forwarding required)

**Machine Details:**

- **OS:** Windows 11
- **User:** `rakej`
- **Docker:** Docker Desktop (WSL2 backend)
- **SSH:** OpenSSH server enabled

## Connecting to the Beelink

### SSH Access

```bash
# Basic connection
ssh rakej@100.117.194.8

# Run a single command
ssh rakej@100.117.194.8 "command here"

# Copy files to Beelink
scp localfile.txt rakej@100.117.194.8:C:/destination/path/

# Copy files from Beelink
scp rakej@100.117.194.8:C:/source/file.txt ./local/path/
```

**Note:** Windows paths use `C:/` format in SSH commands (forward slashes work better than backslashes).

### Accessing Services

Services running on the Beelink are accessible via Tailscale IP:

```bash
# Web services
http://100.117.194.8:8501  # Streamlit UI
http://100.117.194.8:8000  # FastAPI backend

# Docker containers
ssh rakej@100.117.194.8 "docker ps"
ssh rakej@100.117.194.8 "docker exec container-name command"
```

## Docker Environment

The Beelink runs applications in Docker containers:

```bash
# List running containers
ssh rakej@100.117.194.8 "docker ps"

# View container logs
ssh rakej@100.117.194.8 "docker logs container-name"

# Execute commands in containers
ssh rakej@100.117.194.8 "docker exec container-name python script.py"

# Restart containers
ssh rakej@100.117.194.8 "docker restart container-name"
```

**Current Containers:**

- `fitness-tracker-api` - FastAPI backend (port 8000)
- `fitness-tracker-ui` - Streamlit UI (port 8501)

## File Transfer Methods

### Method 1: SCP (Simple files)

```bash
# Upload single file
scp myfile.py rakej@100.117.194.8:C:/Users/rakej/project/

# Download single file
scp rakej@100.117.194.8:C:/Users/rakej/project/file.py ./
```

### Method 2: Tar + SCP (Multiple files)

```bash
# Upload directory
tar -czf archive.tar.gz my_directory/
scp archive.tar.gz rakej@100.117.194.8:C:/Users/rakej/
ssh rakej@100.117.194.8 "cd C:\\Users\\rakej && tar -xzf archive.tar.gz"

# Download directory
ssh rakej@100.117.194.8 "cd C:\\Users\\rakej\\project && tar -czf archive.tar.gz folder/"
scp rakej@100.117.194.8:C:/Users/rakej/project/archive.tar.gz ./
tar -xzf archive.tar.gz
```

### Method 3: Docker Copy (For containers)

```bash
# Copy file into running container
scp myfile.py rakej@100.117.194.8:myfile.py
ssh rakej@100.117.194.8 "docker cp myfile.py container-name:/app/path/"

# Copy from container to local
ssh rakej@100.117.194.8 "docker cp container-name:/app/path/file.txt ."
scp rakej@100.117.194.8:file.txt ./
```

## Common Workflows

### Deploy Application Updates

```bash
# 1. Copy updated files
scp src/app.py rakej@100.117.194.8:app.py

# 2. Update container
ssh rakej@100.117.194.8 "docker cp app.py container-name:/app/src/app.py"

# 3. Restart container
ssh rakej@100.117.194.8 "docker restart container-name"
```

### Check Application Status

```bash
# View running services
ssh rakej@100.117.194.8 "docker ps"

# Check container health
ssh rakej@100.117.194.8 "docker logs --tail 50 container-name"

# Test API endpoint
curl -s http://100.117.194.8:8000/health
```

### Database Operations

```bash
# Access SQLite database in container
ssh rakej@100.117.194.8 "docker exec container-name python -c \"import sqlite3; conn = sqlite3.connect('/app/data/database.db'); print(conn.execute('SELECT * FROM table LIMIT 5').fetchall())\""

# Backup database
ssh rakej@100.117.194.8 "docker cp container-name:/app/data/database.db ."
scp rakej@100.117.194.8:database.db ./backups/
```

## Important Notes

1. **No Password Authentication:** SSH uses key-based authentication (password prompt means keys not configured)

2. **Windows Path Format:** Use forward slashes in SSH commands: `C:/Users/rakej/` not `C:\Users\rakej\`

3. **WSL2 Integration:** Docker runs in WSL2, but containers are accessible from Windows host

4. **No Port Forwarding:** Tailscale handles all networking - services are only accessible within the VPN mesh

5. **Persistent Services:** Containers auto-restart via Docker Compose `restart: unless-stopped`

## Troubleshooting

### Can't connect via SSH

```bash
# Check Tailscale connection
tailscale status | grep 100.117.194.8

# Test basic connectivity
ping 100.117.194.8
```

### Docker not responding

```bash
# Check Docker status
ssh rakej@100.117.194.8 "docker info"

# Restart Docker Desktop (from Windows)
ssh rakej@100.117.194.8 "powershell -Command \"Restart-Service Docker\""
```

### Service not accessible

```bash
# Check if port is listening
ssh rakej@100.117.194.8 "netstat -an | findstr :8000"

# View container logs
ssh rakej@100.117.194.8 "docker logs container-name"
```

## Security Considerations

- **VPN Only:** All services are only accessible via Tailscale VPN (100.x.x.x addresses)
- **No Public Exposure:** No ports exposed to internet
- **Encrypted Traffic:** Tailscale uses WireGuard for encryption
- **Key-based SSH:** No password authentication allowed

## Project Locations

Current fitness tracker project:

- **Code:** `C:\Users\rakej\fitness_tracker`
- **Data:** Container volume `/app/data` (SQLite database, FIT files)
- **Shareable:** `C:\Users\rakej\fitness_tracker\shareable` (Zwift workouts)

## Additional Resources

- **Tailscale Status:** `tailscale status` (shows all devices on network)
- **Docker Compose:** `C:\Users\rakej\fitness_tracker\docker-compose.yml`
- **Container Logs:** `/var/log/` in containers or `docker logs`

---

**For Development:** Create your own directory under `C:\Users\rakej\` and use Docker containers for services. Follow the same patterns as the fitness tracker for deployment and access.
