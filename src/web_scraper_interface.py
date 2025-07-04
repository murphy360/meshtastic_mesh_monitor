import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Callable, Any, Optional
import time

class WebScraperInterface:
    """Interface for scraping websites and monitoring for changes."""
    
    def __init__(self):
        """Initialize the web scraper interface."""
        self.websites = {}  # Dict to store website configurations
        self.last_check_time = {}
        self.check_interval = timedelta(hours=1)  # Check websites every hour by default
        self.previous_content = {}  # Store previous content to detect changes
        
        logging.info("Web Scraper Interface initialized")
    
    def add_website(self, website_id: str, url: str, css_selector: str = None):
        """
        Add a website to monitor.
        
        Args:
            website_id: A unique identifier for this website
            url: The URL of the website to scrape
            css_selector: Optional CSS selector to extract specific content
        """
        self.websites[website_id] = {
            'url': url,
            'css_selector': css_selector
        }
        self.last_check_time[website_id] = datetime.now(timezone.utc) - self.check_interval
        self.previous_content[website_id] = None
        logging.info(f"Added website to monitor: {website_id} - {url}")
    
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
            del self.previous_content[website_id]
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
    
    def scrape_websites_if_needed(self, 
                                  message_callback: Callable[[str, int, str], None],
                                  channel: int,
                                  destination: str,
                                  log_callback: Callable[[str], None] = None) -> Dict[str, Any]:
        """
        Check all websites for changes if the check interval has elapsed.
        
        This function checks each website for changes, but only if the
        specified check interval has elapsed since the last check. When changes
        are detected, a notification is sent using the provided callback.
        
        Args:
            message_callback: Function used to send messages to the mesh network
                             Should accept (message, channel, destination) parameters
            channel: Channel number for notifications
            destination: Destination ID for messages (usually "^all")
            log_callback: Optional function to log message types that were sent
                         Should accept a single string parameter
            
        Returns:
            Dict mapping website IDs to any detected changes
        """
        
        now = datetime.now(timezone.utc)
        result = {}
        
        for website_id, config in self.websites.items():
            logging.info(f"Checking website: {website_id} - {config['url']}")
            # Only check if interval has elapsed
            if now - self.last_check_time[website_id] >= self.check_interval:
                try:
                    url = config['url']
                    css_selector = config.get('css_selector')
                    
                    # Fetch the webpage
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    
                    # Parse the HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract content based on selector if provided
                    if css_selector:
                        content = soup.select(css_selector)
                        content_text = '\n'.join([element.get_text(strip=True) for element in content])
                    else:
                        # Use the whole body if no selector
                        content_text = soup.body.get_text(strip=True)
                    
                    # Check for changes
                    if self.previous_content[website_id] is not None and content_text != self.previous_content[website_id]:
                        logging.info(f"Change detected on website: {website_id}")
                        result[website_id] = {
                            'url': url,
                            'changed': True
                        }
                        
                        # Send notification
                        message = f"🌐 Website Change Detected 🌐\n\n"
                        message += f"Website: {website_id.replace('_', ' ').title()}\n"
                        message += f"URL: {url}\n\n"
                        message += "The content of this website has changed since the last check."
                        
                        message_callback(message, channel, destination)
                        
                        if log_callback:
                            log_callback(f"website-change-{website_id}")
                    
                    # Update the stored content
                    self.previous_content[website_id] = content_text
                    self.last_check_time[website_id] = now
                    
                except Exception as e:
                    logging.error(f"Error checking website {website_id}: {e}")
        
        return result
