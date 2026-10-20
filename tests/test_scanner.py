import socket
import pytest
from app.scanner import (
    allocate_random_port,
    is_port_free,
    parse_proc_net_file,
)


def test_is_port_free_valid():
    # An ephemeral port that we don't bind should be free
    # Bind a temporary socket to find an open port, then close it and test is_port_free
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()

    assert is_port_free(port, protocol="tcp") is True


def test_is_port_free_occupied():
    # Bind a socket and verify is_port_free returns False while held
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]

    try:
        assert is_port_free(port, protocol="tcp") is False
    finally:
        s.close()


def test_allocate_random_port():
    port = allocate_random_port(min_port=49200, max_port=49250, protocol="tcp")
    assert port is not None
    assert 49200 <= port <= 49250


def test_allocate_random_port_with_exclude():
    # If range is single port and excluded, should return None
    port = allocate_random_port(min_port=55000, max_port=55000, exclude_ports={55000})
    assert port is None


def test_parse_proc_net_file_empty(tmp_path):
    fake_proc = tmp_path / "fake_tcp"
    fake_proc.write_text("  sl  local_address rem_address   st\n")
    ports = parse_proc_net_file(str(fake_proc), is_tcp=True)
    assert len(ports) == 0


def test_parse_proc_net_file_sample(tmp_path):
    # Sample /proc/net/tcp format: local_address 00000000:0050 (hex 50 = port 80), st 0A (LISTEN)
    fake_proc = tmp_path / "fake_tcp"
    fake_proc.write_text(
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        "   0: 00000000:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0\n"
        "   1: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12346 1 0000000000000000 100 0 0 10 0\n"
        "   2: 0100007F:0050 0100007F:1234 01 00000000:00000000 00:00000000 00000000     0        0 12347 1 0000000000000000 100 0 0 10 0\n"
    )
    ports = parse_proc_net_file(str(fake_proc), is_tcp=True)
    # Port 80 (0x0050) LISTEN -> yes
    # Port 8080 (0x1F90) LISTEN -> yes
    # Row 2 is state 01 (ESTABLISHED) -> should be skipped
    assert 80 in ports
    assert 8080 in ports
    assert len(ports) == 2
