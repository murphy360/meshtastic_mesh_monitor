import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
import time
import re
import hashlib

class WebScraperInterface:
    """Interface for scraping and monitoring web pages for changes."""
    
    def __init__(self):
        """Initialize the web scraper interface."""
        self.scrapers = {}
        self.last_check_time = {}
        self.check_interval = timedelta(hours=6)  # Check pages every 6 hours by default
        self.previous_content = {}  # Store previous content hashes to detect changes
        
        # Add the Twinsburg school board page by default
        self.add_scraper(
            "twinsburg_school_board",
            "https://www.twinsburg.k12.oh.us/agendasandminutes.aspx",
            self._scrape_twinsburg_school_board
        )
        
        logging.info(f"Web Scraper Interface initialized with {len(self.scrapers)} scrapers")
    
    def add_scraper(self, scraper_id: str, url: str, scraper_function: Callable[[str], List[Dict]]):
        """
        Add a new web page to monitor.
        
        Args:
            scraper_id: A unique identifier for this scraper
            url: The URL of the page to scrape
            scraper_function: Function that takes HTML content and returns extracted items
        """
        self.scrapers[scraper_id] = {
            "url": url,
            "function": scraper_function
        }
        self.last_check_time[scraper_id] = datetime.now(timezone.utc) - self.check_interval
        self.previous_content[scraper_id] = {}
        logging.info(f"Added web scraper: {scraper_id} - {url}")
    
    def remove_scraper(self, scraper_id: str) -> bool:
        """
        Remove a web scraper from monitoring.
        
        Args:
            scraper_id: The identifier of the scraper to remove
            
        Returns:
            bool: True if the scraper was removed, False if it wasn't found
        """
        if scraper_id in self.scrapers:
            del self.scrapers[scraper_id]
            del self.last_check_time[scraper_id]
            del self.previous_content[scraper_id]
            logging.info(f"Removed web scraper: {scraper_id}")
            return True
        return False
    
    def set_check_interval(self, hours: float):
        """
        Set how often to check for web page changes.
        
        Args:
            hours: Number of hours between web page checks
        """
        self.check_interval = timedelta(hours=hours)
        logging.info(f"Web scraper check interval set to {hours} hours")
    
    def _scrape_twinsburg_school_board(self, html_content: str) -> List[Dict]:
        """
        Scrape the Twinsburg school board agendas and minutes page.
        
        Args:
            html_content: The HTML content of the page
            
        Returns:
            List[Dict]: List of extracted items (agendas and minutes)
        """
        items = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the main content area
            main_content = soup.find('div', {'class': 'main-content'})
            if not main_content:
                logging.error("Could not find main content area")
                return items
            
            # Extract the year headings and their content
            year_headings = main_content.find_all(['h2', 'h3'])
            
            current_year = None
            for heading in year_headings:
                # Check if it's a year heading
                if re.match(r'^\d{4}$', heading.get_text().strip()):
                    current_year = heading.get_text().strip()
                    continue
                
                if not current_year:
                    continue
                
                # Get the meeting date from the heading
                meeting_date = heading.get_text().strip()
                
                # Find all links after this heading and before the next heading
                next_element = heading.next_sibling
                links = []
                
                while next_element and not (next_element.name == 'h2' or next_element.name == 'h3'):
                    if hasattr(next_element, 'find_all'):
                        links.extend(next_element.find_all('a'))
                    next_element = next_element.next_sibling
                
                # Process each link (agenda or minutes)
                for link in links:
                    link_text = link.get_text().strip()
                    link_url = link.get('href', '')
                    
                    # Make sure URL is absolute
                    if link_url and not link_url.startswith('http'):
                        if link_url.startswith('/'):
                            link_url = f"https://www.twinsburg.k12.oh.us{link_url}"
                        else:
                            link_url = f"https://www.twinsburg.k12.oh.us/{link_url}"
                    
                    if link_url:
                        item_type = "Unknown"
                        if "agenda" in link_text.lower():
                            item_type = "Agenda"
                        elif "minute" in link_text.lower():
                            item_type = "Minutes"
                        
                        # Create a unique ID for this item
                        item_id = hashlib.md5(f"{meeting_date}_{link_text}_{link_url}".encode()).hexdigest()
                        
                        items.append({
                            "id": item_id,
                            "year": current_year,
                            "date": meeting_date,
                            "type": item_type,
                            "title": link_text,
                            "url": link_url
                        })
            
            logging.info(f"Scraped {len(items)} items from Twinsburg school board page")
            
        except Exception as e:
            logging.error(f"Error scraping Twinsburg school board page: {e}")
        
        return items
    
    def check_scraper(self, scraper_id: str) -> List[Dict]:
        """
        Check a specific web page for new content.
        
        Args:
            scraper_id: The identifier of the scraper to check
            
        Returns:
            List[Dict]: List of new items
        """
        if scraper_id not in self.scrapers:
            logging.warning(f"Scraper ID '{scraper_id}' not found")
            return []
        
        scraper_info = self.scrapers[scraper_id]
        url = scraper_info["url"]
        scraper_function = scraper_info["function"]
        new_items = []
        
        try:
            # Use a desktop browser user agent to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            items = scraper_function(response.text)
            current_items = {}
            
            # Process each item and find new ones
            for item in items:
                if "id" in item:
                    item_id = item["id"]
                    current_items[item_id] = item
                    
                    if item_id not in self.previous_content[scraper_id]:
                        new_items.append(item)
            
            # Update previous items
            self.previous_content[scraper_id] = current_items
            self.last_check_time[scraper_id] = datetime.now(timezone.utc)
            
            logging.info(f"Checked scraper '{scraper_id}', found {len(new_items)} new items")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching page for scraper '{scraper_id}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error checking scraper '{scraper_id}': {e}")
        
        return new_items
    
    def check_scrapers_if_needed(self, 
                                message_callback: Callable[[str, int, str], None],
                                channel: int,
                                destination: str,
                                log_callback: Callable[[str], None] = None) -> Dict[str, List[Dict]]:
        """
        Check all web scrapers for new content if the check interval has elapsed.
        
        This function checks each web page for new content, but only if the
        specified check interval has elapsed since the last check. When new
        items are found, they are sent to the specified channel using the
        provided callback.
        
        Args:
            message_callback: Function used to send messages to the mesh network
                            Should accept (message, channel, destination) parameters
            channel: Channel number for notifications
            destination: Destination ID for messages (usually "^all")
            log_callback: Optional function to log message types that were sent
                        Should accept a single string parameter
            
        Returns:
            Dict mapping scraper IDs to lists of new items
        """
        now = datetime.now(timezone.utc)
        result = {}
        
        for scraper_id in self.scrapers:
            # Only check if interval has elapsed
            if now - self.last_check_time[scraper_id] >= self.check_interval:
                new_items = self.check_scraper(scraper_id)
                
                if new_items:
                    result[scraper_id] = new_items
                    
                    # Send notification for each new item
                    for item in new_items:
                        # Create message with details
                        message = self.format_item_summary(scraper_id, item)
                        
                        # Send message
                        message_callback(message, channel, destination)
                        
                        if log_callback:
                            log_callback(f"web-scraper-{scraper_id}")
        
        return result
    
    def format_item_summary(self, scraper_id: str, item: Dict) -> str:
        """
        Format a scraped item into a readable summary string.
        
        Args:
            scraper_id: The ID of the scraper that found this item
            item: The scraped item to format
            
        Returns:
            str: A formatted summary string
        """
        if scraper_id == "twinsburg_school_board":
            summary = "📄 Twinsburg School Board Update 📄\n\n"
            
            if "type" in item and "date" in item:
                summary += f"New {item['type']} for {item['date']}\n\n"
            
            if "title" in item:
                summary += f"{item['title']}\n\n"
            
            if "url" in item:
                summary += f"Link: {item['url']}"
            
            return summary
        else:
            # Generic format for other scrapers
            summary = f"🔍 {scraper_id.replace('_', ' ').title()} Update 🔍\n\n"
            
            for key, value in item.items():
                if key != "id" and value:  # Skip the ID field and empty values
                    summary += f"{key.title()}: {value}\n"
            
            return summary
