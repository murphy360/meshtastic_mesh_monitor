# meshtastic_mesh_monitor

Monitors the mesh network using Meshtastic devices.

## Docker Install (Raspberry Pi 4 64bit)

To install Docker on a Raspberry Pi 4 (64bit), run the following commands:

```sh
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Ensure Docker can run as a service:

```sh
sudo systemctl enable docker
```

## Running the Mesh Monitor

To run the mesh monitor, follow these steps:

1. Clone the repository:

    ```sh
    git clone https://github.com/yourusername/meshtastic_mesh_monitor.git
    cd meshtastic_mesh_monitor
    ```

2. Build the Docker image:

    ```sh
    docker build -t meshtastic_mesh_monitor .
    ```

3. Run the Docker container:

    ```sh
    docker run -d --name meshtastic_mesh_monitor meshtastic_mesh_monitor
    ```

## Configuration

The mesh monitor can be configured using environment variables and a configuration file:

### Environment Variables
- `CONNECTION_TYPE`: Connection type - either `tcp` (default) or `serial`
- `TCP_SERVER`: The hostname/IP address of the Meshtastic device (default: `meshtastic.local`)
- `SERIAL_PORT`: The serial port path (default: `/dev/ttyUSB0`)

### RSS Feeds and Web Scrapers
RSS feeds and web scrapers are configured through a `config.json` file. See [CONFIGURATION.md](CONFIGURATION.md) for detailed instructions.

Example config.json:
```json
{
  "rss_feeds": [
    {
      "id": "example_feed",
      "name": "Example News Feed",
      "url": "https://example.com/rss.xml",
      "enabled": true,
      "check_interval_hours": 1
    }
  ]
}
```

## Logging

Logs are written to the console and can be viewed using the following command:

```sh
docker logs meshtastic_mesh_monitor
```

## build_and_deploy.sh

The `build_and_deploy.sh` script automates the process of building the Docker image and deploying the container. To use this script, run the following command:

```sh
./build_and_deploy.sh
```

This script will:
1. Build the Docker image.
2. Stop and remove any existing container with the same name.
3. Run a new Docker container with the updated image.
4. Follow docker logs (ctrl+c to exit logs)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.