"""
Base interface classes for standardizing external service integrations.

This module provides abstract base classes that define common patterns
for interfaces that interact with external services like APIs, feeds, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
#from config_manager import ConfigManager
import logging
import json
import time
import sys
import os
import requests



class BaseInterface(ABC):
    """
    Abstract base class for all external service interfaces.
    
    Provides common functionality like caching, error handling,
    and configuration management that all interfaces can inherit.
    """
    
    def __init__(self, config_manager=None, cache_duration_seconds: int = 3600):
        """
        Initialize the base interface.
        
        Args:
            config_manager: ConfigManager instance for loading configuration
            cache_duration_seconds: Default cache duration in seconds
        """
        self.config_manager = config_manager
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration = timedelta(seconds=cache_duration_seconds)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize config manager if not provided
        if self.config_manager is None:
            self._initialize_config_manager()
    
    def _initialize_config_manager(self):
        """Initialize config manager - can be overridden by subclasses."""

        # print all directories in sys.path
        for path in sys.path:
            print(f"Path: {path}")

        try:
            self.config_manager = ConfigManager()
        except Exception as e:
            self.logger.warning(f"Failed to initialize ConfigManager: {e}")
            self.config_manager = None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache:
            return False
        if cache_key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[cache_key]
    
    def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Retrieve data from cache if valid."""
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"Cache hit for key: {cache_key}")
            return self.cache[cache_key]
        return None
    
    def _cache_data(self, cache_key: str, data: Any, duration_seconds: Optional[int] = None) -> None:
        """Store data in cache with expiry."""
        if duration_seconds is None:
            duration_seconds = self.cache_duration.total_seconds()
        
        self.cache[cache_key] = data
        self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=duration_seconds)
        self.logger.debug(f"Cached data for key: {cache_key} (expires in {duration_seconds}s)")
    
    def _clear_cache(self, cache_key: Optional[str] = None) -> None:
        """Clear cache data."""
        if cache_key is None:
            self.cache.clear()
            self.cache_expiry.clear()
            self.logger.debug("Cleared all cache")
        else:
            self.cache.pop(cache_key, None)
            self.cache_expiry.pop(cache_key, None)
            self.logger.debug(f"Cleared cache for key: {cache_key}")
    
    def _handle_api_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Standard error handling for API calls."""
        self.logger.error(f"Error in {context}: {str(error)}")
        return {
            "success": False,
            "error": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the interface can connect to its service."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the interface."""
        pass


class PollingInterface(BaseInterface):
    """
    Base class for interfaces that poll external services at regular intervals.
    
    Extends BaseInterface with polling-specific functionality like
    interval management and change detection.
    """
    
    def __init__(self, config_manager=None, cache_duration_seconds: int = 3600, 
                 default_poll_interval_seconds: int = 3600):
        """
        Initialize the polling interface.
        
        Args:
            config_manager: ConfigManager instance
            cache_duration_seconds: Cache duration in seconds
            default_poll_interval_seconds: Default polling interval in seconds
        """
        super().__init__(config_manager, cache_duration_seconds)
        self.default_poll_interval = timedelta(seconds=default_poll_interval_seconds)
        self.last_poll_time: Dict[str, datetime] = {}
        self.poll_intervals: Dict[str, timedelta] = {}
        self.previous_data: Dict[str, Any] = {}
    
    def _should_poll(self, poll_key: str) -> bool:
        """Check if it's time to poll for the given key."""
        if poll_key not in self.last_poll_time:
            return True
        
        interval = self.poll_intervals.get(poll_key, self.default_poll_interval)
        # Handle timezone-aware vs naive datetime comparison
        last_poll = self.last_poll_time[poll_key]
        now = datetime.now()
        
        # Make both timezone-aware or both timezone-naive for comparison
        if last_poll.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        elif last_poll.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        
        return now - last_poll >= interval
    
    def _update_poll_time(self, poll_key: str) -> None:
        """Update the last poll time for the given key."""
        # Use the same timezone as existing entries if they exist
        if poll_key in self.last_poll_time and self.last_poll_time[poll_key].tzinfo is not None:
            self.last_poll_time[poll_key] = datetime.now(timezone.utc)
        else:
            self.last_poll_time[poll_key] = datetime.now()
    
    def _set_poll_interval(self, poll_key: str, interval_seconds: int) -> None:
        """Set a custom poll interval for a specific key."""
        self.poll_intervals[poll_key] = timedelta(seconds=interval_seconds)
    
    def _detect_changes(self, poll_key: str, current_data: Any) -> Dict[str, Any]:
        """
        Detect changes between current and previous data.
        
        Returns:
            Dictionary with change information
        """
        if poll_key not in self.previous_data:
            self.previous_data[poll_key] = current_data
            return {
                "has_changes": True,
                "change_type": "initial",
                "previous": None,
                "current": current_data
            }
        
        previous = self.previous_data[poll_key]
        has_changes = previous != current_data
        
        if has_changes:
            self.previous_data[poll_key] = current_data
        
        return {
            "has_changes": has_changes,
            "change_type": "update" if has_changes else "none",
            "previous": previous if has_changes else None,
            "current": current_data
        }
    
    @abstractmethod
    def poll_for_updates(self) -> Dict[str, Any]:
        """Poll the service for updates."""
        pass


