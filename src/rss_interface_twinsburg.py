import requests
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
import time
import re
from html import unescape

class RSSInterface:
    """Interface for accessing and monitoring RSS feeds."""
    
    def __init__(self):
        """Initialize the RSS interface."""
        self.feeds = {
            "twinsburg_calendar": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=58&CID=All-calendar.xml",
            "twinsburg_news": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=65&CID=All-0"
        }
        self.last_check_time = {}
        self.check_interval = timedelta(hours=1)  # Check feeds every hour by default
        self.previous_items = {}  # Store previous items to detect changes
        
        # Initialize last check time and previous items for each feed
        for feed_id in self.feeds:
            self.last_check_time[feed_id] = datetime.now(timezone.utc) - self.check_interval
            self.previous_items[feed_id] = {}
            
        logging.info(f"RSS Interface initialized with {len(self.feeds)} feeds")
    
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
        logging.info(f"Added RSS feed: {feed_id} - {url}")
    
    def remove_feed(self, feed_id: str) -> bool:
        """
        Remove an RSS feed from monitoring.
        
        Args:
            feed_id: The identifier of the feed to remove
            
        Returns:
            bool: True if the feed was removed, False if it wasn't found
        """
        if feed_id in self.feeds:
            del self.feeds[feed_id]
            del self.last_check_time[feed_id]
            del self.previous_items[feed_id]
            logging.info(f"Removed RSS feed: {feed_id}")
            return True
        return False
    
    def set_check_interval(self, hours: float):
        """
        Set how often to check for new RSS items.
        
        Args:
            hours: Number of hours between RSS feed checks
        """
        self.check_interval = timedelta(hours=hours)
        logging.info(f"RSS check interval set to {hours} hours")
    
    def _clean_html(self, text: str) -> str:
        """
        Clean HTML tags and entities from text.
        
        Args:
            text: The HTML text to clean
            
        Returns:
            str: The cleaned text
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Convert HTML entities
        text = unescape(text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _parse_rss(self, content: str) -> List[Dict[str, str]]:
        """
        Parse RSS content into a list of items.
        
        Args:
            content: The XML content of the RSS feed
            
        Returns:
            List[Dict[str, str]]: List of items with their properties
        """
        items = []
        try:
            root = ET.fromstring(content)
            
            # Find the channel element (might be at different levels depending on RSS version)
            channel = root.find('.//channel')
            if channel is None:
                channel = root  # Some RSS feeds have items directly under root
            
            # Process each item
            for item in channel.findall('.//item'):
                item_data = {}
                
                # Extract standard RSS fields
                for field in ['title', 'link', 'description', 'pubDate', 'guid']:
                    elem = item.find(field)
                    if elem is not None and elem.text:
                        if field == 'description':
                            item_data[field] = self._clean_html(elem.text)
                        else:
                            item_data[field] = elem.text.strip()
                
                # Generate an ID if guid is missing
                if 'guid' not in item_data:
                    if 'link' in item_data:
                        item_data['guid'] = item_data['link']
                    elif 'title' in item_data:
                        item_data['guid'] = item_data['title']
                
                # Only add items with at least a title or description
                if 'title' in item_data or 'description' in item_data:
                    items.append(item_data)
            
            logging.debug(f"Parsed {len(items)} items from RSS feed")
            
        except ET.ParseError as e:
            logging.error(f"XML parsing error: {e}")
        except Exception as e:
            logging.error(f"Error parsing RSS content: {e}")
        
        return items
    
    def check_feed(self, feed_id: str) -> List[Dict[str, str]]:
        """
        Check a specific RSS feed for new items.
        
        Args:
            feed_id: The identifier of the feed to check
            
        Returns:
            List[Dict[str, str]]: List of new items
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
            current_items = {}
            
            # Process each item and find new ones
            for item in items:
                if 'guid' in item:
                    item_id = item['guid']
                    current_items[item_id] = item
                    
                    if item_id not in self.previous_items[feed_id]:
                        new_items.append(item)
            
            # Update previous items
            self.previous_items[feed_id] = current_items
            self.last_check_time[feed_id] = datetime.now(timezone.utc)
            
            logging.info(f"Checked feed '{feed_id}', found {len(new_items)} new items")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching RSS feed '{feed_id}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error checking feed '{feed_id}': {e}")
        
        return new_items
    
    def check_feeds_if_needed(self, 
                              message_callback: Callable[[str, int, str], None],
                              channel: int,
                              destination: str,
                              log_callback: Callable[[str], None] = None) -> Dict[str, List[Dict[str, str]]]:
        """
        Check all RSS feeds for new items if the check interval has elapsed.
        
        This function checks each RSS feed for new items, but only if the
        specified check interval has elapsed since the last check. When new
        items are found, they are sent to the specified channel using the
        provided callback.
        
        Args:
            message_callback: Function used to send messages to the mesh network
                            Should accept (message, channel, destination) parameters
            channel: Channel number for RSS notifications
            destination: Destination ID for messages (usually "^all")
            log_callback: Optional function to log message types that were sent
                        Should accept a single string parameter
            
        Returns:
            Dict mapping feed IDs to lists of new items
        """
        now = datetime.now(timezone.utc)
        result = {}
        
        for feed_id, url in self.feeds.items():
            # Only check if interval has elapsed
            if now - self.last_check_time[feed_id] >= self.check_interval:
                new_items = self.check_feed(feed_id)
                
                if new_items:
                    result[feed_id] = new_items
                    
                    # Send notification for each new item
                    for item in new_items:
                        # Create message with title and description
                        message = f"📰 {feed_id.replace('_', ' ').title()} Update 📰\n\n"
                        
                        if 'title' in item:
                            message += f"{item['title']}\n\n"
                        
                        if 'description' in item:
                            # Truncate description if too long
                            desc = item['description']
                            if len(desc) > 300:
                                desc = desc[:297] + "..."
                            message += f"{desc}\n"
                        
                        if 'link' in item:
                            message += f"\nLink: {item['link']}"
                        
                        # Send message
                        message_callback(message, channel, destination)
                        
                        if log_callback:
                            log_callback(f"rss-{feed_id}")
        
        return result
    
    def format_item_summary(self, item: Dict[str, str]) -> str:
        """
        Format an RSS item into a readable summary string.
        
        Args:
            item: The RSS item to format
            
        Returns:
            str: A formatted summary string
        """
        summary = ""
        
        if 'title' in item:
            summary += f"📰 {item['title']}\n\n"
        
        if 'pubDate' in item:
            try:
                # Try to parse and format the date
                pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
                summary += f"Published: {pub_date.strftime('%Y-%m-%d %H:%M')}\n\n"
            except ValueError:
                # If parsing fails, just use the original string
                summary += f"Published: {item['pubDate']}\n\n"
        
        if 'description' in item:
            # Truncate description if too long
            desc = item['description']
            if len(desc) > 300:
                desc = desc[:297] + "..."
            summary += f"{desc}\n\n"
        
        if 'link' in item:
            summary += f"Link: {item['link']}"
        
        return summary
