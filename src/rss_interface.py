from datetime import datetime, timedelta, timezone
import logging
import requests
from typing import Dict, List
import xml.etree.ElementTree as ET

class RSSInterface:
    """Interface for accessing and monitoring RSS feeds."""
    
    def __init__(self, discard_initial_items: bool = True, config_manager=None):
        """
        Initialize the RSS interface.
        
        Args:
            discard_initial_items: If True, items found on first check will be 
                                  stored but not reported as new
            config_manager: ConfigManager instance for loading feed configuration
        """
        self.config_manager = config_manager
        self.feeds = {}
        self.feed_intervals = {}  # Store custom check intervals per feed
        self.last_check_time = {}
        self.check_interval = timedelta(hours=1)  # Default check interval
        self.previous_items = {}  # Store previous items to detect changes
        self.initial_check_complete = {}  # Track whether initial check is complete
        self.discard_initial_items = discard_initial_items
        
        # Initialize config manager if not provided
        if self.config_manager is None:
            from config_manager import ConfigManager
            self.config_manager = ConfigManager()
        
        # Load feeds from configuration
        self._load_feeds_from_config()
        
        logging.info(f"RSS Interface initialized with {len(self.feeds)} feeds (discard_initial_items={self.discard_initial_items})")

    def _load_feeds_from_config(self):
        """Load RSS feeds from configuration manager."""
        if self.config_manager:
            try:
                enabled_feeds = self.config_manager.get_enabled_rss_feeds()
                for feed_config in enabled_feeds:
                    feed_id = feed_config.get("id")
                    feed_url = feed_config.get("url")
                    check_interval_hours = feed_config.get("check_interval_hours", 1)
                    
                    if feed_id and feed_url:
                        self.feeds[feed_id] = feed_url
                        self.feed_intervals[feed_id] = timedelta(hours=check_interval_hours)
                        self.last_check_time[feed_id] = datetime.now(timezone.utc) - self.feed_intervals[feed_id]
                        self.previous_items[feed_id] = {}
                        self.initial_check_complete[feed_id] = False
                        logging.info(f"Loaded RSS feed: {feed_config.get('name', feed_id)} ({feed_id})")
                    else:
                        logging.warning(f"Invalid feed configuration: missing id or url - {feed_config}")
            except Exception as e:
                logging.error(f"Error loading feeds from configuration: {e}")
                self._load_default_feeds()
        else:
            logging.warning("No configuration manager provided, using default feeds")
            self._load_default_feeds()
    
    def _load_default_feeds(self):
        """Load default RSS feeds if configuration is not available."""
        default_feeds = {
            "twinsburg_calendar": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=58&CID=All-calendar.xml",
            "twinsburg_news": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=65&CID=All-0"
        }
        
        for feed_id, feed_url in default_feeds.items():
            self.feeds[feed_id] = feed_url
            self.feed_intervals[feed_id] = self.check_interval
            self.last_check_time[feed_id] = datetime.now(timezone.utc) - self.check_interval
            self.previous_items[feed_id] = {}
            self.initial_check_complete[feed_id] = False
            
        logging.info(f"RSS Interface initialized with {len(self.feeds)} feeds (discard_initial_items={self.discard_initial_items})")

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
            List[Dict[str, str]]: Parsed RSS items in a human-readable format
        """
        
        logging.debug("Parsing RSS feed content")
        items = []
        try:
            root = ET.fromstring(content)

            # Find the channel element
            channel = root.find('channel')
            if channel is None:
                # Sometimes the namespace is present, so try with namespace
                channel = root.find('{*}channel')
            if channel is None:
                logging.warning("No <channel> element found in RSS feed")
                return items

            # Iterate over all <item> elements
            for item_elem in channel.findall('item'):
                item = {}
                for child in item_elem:
                    tag = child.tag
                    # Remove namespace if present
                    if '}' in tag:
                        tag = tag.split('}', 1)[1]
                    # Store text content
                    item[tag] = child.text.strip() if child.text else ''
                    # For <enclosure> tag, get the url attribute
                    if tag == 'enclosure':
                        item['enclosure_url'] = child.attrib.get('url', '')
                        item['enclosure_type'] = child.attrib.get('type', '')
                items.append(item)
        except Exception as e:
            logging.error(f"Error parsing RSS feed: {e}")
        return items
        

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
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()           
            items = self._parse_rss(response.content)
            logging.debug(f"Parsed {len(items)} items from feed '{feed_id}'")
            current_items = {}
            
            # Process each item and find new ones
            for item in items:
                if 'guid' in item:
                    item_id = item['guid']
                    current_items[item_id] = item
                    # Add to new_items if not already seen
                    if item_id not in self.previous_items[feed_id] and self.initial_check_complete[feed_id]:
                        new_items.append(item)
                        logging.info(f"Adding: {item}")
            
            # Update previous items
            self.previous_items[feed_id] = current_items
            self.last_check_time[feed_id] = datetime.now(timezone.utc)
            
            # Mark initial check as complete
            if not self.initial_check_complete[feed_id]:
                self.initial_check_complete[feed_id] = True
                logging.info(f"Initial check of feed '{feed_id}' complete, discarding {len(items)} existing items") 
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
            feed_interval = self.feed_intervals.get(feed_id, self.check_interval)
            if now - last_check >= feed_interval:
                logging.info(f"Checking feed '{feed_id}' for updates")
                new_items = self.check_feed(feed_id)
                
                if new_items:
                    for item in new_items:
                        message = f"📰 New RSS Item Detected 📰\n\n"
                        message += f"Feed: {feed_id.replace('_', ' ')}\n"
                        message += f"Title: {item.get('title', 'No Title')}\n"
                        message += f"Link: {item.get('link', 'No Link')}\n"
                        message += f"Description: {item.get('description', 'No Description')}\n"
                        message += f"Published: {item.get('pubDate', 'No Date')}\n"
                        
                        message_callback(message, channel, destination)
                else:
                    logging.info(f"No new items found in feed '{feed_id}'")