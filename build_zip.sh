#!/bin/bash
# Builds installable zips for all multi-file plugins.
# Run from the repo root: ./build_zip.sh
# Uses 'zip' if available, otherwise falls back to PowerShell Compress-Archive (Windows).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/plugins"

build_zip() {
    local name="$1"
    rm -f "${name}.zip"
    if command -v zip &>/dev/null; then
        zip -r "${name}.zip" "${name}/" -x "${name}/__pycache__/*" "${name}/**/__pycache__/*"
    else
        powershell.exe -Command "Compress-Archive -Path '${name}' -DestinationPath '${name}.zip' -Force"
    fi
    echo "Built plugins/${name}.zip"
}

build_zip bk_arma_tools
build_zip bk_weight_gradient
build_zip bk_nla_automation
build_zip bk_weapon_rig_replacer
build_zip bk_fbx_exporter
build_zip bk_animation_export_profile

cd ..
