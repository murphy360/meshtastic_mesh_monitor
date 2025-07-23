# Configuration Guide

The Mesh Monitor now supports configuration through a JSON file instead of hardcoding feeds and scrapers in the source code. Configuration is loaded automatically when interfaces are initialized.

## Automatic Configuration Loading

The RSS and Web Scraper interfaces now automatically load configuration on startup:

```python
# Configuration loads automatically - no manual setup required
rss_interface = RSSInterface()
web_scraper = WebScraperInterface()
```

Both interfaces will:
1. Create their own `ConfigManager` instance if none is provided
2. Load `config.json` from the project root
3. Apply all enabled feeds/scrapers automatically
4. Set up custom check intervals per feed/scraper

## Configuration File Location

The configuration file should be named `config.json` and placed in the root directory of the project (same level as the `src` folder).

## Configuration File Format

The configuration file uses JSON format with the following structure:

```json
{
  "rss_feeds": [
    {
      "id": "unique_feed_id",
      "name": "Human Readable Feed Name",
      "url": "https://example.com/rss.xml",
      "enabled": true,
      "check_interval_hours": 1
    }
  ],
  "web_scrapers": [
    {
      "id": "unique_scraper_id",
      "name": "Human Readable Scraper Name",
      "url": "https://example.com/page.html",
      "extractor_type": "extractor_name",
      "enabled": true
    }
  ]
}
```

## RSS Feeds Configuration

Each RSS feed requires the following properties:

- **id**: A unique identifier for the feed (string, required)
- **name**: A human-readable name for the feed (string, optional)
- **url**: The RSS feed URL (string, required)
- **enabled**: Whether the feed is active (boolean, default: true)
- **check_interval_hours**: How often to check for updates in hours (number, default: 1)

## Web Scrapers Configuration

Each web scraper requires the following properties:

- **id**: A unique identifier for the scraper (string, required)
- **name**: A human-readable name for the scraper (string, optional)
- **url**: The website URL to scrape (string, required)
- **extractor_type**: The type of extractor to use (string, required)
- **enabled**: Whether the scraper is active (boolean, default: true)

## Example Configuration

```json
{
  "rss_feeds": [
    {
      "id": "twinsburg_calendar",
      "name": "Twinsburg Calendar",
      "url": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=58&CID=All-calendar.xml",
      "enabled": true,
      "check_interval_hours": 1
    },
    {
      "id": "twinsburg_news",
      "name": "Twinsburg News",
      "url": "https://www.mytwinsburg.com/RSSFeed.aspx?ModID=65&CID=All-0",
      "enabled": true,
      "check_interval_hours": 2
    }
  ],
  "web_scrapers": [
    {
      "id": "twinsburg_school_agendas",
      "name": "Twinsburg School Agendas & Minutes",
      "url": "https://www.twinsburg.k12.oh.us/agendasandminutes.aspx",
      "extractor_type": "twinsburg_links",
      "enabled": true
    }
  ]
}
```

## Adding New Feeds

To add a new RSS feed or web scraper:

1. Edit the `config.json` file
2. Add the new feed/scraper to the appropriate array
3. Restart the mesh monitor

## Disabling Feeds

To temporarily disable a feed or scraper without removing it:

1. Set the `enabled` property to `false`
2. Restart the mesh monitor

## Environment Variables

The following environment variables can override configuration settings:

- RSS feeds can still be configured via environment variables using the format:
  - `RSS_FEED_<NAME>=<URL>` (for backward compatibility)

## Configuration Management API

The `ConfigManager` class provides methods to programmatically modify configuration:

- `add_rss_feed(feed_id, name, url, enabled, check_interval_hours)`
- `remove_rss_feed(feed_id)`
- `get_rss_feeds()`
- `get_enabled_rss_feeds()`
- `reload_config()`

## Default Configuration

If no configuration file is found, the system will use default feeds:

- Twinsburg Calendar RSS
- Twinsburg News RSS

## Docker Configuration

When running in Docker, mount the configuration file as a volume:

```bash
docker run -v /path/to/config.json:/app/config.json mesh-monitor
```

## Troubleshooting

1. **Configuration not loading**: Check that `config.json` is in the correct location and has valid JSON syntax
2. **Feeds not updating**: Check the `enabled` flag and `check_interval_hours` setting
3. **Invalid extractor type**: Ensure the `extractor_type` matches available extractors in the web scraper interface

## Migration from Hardcoded Configuration

If you were using environment variables or had custom feeds hardcoded:

1. Create a `config.json` file based on the example above
2. Add your custom feeds to the appropriate sections
3. Remove any custom code that hardcoded feeds
4. Restart the application
