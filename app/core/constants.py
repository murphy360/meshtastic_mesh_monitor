"""
Centralized constants for the Meshtastic Mesh Monitor application.

Eliminates magic numbers and strings scattered across the codebase.
"""

# ---------------------------------------------------------------------------
# Default node / identity strings
# ---------------------------------------------------------------------------
DEFAULT_NODE_NAME = "Unknown"
DEFAULT_LOCATION = "Unknown"
DEFAULT_AI_SHORT_NAME = "MM"
DEFAULT_AI_LONG_NAME = "Mesh Monitor"
DEFAULT_AI_LOCATION = "Unknown Location"

# ---------------------------------------------------------------------------
# Meshtastic identifiers
# ---------------------------------------------------------------------------
LOCAL_NODE_ID = "^local"
BROADCAST_DESTINATION = "^all"

# ---------------------------------------------------------------------------
# Network / connection defaults
# ---------------------------------------------------------------------------
DEFAULT_TCP_SERVER = "meshtastic.local"
DEFAULT_SERIAL_DEVICE = "/dev/ttyUSB0"

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
DATABASE_PATH = "/data/mesh_monitor.db"
MESH_DATA_FILE_PATH = "/data/mesh_data.json"

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------
USER_AGENT_STRING = "MeshtasticMeshMonitor/1.0"

# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------
MESSAGE_MAX_LENGTH = 240
MESSAGE_CHUNK_SIZE = 200
MESSAGE_QUEUE_DELAY_SECONDS = 3
MESSAGE_SEND_MAX_RETRIES = 3
MESSAGE_RETRY_BACKOFF_SECONDS = 5

# ---------------------------------------------------------------------------
# Gemini AI defaults
# ---------------------------------------------------------------------------
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
GEMINI_MAX_MESSAGE_LENGTH = 200
GEMINI_MAX_OUTPUT_TOKENS = 100

# ---------------------------------------------------------------------------
# Infrastructure node roles
# ---------------------------------------------------------------------------
INFRASTRUCTURE_ROLES = {"ROUTER", "ROUTER_CLIENT", "REPEATER", "ROUTER_LATE"}

# ---------------------------------------------------------------------------
# Aircraft detection thresholds
# ---------------------------------------------------------------------------
AIRCRAFT_GROUND_SPEED_THRESHOLD = 150  # m/s
AIRCRAFT_ALTITUDE_THRESHOLD = 8000  # meters

# ---------------------------------------------------------------------------
# Position comparison tolerances
# ---------------------------------------------------------------------------
POSITION_COORDINATE_TOLERANCE = 0.0001
POSITION_ALTITUDE_TOLERANCE = 5  # meters

# ---------------------------------------------------------------------------
# Timing — main loop / connection
# ---------------------------------------------------------------------------
MAIN_LOOP_INTERVAL_SECONDS = 60
CONFIG_WRITE_DELAY_SECONDS = 3
INITIAL_DISCOVERY_TIMEOUT_SECONDS = 10.0
INITIAL_TRACE_OFFSET_SECONDS = 30
HEARTBEAT_FAILURE_THRESHOLD = 5

# ---------------------------------------------------------------------------
# Timing — trace / sitrep
# ---------------------------------------------------------------------------
TRACE_INTERVAL_HOURS = 6
SITREP_LINE_SEND_DELAY_SECONDS = 5
ACTIVE_NODE_THRESHOLD_MINUTES = 60
SITREP_MAX_NODES_TO_LIST = 20

# ---------------------------------------------------------------------------
# Timing — time unit helpers (seconds)
# ---------------------------------------------------------------------------
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 604800
SECONDS_PER_MONTH = 2592000  # ~30 days
SECONDS_PER_YEAR = 31536000  # 365 days

# ---------------------------------------------------------------------------
# Cache durations (seconds)
# ---------------------------------------------------------------------------
DEFAULT_CACHE_DURATION_SECONDS = 3600  # 1 hour
WEATHER_FORECAST_CACHE_SECONDS = 3600
WEATHER_POINTS_CACHE_SECONDS = 86400  # 24 hours
WEATHER_ALERTS_CACHE_SECONDS = 900  # 15 minutes
WEATHER_CONDITIONS_CACHE_SECONDS = 1800  # 30 minutes
WEATHER_API_RATE_LIMIT_SECONDS = 0.5
RSS_DEFAULT_POLL_INTERVAL_SECONDS = 3600

# ---------------------------------------------------------------------------
# Battery alert thresholds
# ---------------------------------------------------------------------------
BATTERY_CRITICAL_THRESHOLD = 5
BATTERY_LOW_THRESHOLD = 10
BATTERY_NOTIFICATION_THRESHOLD = 20
BATTERY_CLEAR_THRESHOLD = 50

# ---------------------------------------------------------------------------
# Traceroute
# ---------------------------------------------------------------------------
DEFAULT_HOP_LIMIT = 5

# ---------------------------------------------------------------------------
# Geolocator
# ---------------------------------------------------------------------------
GEOLOCATOR_TIMEOUT_SECONDS = 10

# ---------------------------------------------------------------------------
# Keyword rate limiting
# ---------------------------------------------------------------------------
KEYWORD_COOLDOWN_SECONDS = 30

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
SCHEDULER_MAX_WORKERS = 3

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_SEPARATOR = "=" * 60
LOG_FILE_MAX_SIZE_BYTES = 10485760  # 10 MB
LOG_BACKUP_COUNT = 5

# ---------------------------------------------------------------------------
# Date/time formats
# ---------------------------------------------------------------------------
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ZULU_DATETIME_FORMAT = "%H%MZ %d %b %Y"
