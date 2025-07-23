#!/usr/bin/env python3
"""
Interface standardization demonstration script.

This script shows how the refactored interfaces now inherit from 
standardized base classes, providing consistent behavior and easier testing.
"""

import sys
import os

# Add the project root and src to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

from interfaces.weather_interface import WeatherGovInterface
from interfaces.rss_interface import RSSInterface
from interfaces.gemini_interface import GeminiInterface
from config.config_manager import ConfigManager

def test_interfaces():
    """Test the standardized interfaces."""
    
    print("=== Interface Standardization Demo ===\n")
    
    # Initialize config manager
    config_manager = ConfigManager()
    
    # Test Weather Interface (API-based)
    print("1. Testing Weather Interface (APIInterface)")
    print("-" * 40)
    try:
        weather = WeatherGovInterface(config_manager=config_manager)
        print(f"   Connection test: {'✅ Pass' if weather.test_connection() else '❌ Fail'}")
        status = weather.get_status()
        print(f"   Interface type: {status['interface_type']}")
        print(f"   Base URL: {status['base_url']}")
        print(f"   Cache entries: {status['cache_entries']}")
        print(f"   Current location: {status['city']}, {status['state']}")
        print()
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test RSS Interface (Feed-based)
    print("2. Testing RSS Interface (FeedInterface)")
    print("-" * 40)
    try:
        rss = RSSInterface(config_manager=config_manager)
        print(f"   Connection test: {'✅ Pass' if rss.test_connection() else '❌ Fail'}")
        status = rss.get_status()
        print(f"   Interface type: {status['interface_type']}")
        print(f"   Total feeds: {status['feed_status']['total_feeds']}")
        print(f"   Cache entries: {status['cache_entries']}")
        
        # Show feed details
        for feed_id, feed_info in status['feed_status']['feeds'].items():
            print(f"   Feed '{feed_id}': {feed_info['url'][:50]}...")
        print()
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test Gemini Interface (Base interface)
    print("3. Testing Gemini Interface (BaseInterface)")
    print("-" * 40)
    try:
        # Only test if API key is available
        if os.getenv('GEMINI_API_KEY'):
            gemini = GeminiInterface(config_manager=config_manager)
            print(f"   Connection test: {'✅ Pass' if gemini.test_connection() else '❌ Fail'}")
            status = gemini.get_status()
            print(f"   Interface type: {status['interface_type']}")
            print(f"   Location: {status['location']}")
            print(f"   Max message length: {status['max_message_length']}")
            print(f"   API key available: {'✅ Yes' if status['has_api_key'] else '❌ No'}")
        else:
            print("   ⚠️  Skipped: GEMINI_API_KEY not set")
        print()
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    print("=== Base Class Features Demo ===\n")
    
    # Show caching capabilities
    print("4. Testing Base Class Caching")
    print("-" * 30)
    weather = WeatherGovInterface(config_manager=config_manager)
    
    # Add some test data to cache
    weather._cache_data("test_key", {"test": "data"}, 60)
    cached_data = weather._get_cached_data("test_key")
    print(f"   Cache test: {'✅ Pass' if cached_data else '❌ Fail'}")
    print(f"   Cached data: {cached_data}")
    
    # Test cache expiry
    weather._cache_data("expired_key", {"expired": "data"}, -1)  # Already expired
    expired_data = weather._get_cached_data("expired_key")
    print(f"   Expiry test: {'✅ Pass' if not expired_data else '❌ Fail'}")
    print()
    
    # Show polling capabilities
    print("5. Testing Polling Interface Features")
    print("-" * 35)
    rss = RSSInterface(config_manager=config_manager)
    
    # Check if polling is needed
    first_feed = next(iter(rss.feeds)) if rss.feeds else None
    if first_feed:
        should_poll = rss._should_poll(first_feed)
        print(f"   Should poll '{first_feed}': {'✅ Yes' if should_poll else '❌ No'}")
        
        # Set a custom poll interval
        rss._set_poll_interval(first_feed, 7200)  # 2 hours
        print(f"   Custom interval set: ✅ 2 hours")
    
    print("\n=== Migration Complete ===")
    print("✅ All interfaces now inherit from standardized base classes")
    print("✅ Common functionality is centralized and consistent")
    print("✅ Easier testing and maintenance")
    print("✅ Ready for Phase 3 improvements")

if __name__ == "__main__":
    test_interfaces()
