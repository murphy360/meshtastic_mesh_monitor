#!/usr/bin/env python3
"""
Docker entrypoint script that ensures proper Python path setup.
"""
import sys
import os

# Debug: Print current working directory and contents
print(f"Current working directory: {os.getcwd()}")
print(f"Contents of /app: {os.listdir('/app')}")
if os.path.exists('/app/config'):
    print(f"Contents of /app/config: {os.listdir('/app/config')}")
else:
    print("No /app/config directory found!")

if os.path.exists('/app/core'):
    print(f"Contents of /app/core: {os.listdir('/app/core')}")
else:
    print("No /app/core directory found!")

# Ensure /app is in the Python path
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

print(f"Python sys.path: {sys.path}")

# Test the import
try:
    from config.config_manager import ConfigManager
    print("✓ config.config_manager import successful!")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    # Try alternative import
    try:
        import config.config_manager
        print("✓ Alternative import successful!")
    except ImportError as e2:
        print(f"✗ Alternative import also failed: {e2}")

# Now import and run main
if __name__ == "__main__":
    # Import main module
    exec(open('/app/main.py').read())
