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
    config_contents = os.listdir('/app/config')
    print(f"Contents of /app/config: {config_contents}")
    if 'config_manager.py' in config_contents:
        print("✓ config_manager.py found!")
    else:
        print("✗ config_manager.py NOT found!")
        # Check for any .py files
        py_files = [f for f in config_contents if f.endswith('.py')]
        print(f"Python files in /app/config: {py_files}")
else:
    print("No /app/config directory found!")

if os.path.exists('/app/core'):
    print(f"Contents of /app/core: {os.listdir('/app/core')}")
else:
    print("No /app/core directory found!")

if os.path.exists('/app/config_files'):
    print(f"Contents of /app/config_files: {os.listdir('/app/config_files')}")
else:
    print("No /app/config_files directory found!")

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
    
    # If the config directory is empty, try to copy files manually
    if os.path.exists('/app/config_files') and not os.listdir('/app/config'):
        print("Attempting to manually fix the config directory...")
        
        # Check if we have config files in the source that we can copy
        import shutil
        
        # Since the src files should be in /app, let's look for them
        possible_config_sources = [
            '/app/src/config',  # In case src structure is preserved
            '/app/config_files'  # Last resort, though this has JSON files
        ]
        
        for source in possible_config_sources:
            if os.path.exists(source):
                print(f"Found potential source: {source}")
                try:
                    # List what's in the source
                    print(f"Contents of {source}: {os.listdir(source)}")
                except:
                    pass
        
        # Try to find config_manager.py anywhere in /app
        import glob
        config_files = glob.glob('/app/**/config_manager.py', recursive=True)
        print(f"Found config_manager.py files: {config_files}")
        
        if config_files:
            # Copy the config_manager.py to the right location
            config_dir = os.path.dirname(config_files[0])
            print(f"Copying from {config_dir} to /app/config/")
            if not os.path.exists('/app/config'):
                os.makedirs('/app/config')
            
            for file in os.listdir(config_dir):
                if file.endswith('.py'):
                    src_file = os.path.join(config_dir, file)
                    dst_file = os.path.join('/app/config', file)
                    shutil.copy2(src_file, dst_file)
                    print(f"Copied {src_file} to {dst_file}")
    
    # Try the import again
    try:
        from config.config_manager import ConfigManager
        print("✓ config.config_manager import successful after manual fix!")
    except ImportError as e2:
        print(f"✗ Import still failed after manual fix: {e2}")
        # Add the config directory manually to sys.path as a last resort
        sys.path.insert(0, '/app/config')
        try:
            import config_manager
            print("✓ Direct config_manager import successful!")
            # Create a dummy config module
            import types
            config_module = types.ModuleType('config')
            config_module.config_manager = config_manager
            sys.modules['config'] = config_module
            sys.modules['config.config_manager'] = config_manager
        except ImportError as e3:
            print(f"✗ All import attempts failed: {e3}")
            raise

# Now import and run main
if __name__ == "__main__":
    # Import main module
    exec(open('/app/main.py').read())
