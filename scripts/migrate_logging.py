#!/usr/bin/env python3
"""
Migration script to update existing Python files to use the unified logging system.

This script helps convert existing logging patterns to use the new unified logger.
"""

import os
import re
import argparse
from pathlib import Path


def update_file_logging(file_path: Path) -> bool:
    """
    Update a Python file to use the unified logging system.
    
    Args:
        file_path: Path to the Python file to update
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        # Check if file already uses unified logging
        if 'from utils.logger import' in content:
            print(f"✓ {file_path.name} already uses unified logging")
            return False
        
        # Pattern 1: Remove standalone logging.basicConfig
        basicconfig_pattern = r'logging\.basicConfig\([^)]*\)\s*\n?'
        if re.search(basicconfig_pattern, content):
            content = re.sub(basicconfig_pattern, '', content)
            modified = True
        
        # Pattern 2: Add unified logging import after existing imports
        import_pattern = r'(import logging\s*\n)'
        if re.search(import_pattern, content):
            replacement = r'\1from utils.logger import get_logger\n\n# Get logger instance\nlogger = get_logger(__name__)\n'
            content = re.sub(import_pattern, replacement, content, count=1)
            modified = True
        
        # Pattern 3: If no logging import, add it after other imports
        elif 'import ' in content and 'logging' not in content:
            # Find the last import statement
            import_lines = []
            lines = content.split('\n')
            last_import_idx = -1
            
            for i, line in enumerate(lines):
                if (line.strip().startswith('import ') or 
                    line.strip().startswith('from ') and ' import ' in line):
                    last_import_idx = i
            
            if last_import_idx >= 0:
                lines.insert(last_import_idx + 1, 'from utils.logger import get_logger')
                lines.insert(last_import_idx + 2, '')
                lines.insert(last_import_idx + 3, '# Get logger instance')
                lines.insert(last_import_idx + 4, 'logger = get_logger(__name__)')
                lines.insert(last_import_idx + 5, '')
                content = '\n'.join(lines)
                modified = True
        
        # Save the modified file
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated {file_path.name}")
            return True
        else:
            print(f"- No changes needed for {file_path.name}")
            return False
    
    except Exception as e:
        print(f"✗ Error updating {file_path.name}: {e}")
        return False


def find_python_files(directory: Path, exclude_dirs: set = None) -> list:
    """Find all Python files in a directory."""
    if exclude_dirs is None:
        exclude_dirs = {'__pycache__', '.git', 'venv', 'env', '.pytest_cache'}
    
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py') and not file.startswith('.'):
                python_files.append(Path(root) / file)
    
    return python_files


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Migrate Python files to unified logging')
    parser.add_argument('--directory', '-d', type=str, default='src',
                       help='Directory to scan for Python files (default: src)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without modifying files')
    parser.add_argument('--file', '-f', type=str,
                       help='Update a specific file instead of scanning directory')
    
    args = parser.parse_args()
    
    if args.file:
        # Update specific file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"✗ File not found: {file_path}")
            return
        
        if args.dry_run:
            print(f"Would update: {file_path}")
        else:
            update_file_logging(file_path)
    else:
        # Scan directory
        directory = Path(args.directory)
        if not directory.exists():
            print(f"✗ Directory not found: {directory}")
            return
        
        python_files = find_python_files(directory)
        
        if not python_files:
            print(f"No Python files found in {directory}")
            return
        
        print(f"Found {len(python_files)} Python files in {directory}")
        
        if args.dry_run:
            print("\nDry run - files that would be updated:")
            for file_path in python_files:
                print(f"  {file_path}")
        else:
            print("\nUpdating files...")
            updated_count = 0
            for file_path in python_files:
                if update_file_logging(file_path):
                    updated_count += 1
            
            print(f"\n✓ Updated {updated_count} out of {len(python_files)} files")
            
            if updated_count > 0:
                print("\nNext steps:")
                print("1. Review the changes made to your files")
                print("2. Replace 'logging.' calls with 'logger.' where appropriate")
                print("3. Test your application to ensure logging works correctly")
                print("4. Set LOG_LEVEL environment variable for your deployment")


if __name__ == '__main__':
    main()
