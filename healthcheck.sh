#!/bin/bash
# Health check script to verify permissions and directory access
# Run from host: bash healthcheck.sh
# Run from container: docker-compose exec mesh-monitor bash healthcheck.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Meshtastic Mesh Monitor Health Check ==="
echo ""

# Track overall health
HEALTH_OK=true

# Function to check directory/file
check_path() {
    local path=$1
    local description=$2
    local required=${3:-true}
    
    if [ -e "$path" ]; then
        if [ -w "$path" ] 2>/dev/null; then
            echo -e "${GREEN}✓${NC} $description: $path (writable)"
        elif [ -r "$path" ] 2>/dev/null; then
            echo -e "${YELLOW}⚠${NC} $description: $path (readable, not writable)"
        else
            echo -e "${RED}✗${NC} $description: $path (exists but not accessible)"
            HEALTH_OK=false
        fi
    else
        if [ "$required" = true ]; then
            echo -e "${RED}✗${NC} $description: $path (MISSING)"
            HEALTH_OK=false
        else
            echo -e "${YELLOW}⚠${NC} $description: $path (not found - optional)"
        fi
    fi
}

# Check critical directories
echo "Checking directories..."
check_path "/app/logs" "Logs directory" true
check_path "/app/config_files" "Config directory" true
check_path "/data" "Data volume (IPC)" true
echo ""

# Check key config files
echo "Checking config files..."
check_path "/app/config_files/config.json" "Config JSON" true
check_path "/app/config_files/gemini_config.json" "Gemini config" false
echo ""

# Test write permissions with actual file operations
echo "Testing write permissions..."
TEST_FILE="/app/logs/healthcheck_test_$(date +%s).tmp"
if touch "$TEST_FILE" 2>/dev/null; then
    if rm "$TEST_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Can create and delete files in /app/logs"
    else
        echo -e "${RED}✗${NC} Cannot delete test file in /app/logs"
        HEALTH_OK=false
    fi
else
    echo -e "${RED}✗${NC} Cannot write to /app/logs"
    HEALTH_OK=false
fi

TEST_FILE="/data/healthcheck_test_$(date +%s).tmp"
if touch "$TEST_FILE" 2>/dev/null; then
    if rm "$TEST_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Can create and delete files in /data"
    else
        echo -e "${RED}✗${NC} Cannot delete test file in /data"
        HEALTH_OK=false
    fi
else
    echo -e "${RED}✗${NC} Cannot write to /data"
    HEALTH_OK=false
fi
echo ""

# Check user/privileges
echo "Checking user privileges..."
CURRENT_USER=$(id -u -n 2>/dev/null || echo "unknown")
echo "Current user: $CURRENT_USER (UID: $(id -u 2>/dev/null || echo 'N/A'))"
echo ""

# Final result
echo "=== Health Check Result ==="
if [ "$HEALTH_OK" = true ]; then
    echo -e "${GREEN}✓ All checks passed${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    exit 1
fi
