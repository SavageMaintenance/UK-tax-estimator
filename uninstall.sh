#!/bin/sh
# Removes the launcher entry. Pass --purge to also delete saved settings.
rm -f "$HOME/.local/share/applications/tax-estimator.desktop"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null
if [ "$1" = "--purge" ]; then
    rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/tax-estimator"
    echo "Removed launcher and saved settings."
else
    echo "Removed launcher. Saved settings kept in ${XDG_CONFIG_HOME:-$HOME/.config}/tax-estimator (use --purge to delete)."
fi