class APIInterface(BaseInterface):
    """
    Base class for REST API interfaces.
    
    Provides common functionality for making HTTP requests,
    handling responses, and managing rate limits.
    """
    
    def __init__(self, base_url: str, config_manager=None, cache_duration_seconds: int = 3600,
                 default_headers: Optional[Dict[str, str]] = None, rate_limit_delay: float = 0.1):
        """
        Initialize the API interface.
        
        Args:
            base_url: Base URL for the API
            config_manager: ConfigManager instance
            cache_duration_seconds: Cache duration in seconds
            default_headers: Default headers for requests
            rate_limit_delay: Minimum delay between requests in seconds
        """
        super().__init__(config_manager, cache_duration_seconds)
        self.base_url = base_url.rstrip('/')
        self.default_headers = default_headers or {}
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = None
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, method: str = "GET", 
                     headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, Any]] = None,
                     json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.
        
        Args:
            endpoint: API endpoint (will be appended to base_url)
            method: HTTP method
            headers: Request headers (merged with default_headers)
            params: URL parameters
            json_data: JSON data for POST/PUT requests
            
        Returns:
            Dictionary containing response data or error information
        """
        try:
            if requests is None:
                raise ImportError("requests library is not available")
            
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            # Prepare URL
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            # Prepare headers
            request_headers = self.default_headers.copy()
            if headers:
                request_headers.update(headers)
            
            # Make request
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                json=json_data,
                timeout=30
            )
            
            # Handle response
            response.raise_for_status()
            
            return {
                "success": True,
                "data": response.json() if response.content else {},
                "status_code": response.status_code,
                "headers": dict(response.headers)
            }
            
        except Exception as e:
            return self._handle_api_error(e, f"API request to {endpoint}")
    
    def test_connection(self) -> bool:
        """Test API connection - should be implemented by subclasses."""
        try:
            response = self._make_request("")
            return response.get("success", False)
        except Exception:
            return False


class FeedInterface(PollingInterface):
    """
    Base class for feed-based interfaces (RSS, Atom, etc.).
    
    Combines polling functionality with feed-specific features
    like item tracking and feed management.
    """
    
    def __init__(self, config_manager=None, cache_duration_seconds: int = 3600,
                 default_poll_interval_seconds: int = 3600, discard_initial_items: bool = True):
        """
        Initialize the feed interface.
        
        Args:
            config_manager: ConfigManager instance
            cache_duration_seconds: Cache duration in seconds
            default_poll_interval_seconds: Default polling interval in seconds
            discard_initial_items: Whether to discard items found on first check
        """
        super().__init__(config_manager, cache_duration_seconds, default_poll_interval_seconds)
        self.feeds: Dict[str, str] = {}  # feed_id -> feed_url
        self.initial_check_complete: Dict[str, bool] = {}
        self.discard_initial_items = discard_initial_items
    
    def add_feed(self, feed_id: str, feed_url: str, poll_interval_seconds: Optional[int] = None) -> None:
        """Add a feed to monitor."""
        self.feeds[feed_id] = feed_url
        if poll_interval_seconds is not None:
            self._set_poll_interval(feed_id, poll_interval_seconds)
        self.initial_check_complete[feed_id] = False
        self.logger.info(f"Added feed: {feed_id} -> {feed_url}")
    
    def remove_feed(self, feed_id: str) -> bool:
        """Remove a feed from monitoring."""
        if feed_id in self.feeds:
            del self.feeds[feed_id]
            self.initial_check_complete.pop(feed_id, None)
            self.last_poll_time.pop(feed_id, None)
            self.poll_intervals.pop(feed_id, None)
            self.previous_data.pop(feed_id, None)
            self._clear_cache(feed_id)
            self.logger.info(f"Removed feed: {feed_id}")
            return True
        return False
    
    def get_feed_status(self) -> Dict[str, Any]:
        """Get status of all feeds."""
        return {
            "total_feeds": len(self.feeds),
            "feeds": {
                feed_id: {
                    "url": feed_url,
                    "last_poll": self.last_poll_time.get(feed_id),
                    "initial_check_complete": self.initial_check_complete.get(feed_id, False),
                    "poll_interval": self.poll_intervals.get(feed_id, self.default_poll_interval).total_seconds()
                }
                for feed_id, feed_url in self.feeds.items()
            }
        }
    
    @abstractmethod
    def parse_feed(self, feed_content: str) -> List[Dict[str, Any]]:
        """Parse feed content and return list of items."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the feed interface."""
        return {
            "interface_type": self.__class__.__name__,
            "feed_status": self.get_feed_status(),
            "cache_entries": len(self.cache),
            "last_poll_times": self.last_poll_time
        }
