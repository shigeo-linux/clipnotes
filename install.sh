#!/bin/bash
set -e

APP_NAME="clipnotes"
INSTALL_DIR="/opt/${APP_NAME}"
DESKTOP_DIR="/usr/share/applications"

echo "=== Installing ${APP_NAME} ==="

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found."
    exit 1
fi

echo "Installing dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-requests python3-venv

echo "Copying application files..."
sudo mkdir -p "${INSTALL_DIR}"
sudo cp -r "$(dirname "$0")"/* "${INSTALL_DIR}/"
sudo chmod +x "${INSTALL_DIR}/clipnotes.py"

echo "Creating virtual environment..."
sudo python3 -m venv --system-site-packages "${INSTALL_DIR}/venv"
sudo "${INSTALL_DIR}/venv/bin/pip" install --quiet youtube-transcript-api pypdf

echo "Installing icon..."
sudo mkdir -p /usr/share/icons/hicolor/scalable/apps
sudo cp "${INSTALL_DIR}/clipnotes.svg" /usr/share/icons/hicolor/scalable/apps/clipnotes.svg
sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

echo "Installing desktop entry..."
sudo cp "${INSTALL_DIR}/clipnotes.desktop" "${DESKTOP_DIR}/"
sudo update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

echo "Creating launcher..."
sudo tee /usr/local/bin/clipnotes > /dev/null << 'EOF'
#!/bin/bash
exec /opt/clipnotes/venv/bin/python3 /opt/clipnotes/clipnotes.py "$@"
EOF
sudo chmod +x /usr/local/bin/clipnotes

echo "Creating config directory..."
mkdir -p "$HOME/.config/${APP_NAME}"

echo ""
echo "=== Installation complete! ==="
echo "Run: clipnotes"
echo "Or search for 'Clipnotes' in your application menu."
echo ""
echo "On first launch, open Settings (⚙) and enter your OpenRouter API key."
