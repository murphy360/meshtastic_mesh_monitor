# Meshtastic Mesh Monitor

A comprehensive monitoring system for Meshtastic mesh networks that provides RSS feed monitoring, web scraping, AI-powered responses, weather alerts, and situational reporting capabilities.

## Features

- 🌐 **RSS Feed Monitoring**: Automatically monitor RSS feeds and relay updates to the mesh
- 📄 **Web Scraping**: Monitor websites for changes and new content
- 🤖 **AI Integration**: Generate intelligent responses using Google Gemini AI
- 🌦️ **Weather Alerts**: Monitor and relay weather alerts from weather.gov
- 📊 **Situational Reports**: Generate and track network status reports
- 👍 **Message Reactions**: Visual feedback with emoji reactions
- 🔧 **Flexible Configuration**: File-based configuration with automatic loading

## Quick Start

### Docker Installation (Recommended)

```bash
# Install Docker
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl enable docker
```

### Running the Monitor

1. **Clone the repository**:
   ```bash
   git clone https://github.com/murphy360/meshtastic_mesh_monitor.git
   cd meshtastic_mesh_monitor
   ```

2. **Set up configuration directories**:
   ```bash
   mkdir -p ~/mesh-monitor/{data,config,logs}
   cp config/config.json.example ~/mesh-monitor/config/config.json
   # Edit ~/mesh-monitor/config/config.json with your settings
   ```

3. **Build and run with Docker Compose**:
   ```bash
   cd docker
   docker-compose -f docker-compose-example.yaml up --build
   ```

   **Or use the deployment script**:
   ```bash
   ./scripts/deployment/build_and_deploy_image.sh
   ```

## Project Architecture

The mesh monitor uses a clean, modular architecture:

```
src/
├── main.py                    # Application entry point
├── config/                    # Configuration management
│   ├── config_manager.py     # Centralized config handling
│   └── __init__.py
├── core/                      # Core functionality
│   ├── base_interfaces.py    # Base interface classes
│   ├── database.py           # Database operations (SQLite)
│   ├── node.py               # Node management and tracking
│   ├── sitrep.py             # Situational reporting
│   └── __init__.py
├── interfaces/               # External service interfaces
│   ├── gemini_interface.py   # AI integration (Google Gemini)
│   ├── rss_interface.py      # RSS feed monitoring
│   ├── weather_interface.py  # Weather alerts (weather.gov)
│   ├── web_scraper_interface.py # Web content monitoring
│   └── __init__.py
└── utils/                    # Utility functions
    ├── scrapers/            # Custom web scrapers
    │   └── twinsburg_boe.py # Specific scraper implementations
    └── __init__.py
```

## Configuration

The monitor uses automatic configuration loading - simply create a `config.json` file and the interfaces load it automatically.

### Connection Configuration

Configure how to connect to your Meshtastic device:

```bash
# Environment Variables
export CONNECTION_TYPE="tcp"          # or "serial"
export TCP_SERVER="meshtastic.local"  # IP/hostname for TCP
export SERIAL_PORT="/dev/ttyUSB0"     # Serial port path
```

### RSS Feeds and Web Scrapers

Create a `config.json` file in the project root:

```json
{
  "rss_feeds": [
    {
      "id": "tech_news",
      "name": "Tech News",
      "url": "https://feeds.feedburner.com/TechCrunch",
      "enabled": true,
      "check_interval_hours": 2
    }
  ],
  "web_scrapers": [
    {
      "id": "local_government",
      "name": "City Website",
      "url": "https://www.example.gov/news",
      "enabled": true,
      "check_interval_hours": 24,
      "extractor_type": "links"
    }
  ]
}
```

### Configuration Properties

**RSS Feeds:**
- `id`: Unique identifier (required)
- `name`: Human-readable name (optional)
- `url`: RSS feed URL (required)
- `enabled`: Enable/disable monitoring (default: true)
- `check_interval_hours`: Check frequency in hours (default: 1)

**Web Scrapers:**
- `id`: Unique identifier (required)
- `name`: Human-readable name (optional)
- `url`: Website URL to scrape (required)
- `enabled`: Enable/disable monitoring (default: true)
- `check_interval_hours`: Check frequency in hours (default: 1)
- `extractor_type`: Content extraction method (`generic`, `links`, `twinsburg_links`)
- `css_selector`: CSS selector for targeted content (optional)

