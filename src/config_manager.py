import json
import os
import logging
from typing import Dict, List, Any

class ConfigManager:
    """Manages configuration for the mesh monitor application."""
    
    def __init__(self, config_file_path: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file_path: Path to the configuration file. 
                            Defaults to config.json in the current directory.
        """
        if config_file_path is None:
            # Look for config file in the parent directory of src
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            config_file_path = os.path.join(parent_dir, "config.json")
        
        self.config_file_path = config_file_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from the JSON file."""
        try:
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logging.info(f"Configuration loaded from {self.config_file_path}")
                return config
            else:
                logging.warning(f"Configuration file not found at {self.config_file_path}, using defaults")
                return self._get_default_config()
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            logging.info("Using default configuration")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if no config file is found."""
        return {
            "rss_feeds": [
                {
                    "id": "twinsburg_calendar",
                    "name": "Twinsburg Calendar",
                    "url": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=58&CID=All-calendar.xml",
                    "enabled": True,
                    "check_interval_hours": 1
                },
                {
                    "id": "twinsburg_news", 
                    "name": "Twinsburg News",
                    "url": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=65&CID=All-0",
                    "enabled": True,
                    "check_interval_hours": 1
                }
            ],
            "web_scrapers": []
        }
    
    def get_rss_feeds(self) -> List[Dict[str, Any]]:
        """Get list of configured RSS feeds, including environment variable feeds."""
        feeds = self.config.get("rss_feeds", []).copy()
        
        # Add feeds from environment variables for backward compatibility
        env_feeds = self._get_env_rss_feeds()
        feeds.extend(env_feeds)
        
        return feeds
    
    def _get_env_rss_feeds(self) -> List[Dict[str, Any]]:
        """Get RSS feeds from environment variables."""
        import os
        feeds = []
        
        # Look for environment variables in format RSS_FEED_<NAME>=<URL>
        for key, value in os.environ.items():
            if key.startswith('RSS_FEED_') and value:
                feed_name = key[9:].lower()  # Remove RSS_FEED_ prefix
                feed_id = f"env_{feed_name}"
                
                # Check if this feed already exists in config
                existing_feed_ids = [f.get("id") for f in self.config.get("rss_feeds", [])]
                if feed_id not in existing_feed_ids:
                    feeds.append({
                        "id": feed_id,
                        "name": feed_name.replace('_', ' ').title(),
                        "url": value,
                        "enabled": True,
                        "check_interval_hours": 1
                    })
                    logging.info(f"Added RSS feed from environment variable: {key}")
        
        return feeds
    
    def get_enabled_rss_feeds(self) -> List[Dict[str, Any]]:
        """Get list of enabled RSS feeds only."""
        return [feed for feed in self.get_rss_feeds() if feed.get("enabled", True)]
    
    def get_web_scrapers(self) -> List[Dict[str, Any]]:
        """Get list of configured web scrapers."""
        return self.config.get("web_scrapers", [])
    
    def get_enabled_web_scrapers(self) -> List[Dict[str, Any]]:
        """Get list of enabled web scrapers only."""
        return [scraper for scraper in self.get_web_scrapers() if scraper.get("enabled", True)]
    
    def add_rss_feed(self, feed_id: str, name: str, url: str, enabled: bool = True, check_interval_hours: int = 1):
        """
        Add a new RSS feed to the configuration.
        
        Args:
            feed_id: Unique identifier for the feed
            name: Human-readable name for the feed
            url: RSS feed URL
            enabled: Whether the feed is enabled
            check_interval_hours: How often to check the feed (in hours)
        """
        new_feed = {
            "id": feed_id,
            "name": name,
            "url": url,
            "enabled": enabled,
            "check_interval_hours": check_interval_hours
        }
        
        # Check if feed already exists
        feeds = self.config.get("rss_feeds", [])
        for i, feed in enumerate(feeds):
            if feed.get("id") == feed_id:
                feeds[i] = new_feed
                logging.info(f"Updated existing RSS feed: {feed_id}")
                self._save_config()
                return
        
        # Add new feed
        feeds.append(new_feed)
        self.config["rss_feeds"] = feeds
        logging.info(f"Added new RSS feed: {feed_id}")
        self._save_config()
    
    def remove_rss_feed(self, feed_id: str):
        """Remove an RSS feed from the configuration."""
        feeds = self.config.get("rss_feeds", [])
        self.config["rss_feeds"] = [feed for feed in feeds if feed.get("id") != feed_id]
        logging.info(f"Removed RSS feed: {feed_id}")
        self._save_config()
    
    def _save_config(self):
        """Save the current configuration to the file."""
        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logging.info(f"Configuration saved to {self.config_file_path}")
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
    
    def reload_config(self):
        """Reload configuration from the file."""
        self.config = self._load_config()
        logging.info("Configuration reloaded")
