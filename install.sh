#!/usr/bin/env bash
set -euo pipefail

REPO="blamevlan/carekit"
RAW_URL="https://raw.githubusercontent.com/${REPO}/main/carekit.py"
INSTALL_DIR="${HOME}/.local/bin"
TARGET="${INSTALL_DIR}/carekit"

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found." >&2
    exit 1
fi

if ! python3 -c "from rich.console import Console" &>/dev/null; then
    echo "Installing dependency: python3-rich..."
    if command -v dnf &>/dev/null && sudo -n dnf install -y python3-rich &>/dev/null 2>&1; then
        echo "Installed via dnf."
    elif pip install --user --quiet rich; then
        echo "Installed via pip."
    else
        echo "Error: Could not install 'rich'. Please run:" >&2
        echo "  sudo dnf install python3-rich" >&2
        exit 1
    fi
fi

mkdir -p "$INSTALL_DIR"

echo "Downloading carekit..."
if command -v curl &>/dev/null; then
    curl -fsSL "$RAW_URL" -o "$TARGET"
elif command -v wget &>/dev/null; then
    wget -qO "$TARGET" "$RAW_URL"
else
    echo "Error: curl or wget required." >&2
    exit 1
fi

chmod +x "$TARGET"
echo "Installed: $TARGET"

if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
    echo ""
    echo "Note: Add ${INSTALL_DIR} to your PATH (e.g. in ~/.bashrc or ~/.zshrc):"
    echo "  export PATH=\"\${HOME}/.local/bin:\$PATH\""
fi
