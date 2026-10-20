import os
import random
import socket
from typing import Dict, List, Optional, Set, Tuple

# Linux TCP states (from kernel include/net/tcp_states.h)
TCP_STATE_LISTEN = "0A"


def parse_proc_net_file(filepath: str, is_tcp: bool = True) -> Set[int]:
    """Parse /proc/net/tcp[6] or udp[6] files and return set of bound ports."""
    ports: Set[int] = set()
    if not os.path.exists(filepath):
        return ports

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()[1:]  # skip header line
            for line in lines:
                parts = line.strip().split()
                if len(parts) < 4:
                    continue
                local_address = parts[1]
                state = parts[3]

                # For TCP, only include listening sockets (state 0A = LISTEN)
                # For UDP, sockets are bound to listen for datagrams (state 07)
                if is_tcp and state != TCP_STATE_LISTEN:
                    continue

                if ":" in local_address:
                    hex_port = local_address.split(":")[1]
                    try:
                        port = int(hex_port, 16)
                        if 1 <= port <= 65535:
                            ports.add(port)
                    except ValueError:
                        continue
    except Exception:
        pass

    return ports


def get_kernel_used_ports() -> Dict[str, Set[int]]:
    """Get active listening/bound ports directly from Linux /proc/net."""
    tcp_ports = parse_proc_net_file("/proc/net/tcp", is_tcp=True)
    tcp_ports.update(parse_proc_net_file("/proc/net/tcp6", is_tcp=True))

    udp_ports = parse_proc_net_file("/proc/net/udp", is_tcp=False)
    udp_ports.update(parse_proc_net_file("/proc/net/udp6", is_tcp=False))

    return {"tcp": tcp_ports, "udp": udp_ports}


def get_psutil_used_ports() -> Dict[str, Set[int]]:
    """Fallback method using psutil for non-Linux or containerized without host proc."""
    tcp_ports: Set[int] = set()
    udp_ports: Set[int] = set()

    try:
        import psutil

        for conn in psutil.net_connections(kind="all"):
            if conn.laddr:
                port = conn.laddr.port
                if conn.type == socket.SOCK_STREAM and conn.status == psutil.CONN_LISTEN:
                    tcp_ports.add(port)
                elif conn.type == socket.SOCK_DGRAM:
                    udp_ports.add(port)
    except Exception:
        pass

    return {"tcp": tcp_ports, "udp": udp_ports}


def get_system_used_ports() -> Dict[str, Set[int]]:
    """Get all bound ports on the system using /proc/net if available, else psutil."""
    if os.path.exists("/proc/net/tcp"):
        return get_kernel_used_ports()
    return get_psutil_used_ports()


def is_port_free(port: int, protocol: str = "tcp") -> bool:
    """Verify if a port is actually free by attempting to bind to it."""
    if not (1 <= port <= 65535):
        return False

    proto = socket.SOCK_STREAM if protocol.lower() == "tcp" else socket.SOCK_DGRAM

    # Try binding on IPv4
    try:
        with socket.socket(socket.AF_INET, proto) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", port))
    except OSError:
        return False

    # Try binding on IPv6 if supported
    if socket.has_ipv6:
        try:
            with socket.socket(socket.AF_INET6, proto) as s6:
                s6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s6.bind(("::", port))
                except OSError:
                    # Some OSes don't allow dual-stack binding or IPv6 is disabled
                    pass
        except OSError:
            pass

    return True


def allocate_random_port(
    min_port: int = 8000,
    max_port: int = 9999,
    protocol: str = "tcp",
    reserved_ports: Optional[Set[int]] = None,
    exclude_ports: Optional[Set[int]] = None,
) -> Optional[int]:
    """Find a verified free port within the given range."""
    if min_port > max_port:
        min_port, max_port = max_port, min_port

    min_port = max(1, min_port)
    max_port = min(65535, max_port)

    reserved = set(reserved_ports or set())
    if exclude_ports:
        reserved.update(exclude_ports)

    candidates = [p for p in range(min_port, max_port + 1) if p not in reserved]
    if not candidates:
        return None

    random.shuffle(candidates)

    for port in candidates:
        if is_port_free(port, protocol=protocol):
            return port

    return None
