# Home Assistant Add-on: Port Scout

Port Scout inspects active host listening ports and Docker container mappings to allocate collision-free ports for your homelab services.

## Installation

1. Add this repository to your Home Assistant Add-on Store:
   `https://github.com/CanberraTinkerer/port-scout`
2. Find **Port Scout** in the add-on store and click **Install**.
3. Enable **Show in sidebar** for Ingress access.
4. Start the add-on.

## Configuration

Options:
- `port`: Port on the host for direct web/API access (default: `5055`).
- `min_port`: Lower bound for random port allocation (default: `8000`).
- `max_port`: Upper bound for random port allocation (default: `9999`).

## Features

- **Ingress Support**: Open the dashboard right from your Home Assistant sidebar.
- **Docker Detection**: Finds ports mapped by stopped containers so you never assign a port that conflicts later.
- **Kernel Socket Scanning**: Reads `/proc/net/tcp` directly for zero-overhead real-time accuracy.
- **REST API**: Integrate with Home Assistant automations or sensors via `/api/v1/ports/random`.
