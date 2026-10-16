#!/bin/sh
# Adds Tax Estimator to your desktop's app launcher.
# The app runs from this folder, so re-run this script if you move it.
DIR="$(cd "$(dirname "$0")" && pwd)"

if ! python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null; then
    echo "Python GTK 3 bindings not found. Install them first, e.g.:"
    echo "  Debian/Ubuntu: sudo apt install python3-gi gir1.2-gtk-3.0"
    echo "  Fedora:        sudo dnf install python3-gobject gtk3"
    echo "  Arch:          sudo pacman -S python-gobject gtk3"
    exit 1
fi

mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/tax-estimator.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Tax Estimator
Comment=Estimate UK income tax and NI on self-employed profits
Exec=python3 "$DIR/tax_estimator.py"
Icon=accessories-calculator
Terminal=false
StartupWMClass=tax-estimator
Categories=Office;Finance;
DESKTOP
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null
echo "Installed. Search for 'Tax Estimator' in your app launcher."
