#!/usr/bin/env python3
"""
Docker entrypoint script that ensures proper Python path setup.
"""
import sys
import os

# Ensure /app is in the Python path
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

# Now import and run main
if __name__ == "__main__":
    # Import main module
    exec(open('/app/main.py').read())
