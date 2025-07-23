#!/usr/bin/env python3
"""
Example script showing how to use the updated configuration system.
RSS and Web Scraper interfaces now manage their own configuration internally.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rss_interface import RSSInterface
from web_scraper_interface import WebScraperInterface

def main():
    # Initialize RSS interface (config manager is created internally)
    print("Initializing RSS Interface...")
    rss_interface = RSSInterface()
    
    print(f"RSS Interface loaded with {len(rss_interface.feeds)} feeds:")
    for feed_id, feed_url in rss_interface.feeds.items():
        interval_hours = rss_interface.feed_intervals.get(feed_id).total_seconds() / 3600
        print(f"  - {feed_id}: {feed_url} (check every {interval_hours} hours)")
    
    print("\nInitializing Web Scraper Interface...")
    web_scraper = WebScraperInterface()
    
    print(f"Web Scraper Interface loaded with {len(web_scraper.websites)} websites:")
    for website_id, config in web_scraper.websites.items():
        interval_hours = web_scraper.website_intervals.get(website_id).total_seconds() / 3600
        print(f"  - {website_id}: {config['url']} (check every {interval_hours} hours)")
    
    # Example: Check a specific RSS feed
    if rss_interface.feeds:
        first_feed_id = list(rss_interface.feeds.keys())[0]
        print(f"\nChecking RSS feed '{first_feed_id}' for updates...")
        new_items = rss_interface.check_feed(first_feed_id)
        print(f"Found {len(new_items)} new items")
    
    # Example: Check a specific website
    if web_scraper.websites:
        first_website_id = list(web_scraper.websites.keys())[0]
        print(f"\nChecking website '{first_website_id}' for updates...")
        new_items = web_scraper.check_website(first_website_id)
        print(f"Found {len(new_items)} new items")

if __name__ == "__main__":
    main()
