#!/usr/bin/env bash
set -euo pipefail

REPO_RAW_BASE="${REPO_RAW_BASE:-https://raw.githubusercontent.com/blamevlan/blamevlan/main}"
INSTALL_PATH="${INSTALL_PATH:-/usr/local/bin/carekit}"
TMP_FILE="$(mktemp)"

cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

echo "[INFO] Downloading ${REPO_RAW_BASE}/carekit.py"
curl -fsSL "${REPO_RAW_BASE}/carekit.py" -o "$TMP_FILE"

if [[ ! -s "$TMP_FILE" ]]; then
  echo "[ERROR] Download failed or file is empty"
  exit 1
fi

if [[ "$INSTALL_PATH" == /usr/* || "$INSTALL_PATH" == /opt/* ]]; then
  if [[ $EUID -ne 0 ]]; then
    if command -v sudo >/dev/null 2>&1; then
      sudo install -m 0755 "$TMP_FILE" "$INSTALL_PATH"
    else
      echo "[ERROR] Root privileges required (sudo not found)"
      exit 1
    fi
  else
    install -m 0755 "$TMP_FILE" "$INSTALL_PATH"
  fi
else
  install -m 0755 "$TMP_FILE" "$INSTALL_PATH"
fi

echo "[OK] Installed: $INSTALL_PATH"
echo "[OK] Try: carekit --help"
