#!/bin/bash
# Sync fitness_tracker to Beelink via Tailscale
# Usage: ./sync_to_beelink.sh [beelink-tailscale-ip]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Fitness Tracker Sync to Beelink ===${NC}\n"

# Get Beelink IP from argument or prompt
if [ -z "$1" ]; then
    echo -e "${YELLOW}Enter Beelink Tailscale IP (check Windows setup output):${NC}"
    read BEELINK_IP
else
    BEELINK_IP=$1
fi

echo -e "${CYAN}Target: rakej@${BEELINK_IP}${NC}\n"

# Test connection first
echo -e "${YELLOW}[1/4] Testing connection...${NC}"
if ssh -o ConnectTimeout=5 -o BatchMode=yes rakej@${BEELINK_IP} "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✓ Connection established${NC}\n"
else
    echo -e "\nConnection failed. Make sure:"
    echo "  1. Beelink setup script has been run"
    echo "  2. Tailscale is running on both devices"
    echo "  3. IP address is correct"
    exit 1
fi

# Create directory on Beelink
echo -e "${YELLOW}[2/4] Creating directory on Beelink...${NC}"
ssh rakej@${BEELINK_IP} "New-Item -ItemType Directory -Path C:\Users\rakej\fitness_tracker -Force" 2>/dev/null || true
echo -e "${GREEN}✓ Directory ready${NC}\n"

# Sync files (excluding large/temp files)
echo -e "${YELLOW}[3/4] Syncing files...${NC}"
rsync -avz --progress \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '.env' \
    --exclude 'logs/*' \
    --exclude 'data/*.backup' \
    --exclude 'data/*.bak*' \
    --exclude 'archive/' \
    /Users/jacobrobinson/fitness_tracker/ \
    rakej@${BEELINK_IP}:/c/Users/rakej/fitness_tracker/

echo -e "\n${GREEN}✓ Files synced${NC}\n"

# Copy .env separately with confirmation
echo -e "${YELLOW}[4/4] Copying sensitive files...${NC}"
if [ -f /Users/jacobrobinson/fitness_tracker/.env ]; then
    echo "Copy .env file? (contains API keys) [y/N]"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        scp /Users/jacobrobinson/fitness_tracker/.env rakej@${BEELINK_IP}:/c/Users/rakej/fitness_tracker/.env
        echo -e "${GREEN}✓ .env copied${NC}"
    fi
fi

echo -e "\n${GREEN}=== Sync Complete ===${NC}"
echo -e "\nNext steps on Beelink:"
echo -e "  ${CYAN}1. Install Docker Desktop: https://www.docker.com/products/docker-desktop/${NC}"
echo -e "  ${CYAN}2. Install Python: choco install python${NC}"
echo -e "  ${CYAN}3. Run: cd C:\\Users\\rakej\\fitness_tracker${NC}"
echo -e "  ${CYAN}4. Run: docker compose up -d${NC}\n"

# Save IP for future use
echo "$BEELINK_IP" > /Users/jacobrobinson/fitness_tracker/.beelink_ip
