#!/bin/sh
set -e

# Ensure cache directory has proper permissions
if [ -d "${LCC_CACHE_DIR}" ]; then
    # Check if we have write permission
    if [ ! -w "${LCC_CACHE_DIR}" ]; then
        echo "Warning: No write permission for ${LCC_CACHE_DIR}"
        echo "Attempting to fix permissions..."
        # Try to fix - this will work if container is run as root initially
        chmod -R 755 "${LCC_CACHE_DIR}" 2>/dev/null || true
    fi
fi

# Execute the main command
exec "$@"
