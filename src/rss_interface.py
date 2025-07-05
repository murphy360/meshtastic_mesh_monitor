from datetime import datetime, timedelta, timezone
import logging
import requests
from typing import Dict, List

class RSSInterface:
    """Interface for accessing and monitoring RSS feeds."""
    
    def __init__(self, discard_initial_items: bool = True):
        """
        Initialize the RSS interface.
        
        Args:
            discard_initial_items: If True, items found on first check will be 
                                  stored but not reported as new
        """
        self.feeds = {
            "twinsburg_calendar": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=58&CID=All-calendar.xml",
            "twinsburg_news": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=65&CID=All-0"
        }
        self.last_check_time = {}
        self.check_interval = timedelta(hours=1)  # Check feeds every hour by default
        self.previous_items = {}  # Store previous items to detect changes
        self.initial_check_complete = {}  # Track whether initial check is complete
        self.discard_initial_items = discard_initial_items
        
        # Initialize last check time and previous items for each feed
        for feed_id in self.feeds:
            self.last_check_time[feed_id] = datetime.now(timezone.utc) - self.check_interval
            self.previous_items[feed_id] = {}
            self.initial_check_complete[feed_id] = False
            
        logging.info(f"RSS Interface initialized with {len(self.feeds)} feeds (discard_initial_items={discard_initial_items})")

    def add_feed(self, feed_id: str, url: str):
        """
        Add a new RSS feed to monitor.
        
        Args:
            feed_id: A unique identifier for this feed
            url: The URL of the RSS feed
        """
        if feed_id in self.feeds:
            logging.warning(f"Feed ID '{feed_id}' already exists, updating URL")
        
        self.feeds[feed_id] = url
        self.last_check_time[feed_id] = datetime.now(timezone.utc) - self.check_interval
        self.previous_items[feed_id] = {}
        self.initial_check_complete[feed_id] = False
        logging.info(f"Added RSS feed: {feed_id} - {url}")

    def _parse_rss(self, content: bytes) -> List[Dict[str, str]]:
        """
        Parse the RSS feed content.
        
        Args:
            content: The RSS feed content as bytes
            
        Returns:
            List[Dict[str, str]]: Parsed RSS items
        """
        # Placeholder for RSS parsing logic
        return []

    def check_feed(self, feed_id: str) -> List[Dict[str, str]]:
        """
        Check a specific RSS feed for new items.
        
        Args:
            feed_id: The identifier of the feed to check
            
        Returns:
            List[Dict[str, str]]: List of new items (may be empty on first check if discard_initial_items is True)
        """
        if feed_id not in self.feeds:
            logging.warning(f"Feed ID '{feed_id}' not found")
            return []
        
        url = self.feeds[feed_id]
        new_items = []
        is_initial_check = not self.initial_check_complete[feed_id]
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            logging.info(f"requested RSS feed '{feed_id}' successfully. {response}")
            logging.info(f"Response content: {response.content}") 
            
            items = self._parse_rss(response.content)
            current_items = {}
            
            # Process each item and find new ones
            for item in items:
                logging.debug(f"Processing item: {item}")
                if 'guid' in item:
                    item_id = item['guid']
                    current_items[item_id] = item
                    logging.info(f"Processing item '{item_id}' from feed '{feed_id}'")
                    # Add to new_items if not already seen
                    if item_id not in self.previous_items[feed_id]:
                        logging.info(f"Adding '{feed_id}': {item.get('title', 'No Title')}")
                        new_items.append(item)
            
            # Update previous items
            self.previous_items[feed_id] = current_items
            self.last_check_time[feed_id] = datetime.now(timezone.utc)
            
            # Mark initial check as complete
            if is_initial_check:
                self.initial_check_complete[feed_id] = True
                if self.discard_initial_items and len(new_items) > 1:
                    num_items_removed = len(new_items)-1
                    logging.info(f"Initial check of feed '{feed_id}' complete, discarding {num_items_removed} initial items. Keeping only the first item.")
                    new_items = new_items[0:1]  # Keep only the first item if discarding initial items
                    logging.info(f"Reporting items: {new_items[0].get('title', 'No Title')}")
                else:
                    logging.info(f"Initial check of feed '{feed_id}' complete, found {len(new_items)} items")
            else:
                logging.info(f"Checked feed '{feed_id}', found {len(new_items)} new items")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching RSS feed '{feed_id}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error checking feed '{feed_id}': {e}")
        
        return new_items
    
    def check_feeds_if_needed(self, message_callback, channel: int, destination: str):
        """
        Check all configured RSS feeds if the check interval has elapsed.
        
        Args:
            message_callback: Function to call with new items found
            channel: Channel ID for sending messages
            destination: Destination ID for messages (usually "^all")
        """
        now = datetime.now(timezone.utc)
        
        for feed_id, last_check in self.last_check_time.items():
            if now - last_check >= self.check_interval:
                logging.info(f"Checking feed '{feed_id}' for updates")
                new_items = self.check_feed(feed_id)
                
                if new_items:
                    for item in new_items:
                        message = f"📰 New RSS Item Detected 📰\n\n"
                        message += f"Title: {item.get('title', 'No Title')}\n"
                        message += f"Link: {item.get('link', 'No Link')}\n"
                        message += f"Description: {item.get('description', 'No Description')}\n"
                        
                        message_callback(message, channel, destination)
                else:
                    logging.info(f"No new items found in feed '{feed_id}'")