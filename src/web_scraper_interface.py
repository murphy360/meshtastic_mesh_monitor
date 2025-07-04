import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Callable, Any, Optional, Tuple
import time
import re

class WebScraperInterface:
    """Interface for scraping websites and monitoring for changes."""
    
    def __init__(self, discard_initial_items: bool = True):
        """
        Initialize the web scraper interface.
        
        Args:
            discard_initial_items: If True, items found on first check will be 
                                  stored but not reported as new
        """
        self.websites = {}  # Dict to store website configurations
        self.last_check_time = {}
        self.check_interval = timedelta(hours=1)  # Check websites every hour by default
        self.previous_items = {}  # Store previous content to detect changes
        self.initial_check_complete = {}  # Track whether initial check is complete
        self.discard_initial_items = discard_initial_items
        
        logging.info(f"Web Scraper Interface initialized (discard_initial_items={discard_initial_items})")
    
    def add_website(self, website_id: str, url: str, css_selector: str = None, 
                   extractor_type: str = "generic", custom_parser: Callable = None):
        """
        Add a website to monitor.
        
        Args:
            website_id: A unique identifier for this website
            url: The URL of the website to scrape
            css_selector: CSS selector to extract specific content
            extractor_type: Type of content to extract ("generic", "links", "twinsburg_agendas")
            custom_parser: Optional custom parsing function for special cases
        """
        self.websites[website_id] = {
            'url': url,
            'css_selector': css_selector,
            'extractor_type': extractor_type,
            'custom_parser': custom_parser
        }
        self.last_check_time[website_id] = datetime.now(timezone.utc) - self.check_interval
        self.previous_items[website_id] = {}
        self.initial_check_complete[website_id] = False
        logging.info(f"Added website to monitor: {website_id} - {url} - {extractor_type}")
    
    def remove_website(self, website_id: str) -> bool:
        """
        Remove a website from monitoring.
        
        Args:
            website_id: The identifier of the website to remove
            
        Returns:
            bool: True if the website was removed, False if it wasn't found
        """
        if website_id in self.websites:
            del self.websites[website_id]
            del self.last_check_time[website_id]
            del self.previous_items[website_id]
            del self.initial_check_complete[website_id]
            logging.info(f"Removed website: {website_id}")
            return True
        return False
    
    def set_check_interval(self, hours: float):
        """
        Set how often to check websites for changes.
        
        Args:
            hours: Number of hours between website checks
        """
        self.check_interval = timedelta(hours=hours)
        logging.info(f"Website check interval set to {hours} hours")
    
    def _extract_links_and_titles(self, soup: BeautifulSoup, css_selector: str = None) -> List[Dict[str, str]]:
        """
        Extract links and their titles from HTML.
        
        Args:
            soup: BeautifulSoup object of the parsed HTML
            css_selector: CSS selector to find the container elements
            
        Returns:
            List of dicts with 'url', 'title', and 'id' keys
        """
        items = []
        
        try:
            # If a CSS selector is provided, use it to find container elements
            if css_selector:
                containers = soup.select(css_selector)
            else:
                # Otherwise just look for all links
                containers = [soup]
            
            # Process each container
            for container in containers:
                links = container.find_all('a')
                
                for link in links:
                    href = link.get('href')
                    if href:
                        # Try to get the title from different sources
                        title = link.get_text(strip=True)
                        if not title:
                            title = link.get('title', '')
                        
                        # Create a unique ID for this item
                        item_id = f"{href}|{title}"
                        
                        items.append({
                            'url': href,
                            'title': title,
                            'id': item_id
                        })
        
        except Exception as e:
            logging.error(f"Error extracting links and titles: {e}")
        
        return items
    
    def _extract_twinsburg_agendas(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract agenda links and titles from Twinsburg school website.
        
        Args:
            soup: BeautifulSoup object of the parsed HTML
            
        Returns:
            List of dicts with agenda information
        """
        items = []
        
        try:
            # Find the agenda container
            agenda_container = soup.select_one('.component_container_downloads')
            
            if not agenda_container:
                logging.warning("Could not find agenda container")
                return items
            
            # Find all links in the container
            links = agenda_container.find_all('a', class_='downloadcomponent_linktext')
            
            for link in links:
                href = link.get('href')
                if href:
                    title = link.get_text(strip=True)
                    
                    # Create a unique ID for this item
                    item_id = f"{href}|{title}"
                    
                    # Get the full URL if it's relative
                    if href.startswith('/') or not href.startswith(('http://', 'https://')):
                        # Extract base URL from the website URL
                        base_url = re.match(r'(https?://[^/]+)', soup.get('base_url', '')).group(1)
                        href = f"{base_url}{'' if href.startswith('/') else '/'}{href}"
                    
                    items.append({
                        'url': href,
                        'title': title,
                        'id': item_id,
                        'type': 'agenda'
                    })
        
        except Exception as e:
            logging.error(f"Error extracting Twinsburg agendas: {e}")
        
        return items
    
    def check_website(self, website_id: str) -> List[Dict[str, Any]]:
        """
        Check a specific website for new content.
        
        Args:
            website_id: The identifier of the website to check
            
        Returns:
            List of new items found (may be empty on first check if discard_initial_items is True)
        """
        if website_id not in self.websites:
            logging.warning(f"Website ID '{website_id}' not found")
            return []
        
        config = self.websites[website_id]
        url = config['url']
        css_selector = config['css_selector']
        extractor_type = config['extractor_type']
        custom_parser = config['custom_parser']
        
        new_items = []
        is_initial_check = not self.initial_check_complete[website_id]
        
        try:
            # Fetch the webpage
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Store base URL in soup object for reference
            soup.base_url = url
            
            # Extract items based on extractor type
            current_items = {}
            items = []
            
            if extractor_type == "links":
                items = self._extract_links_and_titles(soup, css_selector)
            elif extractor_type == "twinsburg_agendas":
                items = self._extract_twinsburg_agendas(soup)
            elif custom_parser:
                items = custom_parser(soup, css_selector)
            else:
                # Generic content extraction
                if css_selector:
                    elements = soup.select(css_selector)
                    content_text = '\n'.join([element.get_text(strip=True) for element in elements])
                else:
                    content_text = soup.body.get_text(strip=True)
                
                items = [{
                    'id': 'content',
                    'content': content_text,
                    'type': 'text'
                }]
            
            # Convert items to a dictionary keyed by ID
            for item in items:
                item_id = item.get('id')
                if item_id:
                    current_items[item_id] = item
                    
                    # Check if this is a new item
                    if item_id not in self.previous_items[website_id] and (not is_initial_check or not self.discard_initial_items):
                        new_items.append(item)
            
            # Update previous items
            self.previous_items[website_id] = current_items
            self.last_check_time[website_id] = datetime.now(timezone.utc)
            
            # Mark initial check as complete
            if is_initial_check:
                self.initial_check_complete[website_id] = True
                if self.discard_initial_items:
                    logging.info(f"Initial check of website '{website_id}' complete, discarded {len(items)} initial items")
                else:
                    logging.info(f"Initial check of website '{website_id}' complete, found {len(new_items)} items")
            else:
                logging.info(f"Checked website '{website_id}', found {len(new_items)} new items")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching website '{website_id}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error checking website '{website_id}': {e}")
        
        return new_items
    
    def scrape_websites_if_needed(self, 
                                 message_callback: Callable[[str, int, str], None],
                                 channel: int,
                                 destination: str,
                                 log_callback: Callable[[str], None] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Check all websites for changes if the check interval has elapsed.
        
        Args:
            message_callback: Function to send messages to the mesh network
            channel: Channel number for notifications
            destination: Destination ID for messages (usually "^all")
            log_callback: Optional function to log message types
            
        Returns:
            Dict mapping website IDs to lists of new items
        """
        now = datetime.now(timezone.utc)
        result = {}
        
        for website_id, config in self.websites.items():
            # Only check if interval has elapsed
            if now - self.last_check_time[website_id] >= self.check_interval:
                new_items = self.check_website(website_id)
                
                if new_items:
                    result[website_id] = new_items
                    
                    # Send notification for each new item
                    for item in new_items:
                        # Format message based on item type
                        if 'title' in item and 'url' in item:
                            # Format link items
                            message = f"🔗 New Content: {website_id.replace('_', ' ').title()} 🔗\n\n"
                            message += f"{item['title']}\n\n"
                            message += f"URL: {item['url']}"
                        elif 'content' in item:
                            # Format text content
                            message = f"📄 Content Update: {website_id.replace('_', ' ').title()} 📄\n\n"
                            content = item['content']
                            if len(content) > 300:
                                content = content[:297] + "..."
                            message += content
                        else:
                            # Generic format for other items
                            message = f"🌐 Update Detected: {website_id.replace('_', ' ').title()} 🌐\n\n"
                            message += f"New content has been detected on this website."
                        
                        # Send message
                        message_callback(message, channel, destination)
                        
                        if log_callback:
                            log_callback(f"web-scrape-{website_id}")
        
        return result
