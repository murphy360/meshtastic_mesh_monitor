import requests
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import time
from core.base_interfaces import APIInterface

class WeatherGovInterface(APIInterface):
    """Interface for accessing the National Weather Service (weather.gov) API."""
    
    def __init__(self, user_agent: str = "MeshtasticMeshMonitor/1.0", config_manager=None):
        """
        Initialize the weather.gov interface.
        
        Args:
            user_agent: Identifier for API requests (weather.gov requires a unique identifier)
            config_manager: ConfigManager instance for loading configuration
        """
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/geo+json"
        }
        super().__init__(
            base_url="https://api.weather.gov",
            config_manager=config_manager,
            cache_duration_seconds=3600,  # 1 hour default cache
            default_headers=headers,
            rate_limit_delay=0.5  # Be respectful to weather.gov
        )
        
        # Weather-specific attributes
        self.previous_alerts: Dict[str, Any] = {}  # Store previous alerts to detect changes
        self.current_alerts: Dict[str, Any] = {}
        self.new_alerts: Dict[str, Any] = {}
        self.updated_alerts: Dict[str, Any] = {}    
        self.expired_alerts: Dict[str, Any] = {}  # Store expired alerts from previous run
        self.county = "Unknown County"
        self.zone_url = "Unknown Zone"
        self.city = "Unknown City"
        self.state = "Unknown State"

    def get_forecast(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Get weather forecast for a specific location.
        
        Args:
            latitude: The latitude coordinate
            longitude: The longitude coordinate
            detailed: If True, returns hourly forecast instead of daily
            
        Returns:
            Dictionary containing forecast data
        """

        self.update_location_details(latitude, longitude)
        cache_key = f"forecast_{self.zone_url.split('/')[-1]}"

        cached_result = self._get_cached_data(cache_key)
        
        if cached_result:
            #logging.info(f"Using cached forecast data for {self.city}, {self.state} ({latitude}, {longitude})")
            return cached_result
            
        try:
            # Now get the actual forecast using the base class method
            endpoint = self.forecast_url.replace(self.base_url, "").lstrip("/")
            response = self._make_request(endpoint)
            
            if response.get("success"):
                forecast_data = response["data"]
                self._cache_data(cache_key, forecast_data)
                logging.debug(f"Cached new forecast data for {self.city}, {self.state} ({latitude}, {longitude})")
                return forecast_data
            else:
                logging.error(f"Error fetching forecast: {response.get('error', 'Unknown error')}")
                return {"error": response.get('error', 'Unknown error')}
            
        except Exception as e:
            logging.error(f"Error fetching forecast: {e}")
            return {"error": str(e)}
    
    def update_location_details(self, latitude: float, longitude: float) -> None:
        """
        Update the location details for a specific latitude and longitude.
        
        Args:
            latitude: The latitude coordinate
            longitude: The longitude coordinate
            
        This method fetches the county, zone, city, and state for the given coordinates
        and stores them in the instance variables.
        """
        try:
            points_endpoint = f"/points/{latitude},{longitude}"
            response = self._make_request(points_endpoint)
            
            if not response.get("success"):
                logging.error(f"Error fetching location details: {response.get('error', 'Unknown error')}")
                return
                
            metadata = response["data"]

            if 'forecastZone' in metadata['properties']:
                self.zone_url = metadata['properties']['forecastZone']
            if 'city' in metadata['properties']['relativeLocation']['properties']:
                self.city = metadata['properties']['relativeLocation']['properties']['city']
            if 'state' in metadata['properties']['relativeLocation']['properties']:
                self.state = metadata['properties']['relativeLocation']['properties']['state']
            if 'radarStation' in metadata['properties']:
                self.radar_station = metadata['properties']['radarStation']
            if 'forecast' in metadata['properties']:
                self.forecast_url = metadata['properties']['forecast']
            if 'forecastHourly' in metadata['properties']:
                self.forecast_hourly_url = metadata['properties']['forecastHourly']
            if 'observationStations' in metadata['properties']:
                self.stations_url = metadata['properties']['observationStations']
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching location details: {e}")
    
    def update_alerts(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Get active weather alerts for a specific location.
        
        Args:
            latitude: The latitude coordinate
            longitude: The longitude coordinate
            
        Returns:
            Dictionary containing alert data
        """   
        log_message = f"Fetching weather alerts for {latitude}, {longitude}"
        try:
            # First get the county/zone for the location
            self.update_location_details(latitude, longitude)
            zone = self.zone_url.split('/')[-1]
            log_message += f" - Zone: {zone}"
            
            alerts_data = self._get_cached_data(zone)  # Use Zone as cache key

            if not alerts_data:
                log_message += " - No cached data found, fetching from API"

                # Now get the alerts for this zone
                alerts_endpoint = f"/alerts/active?zone={zone}"
                response = self._make_request(alerts_endpoint)
                
                if response.get("success"):
                    alerts_data = response["data"]
                    self._cache_data(zone, alerts_data, 900)  # 15 minute cache
                else:
                    logging.error(f"Error fetching alerts: {response.get('error', 'Unknown error')}")
                    return []
            else:
                # If we have cached data, log it
                log_message += " - Using cached alerts data"

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching alerts metadata: {e}")
            return {"error": str(e)}
        
        logging.debug(log_message)
        

        # Now process the alerts data
        try:
            self.current_alerts: Dict[str, Any] = {}
            features = alerts_data.get('features', [])
            title = alerts_data.get('title', 'Active Weather Alerts')
            updated_date = alerts_data.get('updated', datetime.now().isoformat())

            logging.debug(f"Processing {title}, updated at {updated_date}")

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
                    'sender': props.get('senderName', 'Unknown'),
                    'severity': props.get('severity', 'Unknown'),
                    'urgency': props.get('urgency', 'Unknown'),
                    'onset': props.get('onset', ''),
                    'expires': props.get('expires', '')
                }

                logging.debug(f"Processed alert ID {alert_id}: {self.current_alerts[alert_id].get('headline', 'No headline')}")

            self.expired_alerts = {k: v for k, v in self.previous_alerts.items() if k not in self.current_alerts}

            # Update new alerts
            self.new_alerts = {k: v for k, v in self.current_alerts.items() if k not in self.previous_alerts}

            # Update updated alerts
            self.updated_alerts = {k: v for k, v in self.current_alerts.items() if k in self.previous_alerts and v != self.previous_alerts[k]}

            # Log alert changes at info level
            if self.new_alerts:
                logging.info(f"🆕 {len(self.new_alerts)} new weather alerts detected")
            if self.updated_alerts:
                logging.info(f"📝 {len(self.updated_alerts)} weather alerts updated")
            if self.expired_alerts:
                logging.info(f"⏰ {len(self.expired_alerts)} weather alerts expired")

            # Update previous alerts for next run
            self.previous_alerts = self.current_alerts.copy()

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
        cached_result = self._get_cached_data(cache_key)
        if cached_result:
            return cached_result
            
        try:
            self.update_location_details(latitude, longitude)
            
            # Get the list of stations
            stations_endpoint = self.stations_url.replace(self.base_url, "").lstrip("/")
            response = self._make_request(stations_endpoint)
            
            if not response.get("success"):
                logging.error(f"Error fetching stations: {response.get('error', 'Unknown error')}")
                return {"error": response.get('error', 'Unknown error')}
                
            stations_data = response["data"]
            
            if len(stations_data['features']) == 0:
                return {"error": "No observation stations found for this location"}
                
            # Get observations from the first station
            station_id = stations_data['features'][0]['properties']['stationIdentifier']
            observations_endpoint = f"/stations/{station_id}/observations/latest"
            
            obs_response = self._make_request(observations_endpoint)
            
            if not obs_response.get("success"):
                logging.error(f"Error fetching observations: {obs_response.get('error', 'Unknown error')}")
                return {"error": obs_response.get('error', 'Unknown error')}
            
            conditions_data = obs_response["data"]
            self._cache_data(cache_key, conditions_data, 1800)  # 30 minute cache
            return conditions_data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching current conditions: {e}")
            return {"error": str(e)}
    
    def get_forecast_string(self, latitude: float, longitude: float) -> str:
        """
        Format forecast data into a simple human-readable string.
        
        Args:
            forecast_data: The forecast data from get_forecast()
            
        Returns:
            A formatted string with the forecast
        """
        forecast_data = self.get_forecast(latitude, longitude)

        if "error" in forecast_data:
            return f"Weather forecast unavailable: {forecast_data['error']}"
            
        try:
            periods = forecast_data['properties']['periods']
            if not periods:
                return "No forecast data available"
                
            result = f"Forecast for {self.city}, {self.state}\n"
            # iterate through the first three periods and format the output
            for i in range(3):
                if i < len(periods):
                    period = periods[i]
                    result += f"{period['name']}: {period['detailedForecast']}, {period['temperature']}{period['temperatureUnit']}. "

            return result
            
        except (KeyError, IndexError) as e:
            logging.error(f"Error formatting forecast: {e}")
            return "Error formatting weather forecast"

    def get_alerts_string(self) -> str:
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
            
    def get_current_conditions_string(self, latitude: float, longitude: float) -> str:
        """
        Format current conditions data into a human-readable string.
        
        Args:
            conditions_data: The conditions data from get_current_conditions()
            
        Returns:
            A formatted string with the current conditions
        """
        conditions_data = self.get_current_conditions(latitude, longitude)

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
        conditions_str = self.get_current_conditions_string(latitude, longitude)
        
        # Get alerts
        alerts_str = self.get_alerts_string()
        
        # Get forecast
        forecast_str = self.get_forecast_string(latitude=latitude, longitude=longitude)
        
        # Combine into summary
        summary = f"{conditions_str}\n\n"
        summary += f"{alerts_str}\n\n"    
        summary += f"{forecast_str}"
        
        return summary
    
    def test_connection(self) -> bool:
        """Test if the interface can connect to the weather service."""
        try:
            response = self._make_request("/")
            return response.get("success", False)
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the weather interface."""
        return {
            "interface_type": "WeatherGovInterface",
            "base_url": self.base_url,
            "county": self.county,
            "city": self.city,
            "state": self.state,
            "zone_url": self.zone_url,
            "cache_entries": len(self.cache),
            "alert_counts": {
                "current": len(self.current_alerts),
                "new": len(self.new_alerts),
                "updated": len(self.updated_alerts),
                "expired": len(self.expired_alerts)
            }
        }