### Automatic Loading

The system automatically loads configuration:

```python
# No manual setup required - config loads automatically
rss_interface = RSSInterface()
web_scraper = WebScraperInterface()
```

### Backward Compatibility

Environment variables are still supported for RSS feeds:

```bash
export RSS_FEED_NEWS="https://example.com/news.rss"
export RSS_FEED_TECH="https://techsite.com/feed.xml"
```

## Docker Configuration

### Environment Variables

```bash
# Connection settings
CONNECTION_TYPE=tcp
TCP_SERVER=meshtastic.local
SERIAL_PORT=/dev/ttyUSB0

# AI Integration (optional)
GEMINI_API_KEY=your_api_key_here

# Legacy RSS feeds (optional)
RSS_FEED_NEWS=https://example.com/rss.xml
```

### Volume Mounts

```bash
docker run -d \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/data:/data \
  -e CONNECTION_TYPE=tcp \
  -e TCP_SERVER=your.meshtastic.device \
  --name mesh_monitor \
  meshtastic_mesh_monitor
```

## AI Integration

The monitor can generate intelligent responses using Google Gemini AI:

1. **Get an API key** from [Google AI Studio](https://aistudio.google.com/)
2. **Set the environment variable**:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
3. **Send messages** to the bot and it will respond with AI-generated content

## Monitoring Features

### RSS Feed Monitoring
- Automatic detection of new RSS items
- Configurable check intervals per feed
- Rich message formatting with titles, links, and descriptions

### Web Scraping
- Monitor websites for new content and changes
- Extract links, PDFs, and text content
- Support for custom extractors
- Automatic PDF download and processing

### Weather Alerts
- Integration with weather.gov API
- Automatic alert monitoring and relay
- Geographical filtering for relevant alerts

### Network Monitoring
- Track node status and connectivity
- Generate situational reports (SITREP)
- Monitor mesh health and performance

## Logging and Monitoring

View logs in real-time:

```bash
# Follow logs
docker logs -f meshtastic_mesh_monitor

# View recent logs
docker logs --tail 100 meshtastic_mesh_monitor
```

Logs include:
- RSS feed check results
- Web scraper activity
- AI response generation
- Network events and status
- Configuration loading status

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the monitor
python src/mesh-monitor.py
```

### Adding New Features

The monitor is designed for extensibility:

- **RSS feeds**: Add new feeds to `config.json`
- **Web scrapers**: Create custom extractors in `web_scraper_interface.py`
- **AI responses**: Customize prompts in `gemini_interface.py`
- **Monitoring**: Add new data sources following existing patterns

### Testing Configuration

Use the example script to test your configuration:

```bash
python example_config_usage.py
```

## Troubleshooting

### Common Issues

1. **Configuration not loading**
   - Verify `config.json` is in the project root
   - Check JSON syntax is valid
   - Review logs for error messages

2. **Feeds not updating**
   - Check `enabled` flag is set to `true`
   - Verify `check_interval_hours` setting
   - Ensure feed URLs are accessible

3. **Connection issues**
   - Verify `CONNECTION_TYPE` environment variable
   - Check TCP server address or serial port path
   - Ensure Meshtastic device is accessible

4. **AI responses not working**
   - Verify `GEMINI_API_KEY` is set correctly
   - Check API quota and billing status
   - Review logs for API error messages

### Log Analysis

Key log messages to monitor:
- `RSS Interface initialized with X feeds`
- `Web Scraper Interface initialized with X websites`
- `Configuration loaded successfully`
- `New RSS Item Detected` / `Update Detected`

## Build and Deployment

The `build_and_deploy.sh` script automates deployment:

```bash
./build_and_deploy.sh
```

This script:
1. Builds the Docker image
2. Stops any existing container
3. Starts a new container with updated code
4. Follows logs for monitoring

## Contributing

Contributions are welcome! Areas for improvement:

- Additional RSS feed sources
- New web scraper extractors
- Enhanced AI response capabilities
- Mobile-friendly interfaces
- Performance optimizations

Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.