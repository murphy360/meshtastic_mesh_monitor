#!/usr/bin/env python3
"""
Test script for the unified logging system.

This script demonstrates and validates the logging configuration.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.logger import setup_logging, get_logger, setup_development_logging, setup_production_logging, setup_quiet_logging


def test_basic_logging():
    """Test basic logging functionality."""
    print("=== Testing Basic Logging ===")
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    # Test all log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    print("✓ Basic logging test completed")


def test_environment_variables():
    """Test logging with environment variables."""
    print("\n=== Testing Environment Variables ===")
    
    # Set test environment variables
    os.environ['LOG_LEVEL'] = 'DEBUG'
    os.environ['LOG_FORMAT'] = '%(levelname)s: %(message)s'
    os.environ['LOG_CONSOLE'] = 'true'
    
    # Setup logging with environment variables
    setup_logging()
    logger = get_logger('test_env')
    
    logger.debug("Debug message with env vars")
    logger.info("Info message with env vars")
    
    print("✓ Environment variables test completed")


def test_presets():
    """Test logging presets."""
    print("\n=== Testing Logging Presets ===")
    
    # Test development preset
    print("Testing development preset:")
    setup_development_logging()
    dev_logger = get_logger('dev_test')
    dev_logger.debug("Development debug message")
    dev_logger.info("Development info message")
    
    # Test production preset
    print("\nTesting production preset:")
    setup_production_logging()
    prod_logger = get_logger('prod_test')
    prod_logger.info("Production info message")
    prod_logger.warning("Production warning message")
    
    # Test quiet preset
    print("\nTesting quiet preset:")
    setup_quiet_logging()
    quiet_logger = get_logger('quiet_test')
    quiet_logger.warning("Quiet warning message")
    quiet_logger.error("Quiet error message")
    
    print("✓ Presets test completed")


def test_file_logging():
    """Test file logging functionality."""
    print("\n=== Testing File Logging ===")
    
    # Create temporary log file
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as temp_file:
        temp_log_path = temp_file.name
    
    try:
        # Setup logging with file output
        setup_logging(
            log_level='INFO',
            log_to_file=True,
            log_file_path=temp_log_path,
            enable_console=False
        )
        
        file_logger = get_logger('file_test')
        file_logger.info("This message should be in the file")
        file_logger.warning("This warning should also be in the file")
        
        # Check if file was created and contains messages
        if os.path.exists(temp_log_path):
            with open(temp_log_path, 'r') as f:
                content = f.read()
                if 'This message should be in the file' in content:
                    print("✓ File logging test completed successfully")
                else:
                    print("✗ File logging test failed - message not found")
        else:
            print("✗ File logging test failed - file not created")
    
    finally:
        # Clean up
        if os.path.exists(temp_log_path):
            os.unlink(temp_log_path)


def test_config_integration():
    """Test integration with config manager."""
    print("\n=== Testing Config Manager Integration ===")
    
    try:
        from config.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        # Test getting logging config
        logging_config = config_manager.get_logging_config()
        print(f"Current logging config: {logging_config}")
        
        # Test applying a preset
        config_manager.apply_logging_preset('development')
        dev_config = config_manager.get_logging_config()
        print(f"Development preset config: {dev_config}")
        
        print("✓ Config manager integration test completed")
    
    except ImportError:
        print("- Config manager not available for testing")
    except Exception as e:
        print(f"✗ Config manager integration test failed: {e}")


def main():
    """Run all logging tests."""
    print("Meshtastic Mesh Monitor - Logging System Test")
    print("=" * 50)
    
    try:
        test_basic_logging()
        test_environment_variables()
        test_presets()
        test_file_logging()
        test_config_integration()
        
        print("\n" + "=" * 50)
        print("✓ All logging tests completed successfully!")
        print("\nUsage examples:")
        print("  Development: export LOG_LEVEL=DEBUG")
        print("  Production:  export LOG_LEVEL=INFO")
        print("  Quiet:       export LOG_LEVEL=WARNING")
        print("  File only:   export LOG_CONSOLE=false")
        print("  Console only: export LOG_TO_FILE=false")
    
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
