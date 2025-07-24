import os
import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Callable, Any, Optional, Tuple
import time
import re
import sys
from config.config_manager import ConfigManager

class WebScraperInterface:
    """Interface for scraping websites and monitoring for changes."""
    
    def __init__(self, discard_initial_items: bool = True, config_manager=None):
        """
        Initialize the web scraper interface.
        
        Args:
            discard_initial_items: If True, items found on first check will be 
                                  stored but not reported as new
            config_manager: ConfigManager instance for loading scraper configuration
        """
        self.config_manager = config_manager
        self.websites = {}  # Dict to store website configurations
        self.website_intervals = {}  # Store custom check intervals per website
        self.last_check_time = {}
        self.check_interval = timedelta(hours=1)  # Check websites every hour by default
        self.previous_items = {}  # Store previous content to detect changes
        self.initial_check_complete = {}  # Track whether initial check is complete
        self.discard_initial_items = discard_initial_items
        
        # Load websites from configuration if config manager is provided
        if self.config_manager is None:
            self.config_manager = ConfigManager()
        
        self._load_websites_from_config()
        
        logging.info(f"Web Scraper Interface initialized with {len(self.websites)} websites (discard_initial_items={discard_initial_items})")

    def _load_websites_from_config(self):
        """Load website scrapers from configuration manager."""
        if self.config_manager:
            try:
                enabled_scrapers = self.config_manager.get_enabled_web_scrapers()
                for scraper_config in enabled_scrapers:
                    scraper_id = scraper_config.get("id")
                    scraper_url = scraper_config.get("url")
                    check_interval_hours = scraper_config.get("check_interval_hours", 1)
                    extractor_type = scraper_config.get("extractor_type", "generic")
                    css_selector = scraper_config.get("css_selector")
                    
                    if scraper_id and scraper_url:
                        self.add_website(
                            scraper_id,
                            scraper_url,
                            css_selector=css_selector,
                            extractor_type=extractor_type
                        )
                        # Set custom check interval for this website
                        self.website_intervals[scraper_id] = timedelta(hours=check_interval_hours)
                        logging.info(f"Loaded web scraper: {scraper_config.get('name', scraper_id)} ({scraper_id})")
                    else:
                        logging.warning(f"Invalid scraper configuration: missing id or url - {scraper_config}")
            except Exception as e:
                logging.error(f"Error loading scrapers from configuration: {e}")
        else:
            logging.warning("No configuration manager provided for web scrapers")
    
    def add_website(self, website_id: str, url: str, css_selector: str = None, 
                   extractor_type: str = "generic", custom_parser: Callable = None):
        """
        Add a website to monitor.
        
        Args:
            website_id: A unique identifier for this website
            url: The URL of the website to scrape
            css_selector: CSS selector to extract specific content
            extractor_type: Type of content to extract ("generic", "links", "twinsburg_links")
            custom_parser: Optional custom parsing function for special cases
        """
        self.websites[website_id] = {
            'url': url,
            'css_selector': css_selector,
            'extractor_type': extractor_type,
            'custom_parser': custom_parser
        }
        # Set default interval if not already set
        if website_id not in self.website_intervals:
            self.website_intervals[website_id] = self.check_interval
        
        self.last_check_time[website_id] = datetime.now(timezone.utc) - self.website_intervals[website_id]
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
    
    def _extract_rock_the_park_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract links and titles from the Rock the Park website.
        
        Args:
            soup: BeautifulSoup object of the parsed HTML
            
        Returns:
            List of dicts with link information
        """
        items = []
        
        try:
            # Find all links in the soup object
            links = soup.find_all('a')
            
            for link in links:
                href = link.get('href')
                title = link.get_text(strip=True)
                class_ = link.get('class')

                # Skip if href is missing
                if not href:
                    continue
                
                # Looking for specific Rock the Park links
                if not href.startswith('https://rocktheparkconcert.com/schedule/'):
                    continue

                # Example link format:
                '''
                    "<a href="https://rocktheparkconcert.com/schedule/august-16/">
				AUGUST 16: Cocktail Johnny			</a>"
                '''     
                           
                logging.debug(f"Processing link: {link}")
                link_type = "event"
                date = href.split('/')[-2]
                logging.debug(f"Extracted date: {date} from link: {href}")
                
                # Create a unique ID for this item
                item_id = f"{href}|{title}"
                
                items.append({
                    'url': href,
                    'title': title,
                    'id': item_id,
                    'type': link_type
                })
        
        except Exception as e:
            logging.error(f"Error extracting Rock the Park links: {e}")
        
        return items
    
    def _extract_twinsburg_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract links and titles from Twinsburg school website.
        
        Args:
            soup: BeautifulSoup object of the parsed HTML
            
        Returns:
            List of dicts with link information
        """
        items = []
        
        try:
            
            links = soup.find_all('a')
            
            for link in links:
                
                href = link.get('href')
                title = link.get_text(strip=True)
                class_ = link.get('class')
                # Skip if href, title, or class is missing
                if not href or not title or not class_:
                    continue
                # Ensure href is absolute URL
                if not href.startswith(('http://', 'https://')):
                    continue

                link_type = "unknown"

                # Are we dealing with a PDF link?
                if '.pdf' in href or 'pdf' in class_:  
                    link_type = "pdf"
                else:
                    link_type = "unknown"
                
                # Create a unique ID for this item
                item_id = f"{href}|{title}"

                
                items.append({
                    'url': href,
                    'title': title,
                    'id': item_id,
                    'type': link_type
                })
        
        except Exception as e:
            logging.error(f"Error extracting {link}:\n\n {e}")

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
            elif extractor_type == "twinsburg_links":
                items = self._extract_twinsburg_links(soup)
            elif extractor_type == "rock_the_park_links":
                items = self._extract_rock_the_park_links(soup)
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
                    #logging.info(f"Checking item: {item_id} on website '{website_id}'")
                    # Check if this is a new item
                    if item_id not in self.previous_items[website_id] and self.initial_check_complete[website_id]:
                        logging.info(f"New item found on website '{website_id}': {item_id}")
                        new_items.append(item)
                else:
                    logging.warning(f"Item on website '{website_id}' has no ID, skipping: {item}")
            
            # Update previous items
            self.previous_items[website_id] = current_items
            self.last_check_time[website_id] = datetime.now(timezone.utc)
            
            # Mark initial check as complete
            if not self.initial_check_complete[website_id]:
                self.initial_check_complete[website_id] = True
                logging.info(f"Initial check of website '{website_id}', discarding {len(items)} items")
            else:
                logging.info(f"Checked website '{website_id}', found {len(new_items)} new items")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching website '{website_id}': {e}")

        except Exception as e:
            logging.error(f"Unexpected error checking website '{website_id}': {e}")
        return new_items
    
    def download_pdf(self, url: str, destination: str) -> Optional[str]:
        """
        Download a PDF file from the given URL.
        
        Args:
            url: The URL of the PDF file
            destination: Local path to save the downloaded PDF
        Returns:
            Optional[str]: Path to the downloaded PDF file, or None if download failed
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Ensure the destination directory exists
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            with open(destination, 'wb') as f:
                f.write(response.content)
            
            logging.info(f"Downloaded PDF from {url} to {destination}")
            return destination
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading PDF from '{url}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error downloading PDF from '{url}': {e}")
        
        return None
    
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
            website_interval = self.website_intervals.get(website_id, self.check_interval)
            if now - self.last_check_time[website_id] >= website_interval:
                new_items = self.check_website(website_id)
                if new_items:
                    result[website_id] = new_items
                    # Send notification for each new item
                    for item in new_items:
                        # Format message based on item type
                        pdf_path = None
                        if 'title' in item and 'url' in item and 'type' in item:
                            # If .pdf in url, download and process it
                            if item['type'] == 'pdf':
                                logging.info(f"Downloading PDF from {item['url']}")
                                clean_filename = re.sub(r'[\\/*?:"<>|]', '', item['title'].strip())                    
                                pdf_path = f"/data/{website_id}/{clean_filename}.pdf"
                                self.download_pdf(item['url'], pdf_path)
                            # Format link items
                            logging.info(f"Found new {item['type']} on Site: {website_id.replace('_', ' ').title()}")
                            message = f"New {item['title']} on Site: {website_id.replace('_', ' ').title()}"
                        elif 'content' in item:
                            # Format text content
                            logging.info(f"Found new content on Site: {website_id.replace('_', ' ').title()} 📄")
                            message = f"📄 Content Update: {website_id.replace('_', ' ').title()} 📄\n\n"
                            content = item['content']
                            if len(content) > 300:
                                content = content[:297] + "..."
                            message += content
                        else:
                            # Generic format for other items
                            logging.info(f"Update detected on Site: {website_id.replace('_', ' ').title()} 🌐")
                            message = f"🌐 Update Detected: {website_id.replace('_', ' ').title()} 🌐\n\n"
                            message += f"New content has been detected on this website."
                            
                        logging.info(f"Sending message for {website_id}: {message}")
                        # Send message
                        logging.info(message)
                        message_callback(message, channel, destination, pdf_path, item.get('url', None))

                        if log_callback:
                            log_callback(f"web-scrape-{website_id}")
        
        return result
