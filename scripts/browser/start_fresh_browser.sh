#!/bin/bash
# L AIO - Fresh Browser Start Script
# This script kills any running Chromium instances and starts a fresh browser
# with the L extension loaded in a clean profile
# Note: This script only affects Chromium, not Google Chrome
#
# Usage:
#   bash start_fresh_browser.sh

set -e  # Exit on error

# ============================================
# CONFIGURATION
# ============================================

IOC_TEST_PORT=8080
DEBUG_PORT=9222

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHROME_EXTENSION_DIR="$SCRIPT_DIR/l_chrome_extension"

# Browser configuration (Chromium only)
if [ -d "/Applications/Chromium.app" ]; then
    CHROME_PATH="/Applications/Chromium.app/Contents/MacOS/Chromium"
    CHROME_NAME="Ungoogled Chromium"
else
    CHROME_PATH=""
    CHROME_NAME=""
fi

# ============================================
# COLORS
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ============================================
# HELPER FUNCTIONS
# ============================================

print_header() {
    echo -e "\n${CYAN}${BOLD}========================================${NC}"
    echo -e "${CYAN}${BOLD}$1${NC}"
    echo -e "${CYAN}${BOLD}========================================${NC}\n"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ============================================
# MAIN FUNCTIONS
# ============================================

kill_chromium_processes() {
    print_header "🛑 Stopping Chromium"

    # Kill Chromium processes only (not Google Chrome)
    local killed=0

    # Use more specific pattern to avoid matching Google Chrome
    # Match processes that contain "Chromium.app" in their path
    if pgrep -f "/Applications/Chromium.app" > /dev/null 2>&1; then
        print_status "Found running Chromium processes..."

        # Try to kill gracefully first
        pkill -f "/Applications/Chromium.app" 2>/dev/null || true
        sleep 2

        # Force kill if still running
        if pgrep -f "/Applications/Chromium.app" > /dev/null 2>&1; then
            print_warning "Force killing remaining Chromium processes..."
            pkill -9 -f "/Applications/Chromium.app" 2>/dev/null || true
            sleep 1
        fi

        killed=1
    fi

    if [ $killed -eq 1 ]; then
        print_success "Chromium processes stopped"
    else
        print_status "No Chromium processes were running"
    fi
}

cleanup_downloads() {
    print_header "🧹 Cleaning Up Downloads"

    local downloads_dir="$HOME/Downloads"
    local zip_file="$downloads_dir/l-extension.zip"
    local extension_folder="$downloads_dir/l-extension"

    local cleaned=0

    # Remove zip file if it exists
    if [ -f "$zip_file" ]; then
        print_status "Removing: $zip_file"
        rm -f "$zip_file" 2>/dev/null || true
        cleaned=1
    fi

    # Remove extension folder if it exists
    if [ -d "$extension_folder" ]; then
        print_status "Removing: $extension_folder"
        rm -rf "$extension_folder" 2>/dev/null || true
        cleaned=1
    fi

    if [ $cleaned -eq 1 ]; then
        print_success "Downloads cleaned up"
    else
        print_status "No extension files found in Downloads"
    fi
}

start_fresh_browser() {
    print_header "🌐 Starting Fresh Browser with Extension"

    # Check if Chromium is available
    if [ -z "$CHROME_PATH" ] || [ ! -f "$CHROME_PATH" ]; then
        print_error "Chromium not found!"
        print_warning "Please install Ungoogled Chromium"
        print_status "Expected location: /Applications/Chromium.app"
        exit 1
    fi

    # Check if extension is built
    if [ ! -d "$CHROME_EXTENSION_DIR/dist" ]; then
        print_error "Chrome extension not built!"
        print_warning "Extension directory not found: $CHROME_EXTENSION_DIR/dist"
        print_status "Please build the extension first:"
        print_status "  cd $CHROME_EXTENSION_DIR && npm run build"
        exit 1
    fi

    print_status "Using: $CHROME_NAME"

    # Generate unique timestamp for profile
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    USER_DATA_DIR="/tmp/chrome-l-$TIMESTAMP"

    print_status "Creating fresh Chromium profile: $USER_DATA_DIR"

    # Always load the test-selector-detection.html page by default
    # Use file:// URL so we don't need the HTTP server running
    TEST_HTML_FILE="$CHROME_EXTENSION_DIR/test-selector-detection.html"

    # Check if test file exists
    if [ ! -f "$TEST_HTML_FILE" ]; then
        print_error "Test file not found: $TEST_HTML_FILE"
        print_warning "Falling back to HTTP URL"
        TEST_URL="http://localhost:$IOC_TEST_PORT/test-selector-detection.html"
    else
        # Convert to file:// URL format (file:///absolute/path - note three slashes)
        TEST_URL="file://$TEST_HTML_FILE"
    fi

    print_status "Opening browser with extension loaded..."
    print_status "Target URL: $TEST_URL"

    # Open Chromium with extension loaded and remote debugging enabled
    "$CHROME_PATH" \
        --no-first-run \
        --no-default-browser-check \
        --disable-default-apps \
        --disable-popup-blocking \
        --remote-debugging-port=$DEBUG_PORT \
        --user-data-dir="$USER_DATA_DIR" \
        --load-extension="$CHROME_EXTENSION_DIR/dist" \
        "$TEST_URL" \
        > /tmp/l_chromium.log 2>&1 &

    local chromium_pid=$!

    print_success "$CHROME_NAME opened with extension loaded (PID: $chromium_pid)"
    print_status "Chromium profile: $USER_DATA_DIR"
    print_status "Extension location: $CHROME_EXTENSION_DIR/dist"
    print_status "Remote debugging port: $DEBUG_PORT"
    print_status "Test page: $TEST_URL"
    print_status "Log file: /tmp/l_chromium.log"
}

# ============================================
# MAIN EXECUTION
# ============================================

main() {
    kill_chromium_processes
    cleanup_downloads
    start_fresh_browser

    print_header "✅ Browser Started"
    echo -e "${GREEN}Fresh Chromium instance is running!${NC}"
    echo ""
    echo -e "${YELLOW}Note:${NC} The browser is running in the background."
    echo -e "${YELLOW}To stop:${NC} Close the browser window or run: pkill -f '/Applications/Chromium.app'"
    echo ""
}

# Run main function
main "$@"
