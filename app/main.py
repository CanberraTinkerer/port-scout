import datetime
import os
from typing import Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.docker_watcher import DockerWatcher
from app.scanner import (
    allocate_random_port,
    get_system_used_ports,
    is_port_free,
)

DEFAULT_MIN_PORT = int(os.getenv("DEFAULT_MIN_PORT", "8000"))
DEFAULT_MAX_PORT = int(os.getenv("DEFAULT_MAX_PORT", "9999"))

app = FastAPI(
    title="Port Scout",
    description="Network port scanner and collision-free port allocator for homelabs",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

docker_watcher = DockerWatcher()

# Path to static assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_ui():
    """Serve the single-page application dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Port Scout API running. Static UI not found.", "version": __version__}


@app.get("/api/v1/health")
def health():
    """System health and integration status."""
    is_proc_available = os.path.exists("/proc/net/tcp")
    return {
        "status": "healthy",
        "version": __version__,
        "scanner_engine": "/proc/net" if is_proc_available else "psutil",
        "docker_connected": docker_watcher.is_available,
        "default_range": [DEFAULT_MIN_PORT, DEFAULT_MAX_PORT],
    }


@app.get("/api/v1/ports/used")
def list_used_ports(protocol: Optional[str] = Query(None, description="Filter by protocol: tcp, udp")):
    """List all currently bound and docker-reserved ports."""
    system_ports = get_system_used_ports()
    docker_reservations = docker_watcher.get_reserved_ports()

    results: List[Dict] = []
    seen: Set[tuple] = set()

    # Add docker reservations
    for r in docker_reservations:
        proto = r["protocol"].lower()
        if protocol and proto != protocol.lower():
            continue
        key = (r["port"], proto)
        seen.add(key)
        results.append({
            "port": r["port"],
            "protocol": proto,
            "source": r["source"],
            "status": "docker_reserved",
            "container": r["container"],
            "container_status": r["status"],
            "host_ip": r["host_ip"],
        })

    # Add active system sockets
    for proto in ["tcp", "udp"]:
        if protocol and proto != protocol.lower():
            continue
        for port in system_ports.get(proto, []):
            key = (port, proto)
            if key not in seen:
                seen.add(key)
                results.append({
                    "port": port,
                    "protocol": proto,
                    "source": "system/kernel",
                    "status": "listening",
                    "container": None,
                    "container_status": None,
                    "host_ip": "0.0.0.0",
                })

    results.sort(key=lambda x: (x["port"], x["protocol"]))
    return {
        "count": len(results),
        "ports": results,
    }


@app.get("/api/v1/ports/random")
def get_random_port(
    min: int = Query(DEFAULT_MIN_PORT, description="Minimum port range"),
    max: int = Query(DEFAULT_MAX_PORT, description="Maximum port range"),
    protocol: str = Query("tcp", description="Protocol: tcp or udp"),
    exclude: Optional[str] = Query(None, description="Comma-separated ports to exclude"),
):
    """Suggest a random verified collision-free port within range."""
    proto = protocol.lower()
    if proto not in ["tcp", "udp"]:
        raise HTTPException(status_code=400, detail="Protocol must be 'tcp' or 'udp'")

    # Collect all reserved ports (system + docker)
    system_ports = get_system_used_ports()
    docker_ports = docker_watcher.get_reserved_port_set()

    reserved: Set[int] = set()
    reserved.update(system_ports.get(proto, set()))
    reserved.update(docker_ports.get(proto, set()))

    exclude_set: Set[int] = set()
    if exclude:
        for p in exclude.split(","):
            p_strip = p.strip()
            if p_strip.isdigit():
                exclude_set.add(int(p_strip))

    port = allocate_random_port(
        min_port=min,
        max_port=max,
        protocol=proto,
        reserved_ports=reserved,
        exclude_ports=exclude_set,
    )

    if port is None:
        raise HTTPException(
            status_code=404,
            detail=f"No free {proto.upper()} ports found in range {min}-{max}",
        )

    return {
        "port": port,
        "protocol": proto,
        "status": "free",
        "range": [min, max],
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.get("/api/v1/ports/check/{port}")
def check_port(port: int, protocol: str = Query("tcp", description="Protocol: tcp or udp")):
    """Check availability status of a specific port."""
    if not (1 <= port <= 65535):
        raise HTTPException(status_code=400, detail="Port must be between 1 and 65535")

    proto = protocol.lower()
    if proto not in ["tcp", "udp"]:
        raise HTTPException(status_code=400, detail="Protocol must be 'tcp' or 'udp'")

    # Check docker reservations
    docker_res = [
        r for r in docker_watcher.get_reserved_ports()
        if r["port"] == port and r["protocol"].lower() == proto
    ]

    # Check active system sockets
    system_ports = get_system_used_ports().get(proto, set())
    is_system_active = port in system_ports

    # Test bind directly
    socket_free = is_port_free(port, protocol=proto)

    in_use = bool(docker_res or is_system_active or not socket_free)

    sources = []
    if docker_res:
        sources.extend([r["source"] for r in docker_res])
    if is_system_active:
        sources.append("system/kernel_listening")
    if not socket_free and not sources:
        sources.append("socket_bind_collision")

    return {
        "port": port,
        "protocol": proto,
        "free": not in_use,
        "status": "free" if not in_use else "in_use",
        "sources": sources,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT_SCOUT_PORT", "5055"))
    host = os.getenv("PORT_SCOUT_HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
