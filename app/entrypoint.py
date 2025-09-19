#!/usr/bin/env python3
"""
Docker entrypoint script that ensures proper Python path setup.
"""
import sys
import os

# Ensure /app is in the Python path
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

# print directory contents for debugging
print("Directory contents of /app:")
for root, dirs, files in os.walk('/app'):
    level = root.replace('/app', '').count(os.sep)
    indent = ' ' * 4 * (level)
    print(f"{indent}{os.path.basename(root)}/")
    subindent = ' ' * 4 * (level + 1)
    for f in files:
        print(f"{subindent}{f}")

# Now import and run main
if __name__ == "__main__":
    import main as main