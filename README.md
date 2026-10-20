# 📡 Port Scout

> Network port scanner and collision-free port allocator for homelabs, Docker hosts, and Home Assistant OS.

[![Tests](https://img.shields.io/badge/tests-11%20passed-brightgreen.svg)]()
[![Container](https://img.shields.io/badge/container-ghcr.io-blue.svg)]()
[![HA Add-on](https://img.shields.io/badge/home--assistant-add--on-blue.svg)]()

---

## ⚡ Features

- **Kernel Socket Scanning**: Reads `/proc/net/tcp` & `/proc/net/udp` directly with sub-millisecond overhead.
- **Docker Mapping Detection**: Inspects `/var/run/docker.sock` to detect host ports mapped to **stopped or restarting** containers so you never pick a port that collides later.
- **Instant Port Allocator**: Returns verified free random ports within your target range (`8000–9999` by default) with real-time socket bind validation.
- **Modern Web Dashboard**: Responsive dark-mode UI with one-click copy, port checker, and searchable port map.
- **Home Assistant Ingress Ready**: Embeds directly into the Home Assistant sidebar without exposing raw external ports.
- **Cross-Platform**: Runs on Ubuntu, Debian, Unraid, and Home Assistant OS (x86_64 and arm64).

---

## 🚀 Quick Start (Docker / Docker Compose)

### Docker Run
```bash
docker run -d \
  --name port-scout \
  --restart unless-stopped \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -e PORT_SCOUT_PORT=5055 \
  -e DEFAULT_MIN_PORT=8000 \
  -e DEFAULT_MAX_PORT=9999 \
  ghcr.io/canberratinkerer/port-scout:latest
```

Open `http://<your-host-ip>:5055/` in your browser.

### Docker Compose
```yaml
services:
  port-scout:
    image: ghcr.io/canberratinkerer/port-scout:latest
    container_name: port-scout
    restart: unless-stopped
    network_mode: host
    environment:
      - PORT_SCOUT_PORT=5055
      - DEFAULT_MIN_PORT=8000
      - DEFAULT_MAX_PORT=9999
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

> **Note**: `network_mode: host` is required so Port Scout can inspect the host's actual listening sockets.

---

## 🖥️ Unraid Installation

1. Place [`deploy/unraid-template.xml`](deploy/unraid-template.xml) into `/boot/config/plugins/dockerMan/templates-user/` on your Unraid flash drive, **or**:
2. In Unraid WebUI -> **Docker** -> **Add Container**:
   - **Name**: `port-scout`
   - **Repository**: `ghcr.io/canberratinkerer/port-scout:latest`
   - **Network Type**: `Host`
   - **Port**: `5055`
   - **Path**: Host `/var/run/docker.sock` -> Container `/var/run/docker.sock` (Read Only)

---

## 🏠 Home Assistant Add-on Installation

1. In Home Assistant, navigate to **Settings** -> **Add-ons** -> **Add-on Store**.
2. Click the three dots (top right) -> **Repositories**.
3. Add: `https://github.com/CanberraTinkerer/port-scout`
4. Refresh and find **Port Scout** under "Canberra Tinkerer Add-ons".
5. Click **Install**.
6. Turn on **Show in sidebar** and click **Start**.

---

## 🔌 REST API Reference

All responses return standard JSON.

### 1. Health Status
`GET /api/v1/health`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "scanner_engine": "/proc/net",
  "docker_connected": true,
  "default_range": [8000, 9999]
}
```

### 2. Suggest Random Free Port
`GET /api/v1/ports/random?min=8000&max=9999&protocol=tcp`

Query Parameters:
- `min` (int, default: 8000)
- `max` (int, default: 9999)
- `protocol` ("tcp" | "udp", default: "tcp")
- `exclude` (string, comma-separated e.g. "8080,8123")

Response:
```json
{
  "port": 8421,
  "protocol": "tcp",
  "status": "free",
  "range": [8000, 9999],
  "checked_at": "2026-10-21T00:00:00Z"
}
```

### 3. Check Specific Port
`GET /api/v1/ports/check/{port}?protocol=tcp`
```json
{
  "port": 8080,
  "protocol": "tcp",
  "free": false,
  "status": "in_use",
  "sources": ["docker:unifi-controller (exited)"]
}
```

### 4. List All Reserved & Listening Ports
`GET /api/v1/ports/used?protocol=tcp`
```json
{
  "count": 14,
  "ports": [
    {
      "port": 53,
      "protocol": "udp",
      "source": "system/kernel",
      "status": "listening",
      "container": null,
      "host_ip": "0.0.0.0"
    },
    {
      "port": 8080,
      "protocol": "tcp",
      "source": "docker:unifi-controller (exited)",
      "status": "docker_reserved",
      "container": "unifi-controller",
      "container_status": "exited",
      "host_ip": "0.0.0.0"
    }
  ]
}
```

---

## 📊 Home Assistant Dashboard Integration

Add to your Home Assistant `configuration.yaml`:

```yaml
rest:
  - resource: "http://127.0.0.1:5055/api/v1/ports/random?min=8000&max=9999&protocol=tcp"
    scan_interval: 86400
    sensor:
      - name: "Port Scout Suggested Port"
        value_template: "{{ value_json.port }}"
        json_attributes:
          - protocol
          - status
          - range
```

Lovelace Card:
```yaml
type: vertical-stack
cards:
  - type: entity
    entity: sensor.port_scout_suggested_port
    name: "Next Available Homelab Port"
    icon: mdi:radar
  - type: button
    name: "Roll New Port"
    icon: mdi:dice-multiple
    tap_action:
      action: call-service
      service: homeassistant.update_entity
      target:
        entity_id: sensor.port_scout_suggested_port
```

---

## 🧪 Development & Testing

```bash
# Clone
git clone https://github.com/CanberraTinkerer/port-scout.git
cd port-scout

# Install dev deps & run tests
uv run --with pytest --with fastapi --with httpx --with docker --with psutil pytest
```

---

## 📄 License
MIT License. Created by CanberraTinkerer for homelabbers everywhere.
