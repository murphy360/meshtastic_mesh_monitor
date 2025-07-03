import requests
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import time

class WeatherGovInterface:
    """Interface for accessing the National Weather Service (weather.gov) API."""
    
    def __init__(self, user_agent: str = "MeshtasticMeshMonitor/1.0"):
        """
        Initialize the weather.gov interface.
        
        Args:
            user_agent: Identifier for API requests (weather.gov requires a unique identifier)
        """
        self.base_url = "https://api.weather.gov"
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/geo+json"
        }
        self.cache = {}
        self.cache_expiry = {}
        self.default_cache_seconds = 3600  # 1 hour default cache
        self.previous_alerts: Dict[str, Any] = {}  # Store previous alerts to detect changes
        self.new_alerts: Dict[str, Any] = {}
        self.updated_alerts: Dict[str, Any] = {}    
        self.expired_alerts: Dict[str, Any] = {}  # Store expired alerts from previous run
        
    def get_forecast(self, latitude: float, longitude: float, detailed: bool = False) -> Dict[str, Any]:
        """
        Get weather forecast for a specific location.
        
        Args:
            latitude: The latitude coordinate
            longitude: The longitude coordinate
            detailed: If True, returns hourly forecast instead of daily
            
        Returns:
            Dictionary containing forecast data
        """
        cache_key = f"forecast_{latitude}_{longitude}_{detailed}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logging.info(f"Using cached forecast data for {latitude}, {longitude}")
            return cached_result
            
        try:
            # First get the forecast office and grid coordinates
            points_url = f"{self.base_url}/points/{latitude},{longitude}"
            response = requests.get(points_url, headers=self.headers)
            response.raise_for_status()
            
            metadata = response.json()
            if detailed:
                forecast_url = metadata['properties']['forecastHourly']
            else:
                forecast_url = metadata['properties']['forecast']
                
            # Now get the actual forecast
            response = requests.get(forecast_url, headers=self.headers)
            response.raise_for_status()
            
            forecast_data = response.json()
            self._add_to_cache(cache_key, forecast_data)
            logging.info(f"Cached forecast data for {latitude}, {longitude} - {forecast_data}")
            return forecast_data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching forecast: {e}")
            return {"error": str(e)}
    
    def update_alerts(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Get active weather alerts for a specific location.
        
        Args:
            latitude: The latitude coordinate
            longitude: The longitude coordinate
            
        Returns:
            Dictionary containing alert data
        """   
        try:
            # First get the county/zone for the location
            points_url = f"{self.base_url}/points/{latitude},{longitude}"
            response = requests.get(points_url, headers=self.headers)
            response.raise_for_status()
            
            metadata = response.json()
            county = metadata['properties']['county']
            zone = metadata['properties']['forecastZone']
            logging.info(f"Found county: {county}, zone: {zone} for coordinates {latitude}, {longitude}")
            cache_key = f"alerts_{zone.split('/')[-1]}"
            alerts_data = self._get_from_cache(cache_key, max_age_seconds=900)  # 15 minute cache for alerts
            if not alerts_data:
                logging.info(f"No cached alerts data for zone {zone}, fetching new data")
                # Now get the alerts for this zone
                alerts_url = f"{self.base_url}/alerts/active?zone={zone.split('/')[-1]}"
                response = requests.get(alerts_url, headers=self.headers)
                response.raise_for_status()
            
                alerts_data = response.json()
                self._add_to_cache(cache_key, alerts_data, expiry_seconds=900)  # 15 minute cache
                logging.info(f"Cached alerts data for zone {zone} - {alerts_data}")
            
            logging.info(f"Fetched alerts data for zone {zone}: {alerts_data}")

            # Update Expired Alerts
            current_alerts = {alert['id']: alert for alert in alerts_data.get('features', [])}
            # Log each alert ID for debugging
            for alert_id in current_alerts.keys():
                logging.debug(f"Current alert ID: {alert_id}")
                logging.debug(f"Alert details: {current_alerts[alert_id]}")

            self.expired_alerts = {k: v for k, v in self.previous_alerts.items() if k not in current_alerts}

            # Update new alerts
            self.new_alerts = {k: v for k, v in current_alerts.items() if k not in self.previous_alerts}

            # Update updated alerts
            self.updated_alerts = {k: v for k, v in current_alerts.items() if k in self.previous_alerts and v != self.previous_alerts[k]}

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching alerts: {e}")
            return {"error": str(e)}

    def clear_alerts(self) -> None:
        """
        Clear the previous alerts data.
        
        This is useful to reset the state before fetching new alerts.
        """
        self.new_alerts = {}
        self.updated_alerts = {}
        self.expired_alerts = {}

    def get_current_conditions(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Get current weather conditions for a specific location.
        
        Args:
            latitude: The latitude coordinate
            longitude: The longitude coordinate
            
        Returns:
            Dictionary containing current conditions data
        """
        cache_key = f"conditions_{latitude}_{longitude}"
        cached_result = self._get_from_cache(cache_key, max_age_seconds=1800)  # 30 minute cache
        if cached_result:
            return cached_result
            
        try:
            # First get the stations for this location
            points_url = f"{self.base_url}/points/{latitude},{longitude}"
            response = requests.get(points_url, headers=self.headers)
            response.raise_for_status()
            
            metadata = response.json()
            stations_url = metadata['properties']['observationStations']
            
            # Get the list of stations
            response = requests.get(stations_url, headers=self.headers)
            response.raise_for_status()
            
            stations_data = response.json()
            if len(stations_data['features']) == 0:
                return {"error": "No observation stations found for this location"}
                
            # Get observations from the first station
            station_id = stations_data['features'][0]['properties']['stationIdentifier']
            observations_url = f"{self.base_url}/stations/{station_id}/observations/latest"
            
            response = requests.get(observations_url, headers=self.headers)
            response.raise_for_status()
            
            conditions_data = response.json()
            self._add_to_cache(cache_key, conditions_data, expiry_seconds=1800)  # 30 minute cache
            return conditions_data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching current conditions: {e}")
            return {"error": str(e)}
    
    def format_simple_forecast(self, forecast_data: Dict[str, Any]) -> str:
        """
        Format forecast data into a simple human-readable string.
        
        Args:
            forecast_data: The forecast data from get_forecast()
            
        Returns:
            A formatted string with the forecast
        """
        if "error" in forecast_data:
            return f"Weather forecast unavailable: {forecast_data['error']}"
            
        try:
            periods = forecast_data['properties']['periods']
            logging.info(f"Periods: {periods}")
            if not periods:
                return "No forecast data available"
                
            today = periods[0]
            tonight = periods[1] if len(periods) > 1 else None
            tomorrow = periods[2] if len(periods) > 2 else None
            
            result = f"{today['name']}: {today['shortForecast']}, {today['temperature']}{today['temperatureUnit']}. "
            result += f"{today['detailedForecast']}\n"
            
            if tonight:
                result += f"{tonight['name']}: {tonight['shortForecast']}, {tonight['temperature']}{tonight['temperatureUnit']}.\n"
                
            if tomorrow:
                result += f"{tomorrow['name']}: {tomorrow['shortForecast']}, {tomorrow['temperature']}{tomorrow['temperatureUnit']}."
                
            return result
            
        except (KeyError, IndexError) as e:
            logging.error(f"Error formatting forecast: {e}")
            return "Error formatting weather forecast"
    
    def format_alerts(self, alerts_data: Dict[str, Any]) -> str:
        """
        Format alerts data into a human-readable string.
        
        Args:
            alerts_data: The alerts data from get_alerts()
            
        Returns:
            A formatted string with the active alerts
        """
        if "error" in alerts_data:
            return f"Weather alerts unavailable: {alerts_data['error']}"
            
        try:
            features = alerts_data.get('features', [])
            if not features:
                return "No active weather alerts"
                
            result = "ACTIVE WEATHER ALERTS:\n"
            for i, feature in enumerate(features, 1):
                props = feature['properties']
                result += f"{i}. {props['event']} - {props['headline']}\n"
                if i == 3:  # Limit to 3 alerts to keep message size reasonable
                    if len(features) > 3:
                        result += f"...and {len(features) - 3} more alerts."
                    break
                    
            return result
            
        except (KeyError, IndexError) as e:
            logging.error(f"Error formatting alerts: {e}")
            return "Error formatting weather alerts"
    
    def format_current_conditions(self, conditions_data: Dict[str, Any]) -> str:
        """
        Format current conditions data into a human-readable string.
        
        Args:
            conditions_data: The conditions data from get_current_conditions()
            
        Returns:
            A formatted string with the current conditions
        """
        if "error" in conditions_data:
            return f"Current conditions unavailable: {conditions_data['error']}"
            
        try:
            props = conditions_data['properties']
            
            # Extract the values safely with defaults
            temp_c = props.get('temperature', {}).get('value', 'N/A')
            temp_f = round((temp_c * 9/5) + 32, 1) if isinstance(temp_c, (int, float)) else 'N/A'
            
            wind_speed = props.get('windSpeed', {}).get('value', 'N/A')
            wind_direction = props.get('windDirection', {}).get('value', 'N/A')
            
            humidity = props.get('relativeHumidity', {}).get('value', 'N/A')
            if isinstance(humidity, (int, float)):
                humidity = f"{round(humidity)}%"
                
            description = props.get('textDescription', 'No description available')
            
            station_name = "Unknown Station"
            if 'station' in conditions_data and isinstance(conditions_data['station'], str):
                station_name = conditions_data['station'].split('/')[-1]
                
            result = f"Current conditions at {station_name}: {description}, "
            result += f"Temperature: {temp_f}°F ({temp_c}°C), "
            result += f"Humidity: {humidity}, "
            result += f"Wind: {wind_speed} mph at {wind_direction}°"
            
            return result
            
        except (KeyError, TypeError) as e:
            logging.error(f"Error formatting current conditions: {e}")
            return "Error formatting current weather conditions"
    
    def get_weather_summary(self, latitude: float, longitude: float) -> str:
        """
        Get a complete weather summary including current conditions, alerts and forecast.
        
        Args:
            latitude: The latitude coordinate
            longitude: The longitude coordinate
            
        Returns:
            A formatted string with the weather summary
        """
        # Get current conditions
        conditions = self.get_current_conditions(latitude, longitude)
        conditions_str = self.format_current_conditions(conditions)
        
        # Get alerts
        alerts = self.get_alerts(latitude, longitude)
        alerts_str = self.format_alerts(alerts)
        
        # Get forecast
        forecast = self.get_forecast(latitude, longitude)
        forecast_str = self.format_simple_forecast(forecast)
        
        # Combine into summary
        summary = f"{conditions_str}\n\n"
        
        # Only include alerts section if there are actual alerts
        if "No active weather alerts" not in alerts_str:
            summary += f"{alerts_str}\n\n"
            
        summary += f"{forecast_str}"
        
        return summary
    
    def _add_to_cache(self, key: str, data: Any, expiry_seconds: int = None) -> None:
        """Add data to the cache with expiration time"""
        if expiry_seconds is None:
            expiry_seconds = self.default_cache_seconds
            
        self.cache[key] = data
        self.cache_expiry[key] = time.time() + expiry_seconds
    
    def _get_from_cache(self, key: str, max_age_seconds: int = None) -> Optional[Any]:
        """Get data from cache if it exists and hasn't expired"""
        if key in self.cache and key in self.cache_expiry:
            if max_age_seconds is not None:
                # Use the provided max age
                if time.time() < self.cache_expiry[key]:
                    return self.cache[key]
            else:
                # Use the expiry time set when the item was cached
                if time.time() < self.cache_expiry[key]:
                    return self.cache[key]
        return None
