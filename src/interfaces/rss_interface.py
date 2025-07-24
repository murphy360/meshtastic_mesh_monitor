from datetime import datetime, timedelta, timezone
import logging
import requests
from typing import Dict, List, Any
import xml.etree.ElementTree as ET
from core.base_interfaces import FeedInterface

class RSSInterface(FeedInterface):
    """Interface for accessing and monitoring RSS feeds."""
    
    def __init__(self, discard_initial_items: bool = True, config_manager=None):
        """
        Initialize the RSS interface.
        
        Args:
            discard_initial_items: If True, items found on first check will be 
                                  stored but not reported as new
            config_manager: ConfigManager instance for loading feed configuration
        """
        super().__init__(
            config_manager=config_manager,
            cache_duration_seconds=3600,  # Cache feed content for 1 hour
            default_poll_interval_seconds=3600,  # Poll every hour by default
            discard_initial_items=discard_initial_items
        )
        
        # RSS-specific attributes that extend the base class
        self.check_interval = timedelta(hours=1)  # Default check interval (kept for compatibility)
        
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
                        # Use the base class method to add the feed
                        self.add_feed(feed_id, feed_url, check_interval_hours * 3600)  # Convert to seconds
                        
                        # Initialize RSS-specific tracking using base class attributes
                        self.last_poll_time[feed_id] = datetime.now(timezone.utc) - timedelta(hours=check_interval_hours)
                        self.previous_data[feed_id] = {}  # Use base class previous_data instead of previous_items
                        
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
            # Use base class method to add feeds
            self.add_feed(feed_id, feed_url, 3600)  # 1 hour interval in seconds
            self.last_poll_time[feed_id] = datetime.now(timezone.utc) - self.check_interval
            
        logging.info(f"RSS Interface initialized with {len(self.feeds)} default feeds")

    def parse_feed(self, feed_content: str) -> List[Dict[str, str]]:
        """
        Parse RSS feed content and return list of items.
        
        Args:
            feed_content: Raw RSS feed content as string
            
        Returns:
            List of dictionaries containing parsed RSS items
        """
        return self._parse_rss(feed_content.encode('utf-8'))

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
                    if item_id not in self.previous_data[feed_id] and self.initial_check_complete[feed_id]:
                        new_items.append(item)
                        logging.info(f"Adding: {item}")
            
            # Update previous items using base class attribute
            self.previous_data[feed_id] = current_items
            self.last_poll_time[feed_id] = datetime.now(timezone.utc)
            
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
        
        for feed_id, last_check in self.last_poll_time.items():
            feed_interval = self.poll_intervals.get(feed_id, self.default_poll_interval)
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

    def poll_for_updates(self) -> Dict[str, Any]:
        """
        Poll all feeds for updates.
        
        Returns:
            Dictionary containing update information
        """
        updates = {}
        for feed_id in self.feeds:
            if self._should_poll(feed_id):
                try:
                    new_items = self.check_feed(feed_id)
                    updates[feed_id] = {
                        "success": True,
                        "new_items": new_items,
                        "count": len(new_items)
                    }
                    self._update_poll_time(feed_id)
                except Exception as e:
                    updates[feed_id] = {
                        "success": False,
                        "error": str(e),
                        "count": 0
                    }
        return updates

    def test_connection(self) -> bool:
        """Test if the interface can connect to at least one feed."""
        if not self.feeds:
            return False
        
        # Test the first feed
        first_feed_id = next(iter(self.feeds))
        try:
            response = requests.get(self.feeds[first_feed_id], timeout=10)
            return response.status_code == 200
        except Exception:
            return False