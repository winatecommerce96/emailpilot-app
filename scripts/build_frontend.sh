#!/bin/bash

# This script builds the frontend assets for the EmailPilot application.

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the source and destination directories.
SRC_DIR="frontend/public"
DEST_DIR="dist"
ENTRYPOINT="$SRC_DIR/main.js"

# Create the destination directory if it doesn't exist.
mkdir -p "$DEST_DIR"

# Bundle the application using the main.js entrypoint.
./node_modules/.bin/esbuild "$ENTRYPOINT" --bundle --outfile="$DEST_DIR/app.js" --loader:.js=jsx

echo "Frontend build complete."