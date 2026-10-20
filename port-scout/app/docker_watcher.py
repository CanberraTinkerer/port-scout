import logging
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DockerWatcher:
    def __init__(self):
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        try:
            import docker
            self._client = docker.from_env(timeout=3)
            self._client.ping()
            self._available = True
            logger.info("Successfully connected to Docker daemon.")
        except Exception as e:
            self._client = None
            self._available = False
            logger.warning("Docker daemon not reachable via socket: %s", e)

    @property
    def is_available(self) -> bool:
        if not self._available:
            self._init_client()
        return self._available

    def get_reserved_ports(self) -> List[Dict]:
        """Inspect all containers (running and stopped) and return their host port reservations."""
        if not self.is_available or self._client is None:
            return []

        reservations: List[Dict] = []
        try:
            containers = self._client.containers.list(all=True)
            for container in containers:
                c_name = container.name
                c_status = container.status
                c_image = container.image.tags[0] if container.image.tags else container.short_id

                # Inspect HostConfig PortBindings
                host_config = container.attrs.get("HostConfig", {})
                port_bindings = host_config.get("PortBindings") or {}

                # Inspect NetworkSettings Ports (running containers)
                net_settings = container.attrs.get("NetworkSettings", {})
                net_ports = net_settings.get("Ports") or {}

                merged_ports = dict(port_bindings)
                for k, v in net_ports.items():
                    if k not in merged_ports or not merged_ports[k]:
                        merged_ports[k] = v

                for container_port_proto, host_bindings in merged_ports.items():
                    if not host_bindings:
                        continue

                    # container_port_proto is like '80/tcp'
                    parts = container_port_proto.split("/")
                    proto = parts[1].lower() if len(parts) > 1 else "tcp"

                    for binding in host_bindings:
                        host_port_str = binding.get("HostPort")
                        host_ip = binding.get("HostIp") or "0.0.0.0"
                        if host_port_str:
                            try:
                                host_port = int(host_port_str)
                                reservations.append({
                                    "port": host_port,
                                    "protocol": proto,
                                    "container": c_name,
                                    "status": c_status,
                                    "image": c_image,
                                    "host_ip": host_ip,
                                    "source": f"docker:{c_name} ({c_status})",
                                })
                            except ValueError:
                                continue
        except Exception as e:
            logger.error("Error inspecting Docker containers: %s", e)
            self._available = False

        return reservations

    def get_reserved_port_set(self) -> Dict[str, Set[int]]:
        """Return dict of set of ports per protocol reserved by Docker."""
        res = {"tcp": set(), "udp": set()}
        for r in self.get_reserved_ports():
            proto = r["protocol"]
            if proto in res:
                res[proto].add(r["port"])
            else:
                res[proto] = {r["port"]}
        return res
