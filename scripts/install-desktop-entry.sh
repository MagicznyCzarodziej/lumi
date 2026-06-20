#!/usr/bin/env bash
# Install ~/.local/share/applications/lumi.desktop for the current checkout.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCHER="$ROOT/scripts/lumi-launch.sh"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/lumi.desktop"

if [[ ! -f "$LAUNCHER" ]]; then
    echo "Missing launcher: $LAUNCHER" >&2
    exit 1
fi

chmod +x "$LAUNCHER"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Lumi
GenericName=Video Library
Comment=Browse an SMB video library
Exec=${LAUNCHER}
Path=${ROOT}
Terminal=false
Categories=Video;Player;
StartupWMClass=lumi
EOF

chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

if command -v gio >/dev/null 2>&1; then
    gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
fi

echo "Installed $DESKTOP_FILE"
echo "Search for 'Lumi' in your app menu, or log out and back in if it does not appear."
