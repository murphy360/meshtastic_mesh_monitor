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
        self.current_alerts: Dict[str, Any] = {}
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

        # First get the county/zone for the location
        points_url = f"{self.base_url}/points/{latitude},{longitude}"
        response = requests.get(points_url, headers=self.headers)
        response.raise_for_status()
        
        metadata = response.json()

        zone = metadata['properties']['forecastZone']
        cache_key = f"forecast_{zone.split('/')[-1]}"
        logging.info(f"Metadata: {metadata}")

        if 'county' not in metadata['properties']:
            logging.warning("County metadata not found, using default 'Unknown County'")
            county = "Unknown County"
        else:
            county = metadata['properties']['county']
            
        if 'city' not in metadata['properties']:
            logging.warning("City metadata not found, using default 'Unknown City'")
            city = "Unknown City"
        else:
            city = metadata['properties']['city']
        
        if 'state' not in metadata['properties']:
            logging.warning("State metadata not found, using default 'Unknown State'")
            state = "Unknown State"
        else:
            state = metadata['properties']['state']

        cached_result = self._get_from_cache(cache_key)
        
        if cached_result:
            logging.info(f"Using cached forecast data for {city}, {state} ({latitude}, {longitude})")
            return cached_result
            
        try:
            # If detailed forecast is requested, use the hourly endpoint
            # Otherwise, use the daily forecast endpoint
            if detailed:
                forecast_url = metadata['properties']['forecastHourly']
            else:
                forecast_url = metadata['properties']['forecast']
                
            # Now get the actual forecast
            response = requests.get(forecast_url, headers=self.headers)
            response.raise_for_status()
            
            forecast_data = response.json()
            self._add_to_cache(cache_key, forecast_data)
            logging.info(f"Cached forecast data for {city}, {state} ({latitude}, {longitude})")
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
            else:
                # If we have cached data, log it
                logging.info(f"Using cached alerts data for zone {zone} - {alerts_data}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching alerts metadata: {e}")
            return {"error": str(e)}
        
        # Now process the alerts data
        try:
            self.current_alerts: Dict[str, Any] = {}
            features = alerts_data.get('features', [])
            title = alerts_data.get('title', 'Active Weather Alerts')
            updated_date = alerts_data.get('updated', datetime.now().isoformat())

            logging.info(f"Processing alerts for zone {zone} - {title} (Updated: {updated_date})")

            for feature in features:
                props = feature['properties']
                alert_id = props.get('id', '')
            
                # Skip if no ID (shouldn't happen but just in case)
                if not alert_id:
                    continue
                
                # Store relevant alert properties
                self.current_alerts[alert_id] = {
                    'event': props.get('event', 'Unknown'),
                    'headline': props.get('headline', ''),
                    'description': props.get('description', ''),
                    'severity': props.get('severity', 'Unknown'),
                    'urgency': props.get('urgency', 'Unknown'),
                    'onset': props.get('onset', ''),
                    'expires': props.get('expires', '')
                }

                logging.info(f"Processed alert ID {alert_id}: {self.current_alerts[alert_id]}")

            self.expired_alerts = {k: v for k, v in self.previous_alerts.items() if k not in self.current_alerts}

            # Update new alerts
            self.new_alerts = {k: v for k, v in self.current_alerts.items() if k not in self.previous_alerts}

            # Update updated alerts
            self.updated_alerts = {k: v for k, v in self.current_alerts.items() if k in self.previous_alerts and v != self.previous_alerts[k]}

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching alerts: {e}")
            return {"error": str(e)}
        
    def get_current_alerts(self) -> Dict[str, Any]:
        """
        Get currently active weather alerts.
        
        Returns:
            Dictionary containing current alerts data
        """
        return self.current_alerts

    def get_new_alerts(self) -> Dict[str, Any]:
        """
        Get newly added weather alerts since the last check.
        
        Returns:
            Dictionary containing new alerts data
        """
        return self.new_alerts
    
    def get_updated_alerts(self) -> Dict[str, Any]:
        """
        Get updated weather alerts since the last check.
        
        Returns:
            Dictionary containing updated alerts data
        """
        return self.updated_alerts
    
    def get_expired_alerts(self) -> Dict[str, Any]:
        """
        Get expired weather alerts since the last check.
        
        Returns:
            Dictionary containing expired alerts data
        """
        return self.expired_alerts

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
            logging.info(f"Formatting forecast data: {forecast_data}")
            if 'city' in forecast_data['properties']:
                city = forecast_data['properties']['city']
            if 'state' in forecast_data['properties']:
                state = forecast_data['properties']['state']
            if 'county' in forecast_data['properties']:
                county = forecast_data['properties']['county']
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

    def format_alerts(self) -> str:
        """
        Format alerts data into a human-readable string.
        
        Args:
            alerts_data: The alerts data from get_alerts()
            
        Returns:
            A formatted string with the active alerts
        """
        result = "No active weather alerts"
        
        try:
            # If current alerts is empty, return default message
            if not self.current_alerts or len(self.current_alerts) == 0:
                return result
                
            result = "ACTIVE WEATHER ALERTS:\n"
            for alert_id in self.current_alerts:
                event = self.current_alerts[alert_id]['event']
                headline = self.current_alerts[alert_id]['headline']
                description = self.current_alerts[alert_id]['description']
                severity = self.current_alerts[alert_id]['severity']
                urgency = self.current_alerts[alert_id]['urgency']
                onset = self.current_alerts[alert_id]['onset']
                expires = self.current_alerts[alert_id]['expires']
                result += f"{alert_id}: {event} - {headline} - {description} - {severity} - {urgency} - {onset} - Expires: {expires}\n"

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
        alerts_str = self.format_alerts(self.current_alerts)
        
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
