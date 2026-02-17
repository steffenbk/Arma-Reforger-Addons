#!/bin/bash
# Builds the installable zip for the BK Arma Tools multi-file plugin.
# Run from the repo root: ./build_zip.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

OUTPUT="bk_arma_tools.zip"

rm -f "$OUTPUT"

cd plugins
zip -r "../$OUTPUT" bk_arma_tools/ -x "bk_arma_tools/__pycache__/*" "bk_arma_tools/**/__pycache__/*"
cd ..

echo "Built $OUTPUT"
