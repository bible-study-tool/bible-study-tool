#!/usr/bin/env bash
# ==============================================================================
# Adventist Bible Study Tool — macOS First-Time Installer & Quarantine Resolver
#
# Removes Apple Gatekeeper internet quarantine flags (com.apple.quarantine)
# and installs the application into /Applications or ~/Applications.
# ==============================================================================

set -e

# Terminal colors
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BOLD}==============================================================${NC}"
echo -e "${BOLD} Adventist Bible Study — macOS Setup & Quarantine Resolver   ${NC}"
echo -e "${BOLD}==============================================================${NC}"
echo ""

APP_NAME="Adventist Bible Study.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_APP=""

# 1. Search for application bundle in common locations
echo -e "${BLUE}▶ Locating '${APP_NAME}'...${NC}"

# Check immediate script directory first (e.g. running from inside DMG or extracted bundle)
if [ -d "$SCRIPT_DIR/$APP_NAME" ]; then
    SOURCE_APP="$SCRIPT_DIR/$APP_NAME"
else
    # Check mounted DMGs before falling back to local installed directories
    for vol in /Volumes/*/"$APP_NAME"; do
        if [ -d "$vol" ]; then
            SOURCE_APP="$vol"
            break
        fi
    done
fi

# Fallback to user downloads or existing installation
if [ -z "$SOURCE_APP" ]; then
    if [ -d "$HOME/Downloads/$APP_NAME" ]; then
        SOURCE_APP="$HOME/Downloads/$APP_NAME"
    elif [ -d "/Applications/$APP_NAME" ]; then
        SOURCE_APP="/Applications/$APP_NAME"
    elif [ -d "$HOME/Applications/$APP_NAME" ]; then
        SOURCE_APP="$HOME/Applications/$APP_NAME"
    fi
fi

if [ -z "$SOURCE_APP" ] || [ ! -d "$SOURCE_APP" ]; then
    echo -e "${RED}✘ Error: Could not find '${APP_NAME}'.${NC}"
    echo "  Please place this script next to '${APP_NAME}', or mount the DMG disk image,"
    echo "  or move the app into your Downloads or Applications folder."
    echo ""
    if [ -t 0 ]; then
        read -n 1 -s -r -p "Press any key to exit..."
        echo ""
    fi
    exit 1
fi

echo -e "  Found app at: ${BOLD}${SOURCE_APP}${NC}"

# 2. Determine target destination directory
TARGET_DIR="/Applications"
if [ ! -w "$TARGET_DIR" ] || ([ -e "$TARGET_DIR/$APP_NAME" ] && [ ! -w "$TARGET_DIR/$APP_NAME" ]); then
    TARGET_DIR="$HOME/Applications"
fi
mkdir -p "$TARGET_DIR"
TARGET_APP="$TARGET_DIR/$APP_NAME"

# 3. Copy application to destination if not already there
if [ "$SOURCE_APP" != "$TARGET_APP" ]; then
    echo -e "${BLUE}▶ Installing '${APP_NAME}' to ${TARGET_DIR}...${NC}"
    rm -rf "$TARGET_APP" 2>/dev/null || true
    cp -a "$SOURCE_APP" "$TARGET_DIR/"
    echo -e "  ${GREEN}✔ Copied to ${TARGET_APP}${NC}"
else
    echo -e "  App is already installed in ${TARGET_DIR}."
fi

# 4. Remove Gatekeeper quarantine attribute
echo -e "${BLUE}▶ Clearing Apple Gatekeeper quarantine flags...${NC}"
xattr -cr "$TARGET_APP" 2>/dev/null || true
xattr -d -r com.apple.quarantine "$TARGET_APP" 2>/dev/null || true
echo -e "  ${GREEN}✔ Removed com.apple.quarantine extended attributes.${NC}"

# 5. Apply local ad-hoc code signature (required for Apple Silicon / M-series)
if command -v codesign &>/dev/null; then
    echo -e "${BLUE}▶ Applying local ad-hoc code signature...${NC}"
    if codesign --force --deep --sign - "$TARGET_APP" 2>/dev/null; then
        echo -e "  ${GREEN}✔ Applied ad-hoc code signature.${NC}"
    else
        echo -e "  ${YELLOW}⚠ Could not apply ad-hoc signature (non-critical).${NC}"
    fi
fi

# 6. Launch the application
echo ""
echo -e "${GREEN}${BOLD}✔ Setup complete!${NC}"
echo -e "${BLUE}▶ Launching Adventist Bible Study...${NC}"
open "$TARGET_APP" 2>/dev/null || true

echo ""
echo -e "${BOLD}You can now launch Adventist Bible Study anytime from:${NC}"
echo "  • Your Applications folder"
echo "  • Spotlight (Cmd + Space, type 'Adventist Bible Study')"
echo "  • Launchpad"
echo ""
echo "You may now close this terminal window."
sleep 3
